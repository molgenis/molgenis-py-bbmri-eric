"""
This is the post-cross-restore hook for the BBMRI-ERIC acceptance server. This server
is deployed by copying the production database and this hook transforms the database in
such a way that is safe to use as an acceptance test environment:

1. Changes the password
2. Removes production PIDs and replaces them with test PIDs
3. Disables some scheduled jobs
4. Removes people from email lists in scheduled jobs (except the support email)

Requires a .env file next to it to configure. Example:

HOOK_OLD_PASSWORD=oldpassword
HOOK_NEW_PASSWORD=newpassword
HOOK_SERVER_URL=https://myserver/
HOOK_PYHANDLE_CREDS_JSON=pyhandle_creds.json
HOOK_USE_LIVE_PID_SERVICE=True
HOOK_MOLGENIS_SUPPORT_EMAIL=molgenis-support@umcg.nl

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


def run():
    logging.getLogger("pyhandle").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    session = EricSession(url)
    session.login("admin", old_password)

    change_password(session, logger)
    overwrite_pids(session, logger)
    disable_jobs(session, logger)
    remove_job_emails(session, logger)

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
        headers=session._get_token_header_with_content_type(),
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

    biobanks = session.get_uploadable_data("eu_bbmri_eric_biobanks")
    for biobank in biobanks:
        biobank.pop("pid", None)
    pid_manager.assign_biobank_pids(Table.of(TableType.BIOBANKS, Mock(), biobanks))

    session.update("eu_bbmri_eric_biobanks", biobanks)

    # ========================

    logger.info("Making biobanks PID column readonly again")

    response = session._session.patch(
        session._api_url + f"metadata/eu_bbmri_eric_biobanks/attributes/{pid_attr_id}",
        data=json.dumps({"readonly": True}),
        headers=session._get_token_header_with_content_type(),
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


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    run()
