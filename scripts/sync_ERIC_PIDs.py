"""
This script updates the biobank PIDs on an external
server with the PIDs from the BBMRI-ERIC Directory.

The script can be placed and scheduled on an external server
with the ${molgenisToken} security token activated.
"""

import json
from typing import List
from urllib.parse import quote_plus

import requests

from molgenis.client import Session
from molgenis.errors import raise_exception


class ExtendedSession(Session):
    """
    Class adding batch update of one attribute to the molgenis-py-client
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_one_batch(self, entity: str, attribute: str, values: List[dict]):
        """Updates one column in multiple rows."""
        response = self._session.put(
            self._api_url + "v2/" + quote_plus(entity) + "/" + quote_plus(attribute),
            headers=self._headers.ct_token_header,
            data=json.dumps({"entities": values}),
        )

        try:
            response.raise_for_status()
        except requests.RequestException as ex:
            raise_exception(ex)

        return response


session = ExtendedSession(url="http://localhost:8080", token="${molgenisToken}")
eric_session = Session(url="${eric_url}")

biobanks = session.get("eu_bbmri_eric_biobanks", attributes="id", uploadable=True)
eric_pids = eric_session.get(
    "eu_bbmri_eric_biobanks", attributes="id,pid", uploadable=True
)

biobank_pids = {}

for pid in eric_pids:
    biobank_pids[pid["id"]] = pid["pid"]

for biobank in biobanks:
    biobank["pid"] = biobank_pids[biobank["id"]]

print("Update PIDs")
session.update_one_batch("eu_bbmri_eric_biobanks", "pid", biobanks)
