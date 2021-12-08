"""
Example usage file meant for development. Make sure you have an .env.local file and a
pyhandle_creds.json file in this folder.
"""

from dotenv import dotenv_values

from molgenis.bbmri_eric.bbmri_client import EricSession

# noinspection PyProtectedMember
from molgenis.bbmri_eric.eric import Eric

# get credentials from .env.local
config = dotenv_values(".env.local")
target = config["TARGET"]
username = config["USERNAME"]
password = config["PASSWORD"]

# get staging data of node NL
session = EricSession(url=target)
session.login(username, password)

# instantiate the Eric class and do some work
eric = Eric(session)
eric.configure_handle_client("pyhandle_creds.json")
