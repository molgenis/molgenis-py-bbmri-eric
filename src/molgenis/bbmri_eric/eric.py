from typing import List, Optional

from pyhandle.clientcredentials import PIDClientCredentials
from pyhandle.handleclient import PyHandleClient

from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.errors import EricError, ErrorReport, requests_error_handler
from molgenis.bbmri_eric.model import ExternalServerNode, Node, NodeData
from molgenis.bbmri_eric.printer import Printer
from molgenis.bbmri_eric.publisher import Publisher
from molgenis.bbmri_eric.stager import Stager
from molgenis.bbmri_eric.validation import Validator
from molgenis.client import MolgenisRequestError


class Eric:
    """
    Main class for doing operations on the ERIC directory.
    """

    def __init__(self, session: EricSession):
        """
        :param BbmriSession session: an authenticated session with an ERIC directory
        """
        self.session = session
        self.handle_client: Optional[PyHandleClient] = None
        self.printer = Printer()

    def configure_handle_client(self, credentials_json: str):
        """
        Configures a PyHandleClient based on the credentials JSON file.

        :param credentials_json: an absolute path to the credentials file for PyHandle
        :return: a PyHandleClient
        """
        credentials = PIDClientCredentials.load_from_JSON(credentials_json)
        self.handle_client = PyHandleClient("rest").instantiate_with_credentials(
            credentials
        )

    def stage_external_nodes(self, nodes: List[ExternalServerNode]) -> ErrorReport:
        """
        Stages all data from the provided external nodes in the ERIC directory.

        Parameters:
            nodes (List[ExternalServerNode]): The list of external nodes to stage
        """
        report = ErrorReport(nodes)
        for node in nodes:
            self.printer.print_node_title(node)
            try:
                self._stage_node(node)
            except EricError as e:
                self.printer.print_error(e)
                report.add_error(node, e)

        self.printer.print_summary(report)
        return report

    def publish_nodes(self, nodes: List[Node]) -> ErrorReport:
        """
        Publishes data from the provided nodes to the production tables in the ERIC
        directory.

        Parameters:
            nodes (List[Node]): The list of nodes to publish
        """
        report = ErrorReport(nodes)
        publisher = Publisher(self.session, self.printer)
        for node in nodes:
            self.printer.print_node_title(node)
            try:
                self._publish_node(node, report, publisher)
            except EricError as e:
                self.printer.print_error(e)
                report.add_error(node, e)

        self.printer.print_summary(report)
        return report

    @requests_error_handler
    def _publish_node(self, node: Node, report: ErrorReport, publisher: Publisher):
        # Stage the data if this node has an external server
        if isinstance(node, ExternalServerNode):
            self._stage_node(node)

        # Get the data from the staging area
        node_data = self._get_node_data(node)

        # Validate all the rows in the staging area
        self._validate_node(node_data, report)

        # Copy the data from staging to the combined tables
        self._publish_node_data(node_data, publisher, report)

    @requests_error_handler
    def _stage_node(self, node: ExternalServerNode):
        self.printer.print_sub_header(f"📥 Staging data of node {node.code}")
        self.printer.indent()

        Stager(self.session, self.printer).stage(node)

        self.printer.dedent()

    def _publish_node_data(
        self, node_data: NodeData, publisher: Publisher, report: ErrorReport
    ):
        self.printer.print_sub_header(f"📤 Publishing node {node_data.node.code}")
        self.printer.indent()

        warnings = publisher.publish(node_data)
        report.add_warnings(node_data.node, warnings)

        self.printer.dedent()

    def _validate_node(self, node_data: NodeData, report: ErrorReport):
        self.printer.print_sub_header(
            f"🔎 Validating staging data of node {node_data.node.code}"
        )
        self.printer.indent()

        warnings = Validator(node_data, self.printer).validate()
        if warnings:
            report.add_warnings(node_data.node, warnings)

        self.printer.dedent()

    def _get_node_data(self, node: Node) -> NodeData:
        try:
            self.printer.print_sub_header(
                f"📦 Retrieving staging data of node {node.code}"
            )
            return self.session.get_staging_node_data(node)
        except MolgenisRequestError as e:
            raise EricError(f"Error retrieving data of node {node.code}") from e
