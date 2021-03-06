from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from molgenis.bbmri_eric.bbmri_client import EricSession
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
    node = ExternalServerNode("NL", "NL", "url")

    stager.stage(node)

    stager._get_source_data.assert_called_with(node)
    stager._clear_staging_area.assert_called_with(node)
    stager._import_node.assert_called_with(source_data)


def test_get_source_data(external_server_init):
    node_data = MagicMock()
    node = ExternalServerNode("NL", "Netherlands", "url.nl")
    source_session_mock_instance = external_server_init.return_value
    source_session_mock_instance.get_node_data.return_value = node_data

    source_data = Stager(MagicMock(), Printer())._get_source_data(node)

    external_server_init.assert_called_with(node=node)
    assert source_data == node_data


def test_clear_staging_area():
    session = EricSession("url")
    session.delete = MagicMock(name="delete")
    node = ExternalServerNode("NL", "Netherlands", "url.nl")

    Stager(session, Printer())._clear_staging_area(node)

    assert session.delete.mock_calls == [
        mock.call("eu_bbmri_eric_NL_collections"),
        mock.call("eu_bbmri_eric_NL_biobanks"),
        mock.call("eu_bbmri_eric_NL_networks"),
        mock.call("eu_bbmri_eric_NL_persons"),
    ]


def test_import_node(session, external_server_init):
    node_data: NodeData = MagicMock()
    converted_data = MagicMock()
    node_data.convert_to_staging.return_value = converted_data

    Stager(session, Printer())._import_node(node_data)

    session.import_as_csv.assert_called_with(converted_data)
