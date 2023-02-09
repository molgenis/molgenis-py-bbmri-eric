from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.errors import EricWarning
from molgenis.bbmri_eric.model import ExternalServerNode, NodeData
from molgenis.bbmri_eric.printer import Printer
from molgenis.bbmri_eric.stager import Stager


@pytest.fixture
def external_server_init():
    with patch("molgenis.bbmri_eric.stager.ExternalServerSession") as ext_session_mock:
        yield ext_session_mock


def test_stager():
    stager = Stager(EricSession("url"), Printer())
    source_data = MagicMock()
    stager._clear_staging_area = MagicMock(name="_clear_staging_area")
    stager._import_node = MagicMock(name="_import_node")
    stager._get_source_data = MagicMock(name="_get_mock_data")
    stager._get_source_data.return_value = source_data
    node = ExternalServerNode("NL", "NL", None, "url")

    stager.stage(node)

    stager._get_source_data.assert_called_with(node)
    stager._clear_staging_area.assert_called_with(node)
    stager._import_node.assert_called_with(source_data)


def test_get_source_data(external_server_init):
    node_data = MagicMock()
    node = ExternalServerNode("NL", "Netherlands", None, "url.nl")
    source_session_mock_instance = external_server_init.return_value
    source_session_mock_instance.get_node_data.return_value = node_data

    source_data = Stager(MagicMock(), Printer())._get_source_data(node)

    external_server_init.assert_called_with(node=node)
    assert source_data == node_data


def test_check_tables(external_server_init):
    node = ExternalServerNode("NL", "Netherlands", None, "url.nl")
    session = external_server_init.return_value
    session.get.return_value = []
    session.node = node
    stager = Stager(MagicMock(), Printer())

    warnings = stager.stage(node)

    external_server_init.assert_called_with(node=node)

    assert session.get.call_count == 5

    assert warnings[0] == EricWarning("Node NL has no persons table")
    assert warnings[1] == EricWarning("Node NL has no networks table")
    assert warnings[2] == EricWarning("Node NL has no also_known_in table")
    assert warnings[3] == EricWarning("Node NL has no biobanks table")
    assert warnings[4] == EricWarning("Node NL has no collections table")


def test_clear_staging_area():
    session = EricSession("url")
    session.delete = MagicMock(name="delete")
    node = ExternalServerNode("NL", "Netherlands", None, "url.nl")

    Stager(session, Printer())._clear_staging_area(node)

    assert session.delete.mock_calls == [
        mock.call("eu_bbmri_eric_NL_collections"),
        mock.call("eu_bbmri_eric_NL_biobanks"),
        mock.call("eu_bbmri_eric_NL_also_known_in"),
        mock.call("eu_bbmri_eric_NL_networks"),
        mock.call("eu_bbmri_eric_NL_persons"),
    ]


def test_import_node(session, external_server_init):
    node_data: NodeData = MagicMock()
    converted_data = MagicMock()
    node_data.convert_to_staging.return_value = converted_data

    Stager(session, Printer())._import_node(node_data)

    session.upload_data.assert_called_with(converted_data)
