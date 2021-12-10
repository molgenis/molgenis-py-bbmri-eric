from enum import Enum
from typing import List, Optional

from pyhandle.client.resthandleclient import RESTHandleClient
from pyhandle.clientcredentials import PIDClientCredentials
from pyhandle.handleclient import PyHandleClient


class Status(Enum):
    TERMINATED = "TERMINATED"
    MERGED = "MERGED"


class PidService:
    def __init__(self, client: RESTHandleClient, prefix: str):
        self.client = client
        self.prefix = prefix

    @staticmethod
    def from_credentials(credentials_json: str):
        credentials = PIDClientCredentials.load_from_JSON(credentials_json)
        return PidService(
            PyHandleClient("rest").instantiate_with_credentials(credentials),
            credentials.get_prefix(),
        )

    def reverse_lookup(self, url: str) -> Optional[List[str]]:
        return self.client.search_handle(URL=url, prefix=self.prefix)

    def register_pid(self, url: str, name: str) -> str:
        return self.client.generate_and_register_handle(
            prefix=self.prefix, location=url, NAME=name
        )

    def update_name(self, pid: str, new_name: str):
        # TODO implement
        pass

    def set_status(self, pid: str, status: Status):
        # TODO implement
        pass
