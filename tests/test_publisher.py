from unittest import mock
from unittest.mock import MagicMock, patch

from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.model import NodeData, QualityInfo
from molgenis.bbmri_eric.printer import Printer
from molgenis.bbmri_eric.publisher import Publisher


@patch("molgenis.bbmri_eric.publisher.PidManager")
@patch("molgenis.bbmri_eric.publisher.PidService")
@patch("molgenis.bbmri_eric.publisher.Enricher")
def test_publish(
    enricher_mock, pid_manager_mock, pid_service_mock, node_data: NodeData
):
    enricher_instance = enricher_mock.return_value
    session = EricSession("url")
    session.upsert_batched = MagicMock()
    session.get_quality_info = MagicMock()
    session.get_published_biobanks = MagicMock()
    existing_biobanks = MagicMock()
    session.get_quality_info.return_value = MagicMock()
    session.get_published_biobanks.return_value = existing_biobanks
    printer = Printer()
    publisher = Publisher(session, printer, pid_service_mock)
    publisher._delete_rows = MagicMock()

    publisher.publish(node_data)

    assert enricher_mock.called_with(node_data, printer)
    enricher_instance.enrich.assert_called_once()

    assert pid_manager_mock.called_with(pid_service_mock, printer, "url")
    assert pid_manager_mock.assign_biobank_pids.called_with(node_data.biobanks)
    assert pid_manager_mock.update_biobank_pids.called_with(
        node_data.biobanks, existing_biobanks
    )

    assert session.upsert_batched.mock_calls == [
        mock.call(node_data.persons.type.base_id, node_data.persons.rows),
        mock.call(node_data.networks.type.base_id, node_data.networks.rows),
        mock.call(node_data.biobanks.type.base_id, node_data.biobanks.rows),
        mock.call(node_data.collections.type.base_id, node_data.collections.rows),
    ]

    assert publisher._delete_rows.mock_calls == [
        mock.call(node_data.collections, node_data.node),
        mock.call(node_data.biobanks, node_data.node),
        mock.call(node_data.networks, node_data.node),
        mock.call(node_data.persons, node_data.node),
    ]


@patch("molgenis.bbmri_eric.publisher.PidService")
def test_delete_rows(pid_service_mock, node_data: NodeData):
    q_info = QualityInfo(biobanks={"undeletable_id": ["quality"]}, collections={})
    session = EricSession("url")
    session.delete_list = MagicMock()
    session.get = MagicMock()
    session.get.return_value = [
        {"id": "bbmri-eric:ID:NO_OUS", "national_node": {"id": "NO"}},
        {"id": "ignore_this_row", "national_node": {"id": "XX"}},
        {"id": "delete_this_row", "national_node": {"id": "NO"}},
        {"id": "undeletable_id", "national_node": {"id": "NO"}},
    ]
    session.get_quality_info = MagicMock()
    session.get_quality_info.return_value = q_info
    session.get_published_biobanks = MagicMock()
    existing_biobanks = MagicMock()
    session.get_published_biobanks.return_value = existing_biobanks
    publisher = Publisher(session, Printer(), pid_service_mock)

    publisher._delete_rows(node_data.biobanks, node_data.node)

    session.get.assert_called_with(
        "eu_bbmri_eric_biobanks", batch_size=10000, attributes="id,national_node"
    )
    session.delete_list.assert_called_with(
        "eu_bbmri_eric_biobanks", ["delete_this_row"]
    )
    publisher.warnings = [
        "Prevented the deletion of a row that is referenced from "
        "the quality info: biobanks undeletable_id."
    ]
