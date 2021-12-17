import pickle
from unittest.mock import MagicMock

import pkg_resources
import pytest

from molgenis.bbmri_eric.eric import Eric
from molgenis.bbmri_eric.model import NodeData


@pytest.fixture
def node_data() -> NodeData:
    """
    Returns NodeData from node_data.pkl to test with.
    """

    file = open(
        pkg_resources.resource_filename("tests.resources", "node_data.pkl"), "rb"
    )
    node_data: NodeData = pickle.load(file)
    file.close()
    return node_data


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()
    return session


@pytest.fixture
def printer() -> MagicMock:
    return MagicMock()


@pytest.fixture
def pid_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def eric(session, printer, pid_service) -> Eric:
    eric = Eric(session, pid_service)
    eric.printer = printer
    return eric
