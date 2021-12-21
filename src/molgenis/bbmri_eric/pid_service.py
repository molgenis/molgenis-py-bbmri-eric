from enum import Enum
from typing import List, Optional
from urllib.parse import quote

from pyhandle.client.resthandleclient import RESTHandleClient
from pyhandle.clientcredentials import PIDClientCredentials
from pyhandle.handleclient import PyHandleClient
from pyhandle.handleexceptions import (
    HandleAuthenticationError,
    HandleNotFoundException,
    HandleSyntaxError,
)

from molgenis.bbmri_eric.errors import EricError


class Status(Enum):
    TERMINATED = "TERMINATED"
    MERGED = "MERGED"


def pyhandle_error_handler(func):
    """
    Decorator that catches PyHandleExceptions and wraps them in an EricError.
    """

    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HandleAuthenticationError as e:
            raise EricError("Handle authentication failed") from e
        except HandleNotFoundException as e:
            raise EricError(f"Handle not found on handle server: {e.handle}")
        except HandleSyntaxError as e:
            raise EricError(f"Handle has incorrect syntax: {e.handle}")

    return inner_function


class PidService:
    """
    Low level service for interacting with the handle server.
    """

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

    @pyhandle_error_handler
    def reverse_lookup(self, url: str) -> Optional[List[str]]:
        """
        Looks for handles with this url.

        :param url: the URL to look up
        :raise: EricError if insufficient permissions for reverse lookup
        :return: a (potentially empty) list of PIDs
        """
        url = quote(url)
        pids = self.client.search_handle(URL=url, prefix=self.prefix)

        if pids is None:
            raise EricError("Insufficient permissions for reverse lookup")

        return pids

    @pyhandle_error_handler
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

    @pyhandle_error_handler
    def set_name(self, pid: str, new_name: str):
        """
        Sets the NAME field of an existing PID. Adds the field if it doesn't exist.

        :param pid: the PID to change the NAME of
        :param new_name: the new value for the NAME field
        """
        self.client.modify_handle_value(pid, NAME=new_name)

    @pyhandle_error_handler
    def set_status(self, pid: str, status: Status):
        """
        Sets the STATUS field of an existing PID. Adds the field if it doesn't exist.

        :param pid: the PID to change the STATUS of
        :param status: a Status enum
        """
        self.client.modify_handle_value(pid, STATUS=status.value)

    @pyhandle_error_handler
    def remove_status(self, pid: str):
        """
        Removes the STATUS field of an existing PID.

        :param pid: the PID to remove the STATUS field of
        """
        self.client.delete_handle_value(pid, "STATUS")
