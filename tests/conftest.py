import json
from typing import List
from unittest.mock import MagicMock

import pkg_resources
import pytest

from molgenis.bbmri_eric.model import Node, NodeData, Source, Table, TableType


def get_data(table_type) -> List[dict]:
    file = open(
        pkg_resources.resource_filename("tests.resources", table_type + ".json"), "r"
    )
    data = json.load(file)
    file.close()
    return data


@pytest.fixture
def node_data() -> NodeData:
    """
    Reads json files with the five data sources and
    returns NodeData to test with.
    """
    persons_meta = MagicMock()
    persons_meta.id = "eu_bbmri_eric_NL_persons"
    persons = Table.of(
        TableType.PERSONS,
        persons_meta,
        get_data("persons"),
    )

    networks_meta = MagicMock()
    networks_meta.id = "eu_bbmri_eric_NL_networks"
    networks = Table.of(
        TableType.NETWORKS,
        networks_meta,
        get_data("networks"),
    )

    also_known_meta = MagicMock()
    also_known_meta.id = "eu_bbmri_eric_NL_also_known_in"
    also_known = Table.of(
        TableType.ALSO_KNOWN,
        also_known_meta,
        get_data("also_known"),
    )

    biobanks_meta = MagicMock()
    biobanks_meta.id = "eu_bbmri_eric_NL_biobanks"
    biobanks_meta.hyperlinks = ["url"]
    biobanks = Table.of(
        TableType.BIOBANKS,
        biobanks_meta,
        get_data("biobanks"),
    )

    collection_meta = MagicMock()
    collection_meta.id = "eu_bbmri_eric_NL_collections"
    collections = Table.of(
        TableType.COLLECTIONS,
        collection_meta,
        get_data("collections"),
    )

    return NodeData.from_dict(
        Node("NL", "NL", None),
        Source.STAGING,
        {
            TableType.PERSONS.value: persons,
            TableType.NETWORKS.value: networks,
            TableType.ALSO_KNOWN.value: also_known,
            TableType.BIOBANKS.value: biobanks,
            TableType.COLLECTIONS.value: collections,
        },
    )


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()
    session.url = "url"
    return session


@pytest.fixture
def printer() -> MagicMock:
    return MagicMock()


@pytest.fixture
def pid_service() -> MagicMock:
    service = MagicMock()
    service.base_url = "url/"
    return service
