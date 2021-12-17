from unittest.mock import MagicMock

from molgenis.bbmri_eric.enricher import Enricher
from molgenis.bbmri_eric.model import QualityInfo
from molgenis.bbmri_eric.printer import Printer


def test_enricher_node_codes(node_data):
    for table in node_data.import_order:
        assert "national_node" not in table.rows[0]

    Enricher(node_data, MagicMock(), Printer(), MagicMock())._set_national_node_code()

    for table in node_data.import_order:
        assert table.rows[0]["national_node"] == "NO"


def test_enricher_commercial_use():
    node_data = MagicMock()
    node_data.collections.rows = [
        {"biobank": "biobank1", "collaboration_commercial": True},
        {"biobank": "biobank1", "collaboration_commercial": False},
        {"biobank": "biobank1"},
        {"biobank": "biobank2", "collaboration_commercial": True},
        {"biobank": "biobank2", "collaboration_commercial": False},
        {"biobank": "biobank2"},
        {"biobank": "biobank3", "collaboration_commercial": True},
        {"biobank": "biobank3", "collaboration_commercial": False},
        {"biobank": "biobank3"},
    ]
    node_data.biobanks.rows_by_id = {
        "biobank1": dict(),
        "biobank2": {"collaboration_commercial": True},
        "biobank3": {"collaboration_commercial": False},
    }

    Enricher(node_data, MagicMock(), Printer(), MagicMock())._set_commercial_use_bool()

    assert node_data.collections.rows[0]["commercial_use"] is True
    assert node_data.collections.rows[1]["commercial_use"] is False
    assert node_data.collections.rows[2]["commercial_use"] is True
    assert node_data.collections.rows[3]["commercial_use"] is True
    assert node_data.collections.rows[4]["commercial_use"] is False
    assert node_data.collections.rows[5]["commercial_use"] is True
    assert node_data.collections.rows[6]["commercial_use"] is False
    assert node_data.collections.rows[7]["commercial_use"] is False
    assert node_data.collections.rows[8]["commercial_use"] is False


def test_enricher_quality(node_data):
    q_info = QualityInfo(
        biobanks={
            "bbmri-eric:ID:NO_BIOBANK1": ["quality1", "quality2"],
            "bbmri-eric:ID:NO_CoronaTrondelag": ["quality3"],
        },
        collections={
            "bbmri-eric:ID:NO_bbmri-eric:ID:NO_CancerBiobankOUH:collection"
            ":all_samples_samples": ["quality1"]
        },
    )

    Enricher(node_data, q_info, Printer(), MagicMock())._set_quality_info()

    assert node_data.biobanks.rows_by_id["bbmri-eric:ID:NO_BIOBANK1"]["quality"] == [
        "quality1",
        "quality2",
    ]
    assert "quality" not in node_data.biobanks.rows_by_id["bbmri-eric:ID:NO_Janus"]
    assert node_data.biobanks.rows_by_id["bbmri-eric:ID:NO_CoronaTrondelag"][
        "quality"
    ] == ["quality3"]
    assert node_data.collections.rows_by_id[
        "bbmri-eric:ID:NO_bbmri-eric:ID:NO_CancerBiobankOUH:collection"
        ":all_samples_samples"
    ]["quality"] == ["quality1"]
    assert (
        "quality"
        not in node_data.collections.rows_by_id[
            "bbmri-eric:ID:NO_moba:collection:all_samples"
        ]
    )
