from typing import List

from molgenis.bbmri_eric import nodes as national_nodes
from molgenis.bbmri_eric._model import ExternalServerNode, Node
from molgenis.bbmri_eric._publisher import Publisher, PublishReport
from molgenis.bbmri_eric._stager import Stager, StagingReport
from molgenis.bbmri_eric.bbmri_client import BbmriSession


class Eric:
    """
    Main class for doing operations on the ERIC directory.

    Attributes:
        session (BbmriSession): The session with an ERIC directory
    """

    def __init__(self, session: BbmriSession):
        """
        Parameters:
            session: an (authenticated) session with an ERIC directory
        """
        self.session = session

    def stage_all_external_nodes(self) -> StagingReport:
        """
        Stages all data from all external nodes in the ERIC directory.
        """

        return Stager(self.session).stage(national_nodes.get_all_external_nodes())

    def stage_external_nodes(self, nodes: List[ExternalServerNode]) -> StagingReport:
        """
        Stages all data from the provided external nodes in the ERIC directory.

        Parameters:
            nodes (List[ExternalServerNode]): The list of external nodes to stage
        """
        return Stager(self.session).stage(nodes)

    def publish_all_nodes(self) -> PublishReport:
        """
        Publishes data from all nodes to the production tables in the ERIC
        directory.
        """
        return Publisher(self.session).publish(national_nodes.get_all_nodes())

    def publish_nodes(self, nodes: List[Node]) -> PublishReport:
        """
        Publishes data from the provided nodes to the production tables in the ERIC
        directory.

        Parameters:
            nodes (List[Node]): The list of nodes to publish
        """
        return Publisher(self.session).publish(nodes)
