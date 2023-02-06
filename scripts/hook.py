"""
This is the post-cross-restore hook for the BBMRI-ERIC acceptance server. This server
is deployed by copying the production database and this hook transforms the database in
such a way that is safe to use as an acceptance test environment:

1. Changes the password
2. Removes production PIDs and replaces them with test PIDs
3. Disables some scheduled jobs
4. Removes people from email lists in scheduled jobs (except the support email)
5. Updates the OIDC-client settings
6. Updates the Google Analytics settings
7. Update the Negotiator URL, username and password

Requires a .env file next to it to configure. Example:

HOOK_OLD_PASSWORD=oldpassword
HOOK_NEW_PASSWORD=newpassword
HOOK_SERVER_URL=https://myserver/
HOOK_PYHANDLE_CREDS_JSON=pyhandle_creds.json
HOOK_USE_LIVE_PID_SERVICE=True
HOOK_MOLGENIS_SUPPORT_EMAIL=molgenis-support@umcg.nl
HOOK_GA_ID=ga_id
HOOK_OIDC_CLIENT_ID=oidc_client_id
HOOK_OIDC_CLIENT_SECRET=oidc_client_secret
HOOK_OIDC_CLIENT_NAME=oidc_client_name
HOOK_NEGOTIATOR_URL=negotiator_url
HOOK_NEGOTIATOR_USERNAME=negotiator_username
HOOK_NEGOTIATOR_PASSWORD=negotiator_password

Setting HOOK_USE_LIVE_PID_SERVICE to False will use the DummyPidService instead, which
will not create actual handles but will fill the column with fake PIDs.
"""
import json
import logging
from unittest.mock import Mock

from dotenv import dotenv_values

from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.model import Table, TableType
from molgenis.bbmri_eric.pid_manager import PidManager
from molgenis.bbmri_eric.pid_service import DummyPidService, PidService

config = dotenv_values(".env")
old_password = config["HOOK_OLD_PASSWORD"]
new_password = config["HOOK_NEW_PASSWORD"]
url = config["HOOK_SERVER_URL"]
pyhandle_creds = config["HOOK_PYHANDLE_CREDS_JSON"]
use_live_pid_service = config["HOOK_USE_LIVE_PID_SERVICE"].lower() == "true"
support_email = config["HOOK_MOLGENIS_SUPPORT_EMAIL"]
ga_id = config["HOOK_GA_ID"]
oidc_client_id = config["HOOK_OIDC_CLIENT_ID"]
oidc_client_secret = config["HOOK_OIDC_CLIENT_SECRET"]
oidc_client_name = config["HOOK_OIDC_CLIENT_NAME"]
negotiator_url = config["HOOK_NEGOTIATOR_URL"]
negotiator_username = config["HOOK_NEGOTIATOR_USERNAME"]
negotiator_password = config["HOOK_NEGOTIATOR_PASSWORD"]


def run():
    logging.getLogger("pyhandle").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    session = EricSession(url)
    session.login("admin", old_password)

    change_password(session, logger)
    overwrite_pids(session, logger)
    disable_jobs(session, logger)
    remove_job_emails(session, logger)
    update_oidc_settings(session, logger)
    update_ga_settings(session, logger)
    update_negotiator_config(session, logger)

    logger.info("Finished!")


def change_password(session: EricSession, logger):
    logger.info("Updating admin password")
    admin_user_id = session.get("sys_sec_User", q="username==admin")[0]["id"]
    session.update_one("sys_sec_User", admin_user_id, "password_", new_password)


# noinspection PyProtectedMember
def overwrite_pids(session: EricSession, logger):
    logger.info("Making biobanks PID column temporarily editable (readonly=false)")

    pid_attr_id = session.get(
        "sys_md_Attribute", q="name==pid&&entity==eu_bbmri_eric_biobanks"
    )[0]["id"]

    response = session._session.patch(
        session._api_url + f"metadata/eu_bbmri_eric_biobanks/attributes/{pid_attr_id}",
        data=json.dumps({"readonly": False}),
        headers=session._headers.ct_token_header,
    )
    response.raise_for_status()

    # ========================

    logger.info("Setting up PID manager")

    pid_service = (
        PidService.from_credentials(pyhandle_creds)
        if use_live_pid_service
        else DummyPidService()
    )
    pid_manager = PidManager(pid_service, Mock())

    # ========================

    logger.info("Overwriting production PIDs with test PIDs")

    biobanks = session.get("eu_bbmri_eric_biobanks", uploadable=True)
    for biobank in biobanks:
        biobank.pop("pid", None)
    pid_manager.assign_biobank_pids(Table.of(TableType.BIOBANKS, Mock(), biobanks))

    session.update_all("eu_bbmri_eric_biobanks", biobanks)

    # ========================

    logger.info("Making biobanks PID column readonly again")

    response = session._session.patch(
        session._api_url + f"metadata/eu_bbmri_eric_biobanks/attributes/{pid_attr_id}",
        data=json.dumps({"readonly": True}),
        headers=session._headers.ct_token_header,
    )
    response.raise_for_status()


def disable_jobs(session: EricSession, logger):
    logger.info("Disabling scheduled job 'ping_fdp'")

    ping_fdp_id = session.get("sys_job_ScheduledJob", q="name==ping_fdp")[0]["id"]
    session.update_one("sys_job_ScheduledJob", ping_fdp_id, "active", False)


def remove_job_emails(session: EricSession, logger):
    logger.info("Removing email addresses from all scheduled jobs")

    job_entity = "sys_job_ScheduledJob"
    jobs = session.get(job_entity)
    for job in jobs:
        failure_email = ""
        success_email = ""

        if "failureEmail" in job and support_email in job["failureEmail"]:
            failure_email = support_email
        if "successEmail" in job and support_email in job["successEmail"]:
            success_email = support_email

        session.update_one(job_entity, job["id"], "failureEmail", failure_email)
        session.update_one(job_entity, job["id"], "successEmail", success_email)


def update_ga_settings(session: EricSession, logger):
    logger.info("Update Google Analytics settings")

    settings_entity = "sys_set_app"
    settings = session.get(settings_entity)

    for setting in settings:
        ga_acc_privacy_friendly = False
        tracking_code_footer = f"""</script>
<!-- Global site tag (gtag.js) - Google Analytics -->
<script src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', '{ga_id}');
</script>"""

        if "ga_tracking_id" in setting:
            session.update_one(settings_entity, setting["id"], "ga_tracking_id", ga_id)
            session.update_one(
                settings_entity,
                setting["id"],
                "tracking_code_footer",
                tracking_code_footer,
            )
            session.update_one(
                settings_entity,
                setting["id"],
                "ga_acc_privacy_friendly",
                ga_acc_privacy_friendly,
            )


def update_oidc_settings(session: EricSession, logger):
    logger.info("Update OIDC client settings")

    oidc_entity = "sys_sec_oidc_OidcClient"
    oidc_settings = session.get(oidc_entity, uploadable=True)
    to_be_deleted = []

    for oidc in oidc_settings:
        if oidc["registrationId"] == "bbmriEricAAI":
            oidc["clientName"] = "BBMRI-ERIC AAI - BBMRI-ERIC ACCEPTANCE Catalogue"
        else:
            to_be_deleted.append(oidc["registrationId"])

    session.update_all(oidc_entity, oidc_settings)

    if to_be_deleted:
        session.delete_list(oidc_entity, to_be_deleted)


def update_negotiator_config(session: EricSession, logger):
    logger.info("Update Negotiator Config")

    negotiator_entity = "sys_negotiator_NegotiatorConfig"
    negotiator_config = session.get(negotiator_entity, uploadable=True)
    to_be_deleted = []

    for row in negotiator_config:
        if row["id"] == "directory":
            row["negotiator_url"] = negotiator_url
            row["username"] = negotiator_username
            row["password"] = negotiator_password
        else:
            to_be_deleted.append(row["id"])

    session.update_all(negotiator_entity, negotiator_config)

    if to_be_deleted:
        session.delete_list(negotiator_entity, to_be_deleted)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    run()
