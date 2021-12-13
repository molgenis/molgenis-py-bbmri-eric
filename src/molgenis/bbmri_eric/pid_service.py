from enum import Enum
from typing import List, Optional
from urllib.parse import quote

from pyhandle.client.resthandleclient import RESTHandleClient
from pyhandle.clientcredentials import PIDClientCredentials
from pyhandle.handleclient import PyHandleClient

from molgenis.bbmri_eric.errors import EricError


class Status(Enum):
    TERMINATED = "TERMINATED"
    MERGED = "MERGED"


class PidService:
    def __init__(self, client: RESTHandleClient, prefix: str):
        self.client = client
        self.prefix = prefix

    @staticmethod
    def from_credentials(credentials_json: str):
        """
        Factory method to create a PidService from a credentials JSON file. The
        credentials file should have the following contents:

        {
          "handle_server_url": "...",
          "baseuri": "...",
          "private_key": "...",
          "certificate_only": "...",
          "client": "rest",
          "prefix": "...",
          "reverselookup_username": "...",
          "reverselookup_password": "..."
        }

        :param credentials_json: a full path to the credentials file
        :return: a PidService
        """
        credentials = PIDClientCredentials.load_from_JSON(credentials_json)
        return PidService(
            PyHandleClient("rest").instantiate_with_credentials(credentials),
            credentials.get_prefix(),
        )

    def reverse_lookup(self, url: str) -> Optional[List[str]]:
        """
        Looks for handles with this url.

        :param url: the URL to look up
        :raise: EricError if insufficient permissions for reverse lookup
        :return: a (potentially empty) list of PIDs
        """
        url = quote(url)
        pids = self.client.search_handle(URL=url, prefix=self.prefix)

        if not pids:
            raise EricError("Insufficient permissions for reverse lookup")

        return pids

    def register_pid(self, url: str, name: str) -> str:
        """
        Generates a new PID and registers it with a URL and a NAME field.
        :param url: the URL for the handle
        :param name: the NAME for the handle
        :return: the generated PID
        """
        return self.client.generate_and_register_handle(
            prefix=self.prefix, location=url, NAME=name
        )

    def update_name(self, pid: str, new_name: str):
        # TODO implement
        pass

    def set_status(self, pid: str, status: Status):
        # TODO implement
        pass
