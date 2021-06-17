"""
Development only module
"""

from dotenv import dotenv_values

from molgenis.bbmri_eric.bbmri_client import BbmriSession

config = dotenv_values(".env.local")

target = config["TARGET"]
username = config["USERNAME"]
password = config["PASSWORD"]

bbmri_session = BbmriSession(
    url=target,
    username=username,
    password=password,
)

bbmri_session.stage_all_external_nodes()
bbmri_session.publish_all_nodes()
