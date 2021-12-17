from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from molgenis.bbmri_eric.model import NodeData, QualityInfo


@pytest.fixture
def enricher_init():
    with patch("molgenis.bbmri_eric.publisher.Enricher") as enricher_mock:
        yield enricher_mock


@pytest.fixture
def pid_manager_init():
    with patch("molgenis.bbmri_eric.publisher.PidManager") as pid_manager_mock:
        yield pid_manager_mock


def test_publish(
    publisher,
    enricher_init,
    pid_manager_init,
    pid_service,
    node_data: NodeData,
    session,
    printer,
):
    existing_biobanks = MagicMock()
    session.get_published_biobanks.return_value = existing_biobanks
    publisher._delete_rows = MagicMock()

    publisher.publish(node_data)

    assert enricher_init.called_with(node_data, printer)
    enricher_init.return_value.enrich.assert_called_once()

    assert pid_manager_init.called_with(pid_service, printer, "url")
    assert pid_manager_init.assign_biobank_pids.called_with(node_data.biobanks)
    assert pid_manager_init.update_biobank_pids.called_with(
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


def test_delete_rows(publisher, pid_service, node_data: NodeData, session):
    session.get.return_value = [
        {"id": "bbmri-eric:ID:NO_OUS", "national_node": {"id": "NO"}},
        {"id": "ignore_this_row", "national_node": {"id": "XX"}},
        {"id": "delete_this_row", "national_node": {"id": "NO"}},
        {"id": "undeletable_id", "national_node": {"id": "NO"}},
    ]
    publisher.quality_info = QualityInfo(
        biobanks={"undeletable_id": ["quality"]}, collections={}
    )

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
