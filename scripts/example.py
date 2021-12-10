"""
Example usage file meant for development. Make sure you have an .env.local file and a
pyhandle_creds.json file in this folder.
"""

from dotenv import dotenv_values

from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.eric import Eric
from molgenis.bbmri_eric.pid_service import PidService

# get credentials from .env.local
config = dotenv_values(".env")
target = config["TARGET"]
username = config["USERNAME"]
password = config["PASSWORD"]

# login to the directory with an EricSession
session = EricSession(url=target)
session.login(username, password)

# Create PIDClient
pid_service = PidService.from_credentials("pyhandle_creds.json")

# instantiate the Eric class and do some work
eric = Eric(session, pid_service)
eric.publish_nodes(session.get_nodes(["CY"]))
