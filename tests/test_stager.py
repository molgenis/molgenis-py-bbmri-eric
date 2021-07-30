from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from molgenis.bbmri_eric._model import ExternalServerNode, NodeData
from molgenis.bbmri_eric._printer import Printer
from molgenis.bbmri_eric._stager import Stager
from molgenis.bbmri_eric.bbmri_client import BbmriSession
from molgenis.bbmri_eric.errors import EricError
from molgenis.client import MolgenisRequestError


def test_stager():
    stager = Stager(BbmriSession("url"), Printer())
    stager._clear_staging_area = MagicMock(name="_clear_staging_area")
    stager._import_node = MagicMock(name="_import_node")
    node = ExternalServerNode("NL", "NL", "url")

    stager.stage(node)

    stager._clear_staging_area.assert_called_with(node)
    stager._import_node.assert_called_with(node)


def test_clear_staging_area():
    session = BbmriSession("url")
    session.delete = MagicMock(name="delete")
    node = ExternalServerNode("NL", "Netherlands", "url.nl")

    Stager(session, Printer())._clear_staging_area(node)

    assert session.delete.mock_calls == [
        mock.call("eu_bbmri_eric_NL_collections"),
        mock.call("eu_bbmri_eric_NL_biobanks"),
        mock.call("eu_bbmri_eric_NL_networks"),
        mock.call("eu_bbmri_eric_NL_persons"),
    ]


def test_clear_staging_area_error():
    session = BbmriSession("url")
    session.delete = MagicMock(name="delete")
    session.delete.side_effect = MolgenisRequestError("error")
    node = ExternalServerNode("NL", "Netherlands", "url.nl")

    with pytest.raises(EricError) as e:
        Stager(session, Printer())._clear_staging_area(node)

    assert str(e.value) == "Error clearing staging area of node NL"


@patch("molgenis.bbmri_eric._stager.BbmriSession")
def test_import_node(session_mock, node_data: NodeData):
    source_session_mock_instance = session_mock.return_value
    source_session_mock_instance.get_node_data.return_value = node_data
    session = BbmriSession("url")
    session.add_batched = MagicMock(name="add_batched")
    node = ExternalServerNode("NO", "Norway", "url")

    Stager(session, Printer())._import_node(node)

    session_mock.assert_called_with(url=node.url)
    source_session_mock_instance.get_node_data.assert_called_with(node, staging=False)
    assert session.add_batched.mock_calls == [
        mock.call("eu_bbmri_eric_NO_persons", node_data.persons.rows),
        mock.call("eu_bbmri_eric_NO_networks", node_data.networks.rows),
        mock.call("eu_bbmri_eric_NO_biobanks", node_data.biobanks.rows),
        mock.call("eu_bbmri_eric_NO_collections", node_data.collections.rows),
    ]


@patch("molgenis.bbmri_eric._stager.BbmriSession")
def test_import_node_get_node_error(session_mock, node_data: NodeData):
    source_session_mock_instance = session_mock.return_value
    source_session_mock_instance.get_node_data.side_effect = MolgenisRequestError("")
    session = BbmriSession("url")
    node = ExternalServerNode("NO", "Norway", "url")

    with pytest.raises(EricError) as e:
        Stager(session, Printer())._import_node(node)

    assert str(e.value) == "Error getting data from url"


@patch("molgenis.bbmri_eric._stager.BbmriSession")
def test_import_node_copy_node_error(session_mock, node_data: NodeData):
    source_session_mock_instance = session_mock.return_value
    source_session_mock_instance.get_node_data.return_value = node_data
    session = BbmriSession("url")
    session.add_batched = MagicMock(name="add_batched")
    session.add_batched.side_effect = MolgenisRequestError("error")
    node = ExternalServerNode("NO", "Norway", "url")

    with pytest.raises(EricError) as e:
        Stager(session, Printer())._import_node(node)

    assert str(e.value) == "Error copying from url to staging area"
