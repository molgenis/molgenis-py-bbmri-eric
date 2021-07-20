from typing import List

from molgenis.bbmri_eric import nodes as nnodes
from molgenis.bbmri_eric._model import ExternalServerNode, Node
from molgenis.bbmri_eric._publisher import Publisher
from molgenis.bbmri_eric._stager import Stager
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

    def stage_all_external_nodes(self):
        """
        Stages all data from all external nodes in the ERIC directory.
        """

        Stager(self.session).stage(nnodes.get_all_external_nodes())

    def stage_external_nodes(self, nodes: List[ExternalServerNode]):
        """
        Stages all data from the provided external nodes in the ERIC directory.

        Parameters:
            nodes (List[ExternalServerNode]): The list of external nodes to stage
        """
        Stager(self.session).stage(nodes)

    def publish_all_nodes(self):
        """
        Publishes data from all nodes to the production tables in the ERIC
        directory.
        """
        Publisher(self.session).publish(nnodes.get_all_nodes())

    def publish_nodes(self, nodes: List[Node]):
        """
        Publishes data from the provided nodes to the production tables in the ERIC
        directory.

        Parameters:
            nodes (List[Node]): The list of nodes to publish
        """
        Publisher(self.session).publish(nodes)
