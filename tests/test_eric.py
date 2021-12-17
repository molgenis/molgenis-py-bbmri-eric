from unittest import mock
from unittest.mock import MagicMock, patch

from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.eric import Eric
from molgenis.bbmri_eric.errors import EricError, EricWarning
from molgenis.bbmri_eric.model import ExternalServerNode, Node, NodeData, Source


@patch("molgenis.bbmri_eric.eric.Stager")
def test_stage_external_nodes(stager_mock):
    stager_instance = stager_mock.return_value
    error = EricError("error")
    stager_instance.stage.side_effect = [None, error]
    eric = Eric(EricSession("url"))
    nl = ExternalServerNode("NL", "will succeed", "url.nl")
    be = ExternalServerNode("BE", "wil fail", "url.be")
    eric.printer = MagicMock()

    report = eric.stage_external_nodes([nl, be])

    assert eric.printer.print_node_title.mock_calls == [mock.call(nl), mock.call(be)]
    assert stager_mock.mock_calls == [
        mock.call(eric.session, eric.printer),
        mock.call().stage(nl),
        mock.call(eric.session, eric.printer),
        mock.call().stage(be),
    ]
    assert nl not in report.errors
    assert report.errors[be] == error
    eric.printer.print_summary.assert_called_once_with(report)


@patch("molgenis.bbmri_eric.eric.Stager")
@patch("molgenis.bbmri_eric.eric.Validator")
@patch("molgenis.bbmri_eric.eric.Publisher")
@patch("molgenis.bbmri_eric.eric.PidService")
def test_publish_node_staging_fails(
    pid_service_mock, publisher_mock, validator_mock, stager_mock
):
    nl = ExternalServerNode("NL", "Netherlands", "url")
    session = EricSession("url")
    session.get_published_node_data = MagicMock()
    eric = Eric(session, pid_service_mock)
    eric.printer = MagicMock()
    error = EricError("error")
    stager_mock.return_value.stage.side_effect = error

    report = eric.publish_nodes([nl])

    eric.printer.print_node_title.assert_called_once_with(nl)
    publisher_mock.assert_called_with(session, eric.printer, pid_service_mock)
    assert stager_mock.mock_calls == [
        mock.call(session, eric.printer),
        mock.call().stage(nl),
    ]
    assert not session.get_published_node_data.called
    assert not validator_mock.called
    assert not publisher_mock.publish.called
    assert report.errors[nl] == error
    eric.printer.print_summary.assert_called_once_with(report)


@patch("molgenis.bbmri_eric.eric.Stager")
@patch("molgenis.bbmri_eric.eric.Validator")
@patch("molgenis.bbmri_eric.eric.Publisher")
@patch("molgenis.bbmri_eric.eric.PidService")
def test_publish_node_get_data_fails(
    pid_service_mock, publisher_mock, validator_mock, stager_mock
):
    nl = ExternalServerNode("NL", "Netherlands", "url")
    session = EricSession("url")
    session.get_staging_node_data = MagicMock()
    eric = Eric(session, pid_service_mock)
    eric.printer = MagicMock()
    error = EricError("error")
    session.get_staging_node_data.side_effect = error

    report = eric.publish_nodes([nl])

    eric.printer.print_node_title.assert_called_once_with(nl)
    publisher_mock.assert_called_with(session, eric.printer, pid_service_mock)
    assert stager_mock.mock_calls == [
        mock.call(session, eric.printer),
        mock.call().stage(nl),
    ]
    session.get_staging_node_data.assert_called_with(nl)
    assert not validator_mock.called
    assert not publisher_mock.publish.called
    assert report.errors[nl] == error
    eric.printer.print_summary.assert_called_once_with(report)


@patch("molgenis.bbmri_eric.eric.Stager")
@patch("molgenis.bbmri_eric.eric.Validator")
@patch("molgenis.bbmri_eric.eric.Publisher")
@patch("molgenis.bbmri_eric.eric.PidService")
def test_publish_nodes(pid_service_mock, publisher_mock, validator_mock, stager_mock):
    no = Node("NO", "succeeds with validation warnings")
    nl = ExternalServerNode("NL", "fails during publishing", "url")
    no_data = _mock_node_data(no)
    nl_data = _mock_node_data(nl)
    session = EricSession("url")
    session.get_staging_node_data = MagicMock()
    session.get_staging_node_data.side_effect = [no_data, nl_data]
    warning = EricWarning("warning")
    validator_mock.return_value.validate.side_effect = [[warning], []]
    error = EricError("error")
    publisher_mock.return_value.publish.side_effect = [[], error]
    eric = Eric(session, pid_service_mock)
    eric.printer = MagicMock()

    report = eric.publish_nodes([no, nl])

    assert eric.printer.print_node_title.mock_calls == [mock.call(no), mock.call(nl)]
    assert stager_mock.mock_calls == [
        mock.call(session, eric.printer),
        mock.call().stage(nl),
    ]
    assert validator_mock.mock_calls == [
        mock.call(no_data, eric.printer),
        mock.call().validate(),
        mock.call(nl_data, eric.printer),
        mock.call().validate(),
    ]
    assert publisher_mock.mock_calls == [
        mock.call(session, eric.printer, pid_service_mock),
        mock.call().publish(no_data),
        mock.call().publish(nl_data),
    ]
    assert no not in report.errors
    assert report.errors[nl] == error
    assert nl not in report.warnings
    assert report.warnings[no] == [warning]
    eric.printer.print_summary.assert_called_once_with(report)


def _mock_node_data(node: Node):
    return NodeData(
        node=node,
        source=Source.STAGING,
        persons=MagicMock(),
        biobanks=MagicMock(),
        networks=MagicMock(),
        collections=MagicMock(),
        table_by_type=MagicMock(),
    )
