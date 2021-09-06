from typing import List, Set

from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.enricher import Enricher
from molgenis.bbmri_eric.errors import EricError, EricWarning
from molgenis.bbmri_eric.model import Node, NodeData, QualityInfo, Table
from molgenis.bbmri_eric.printer import Printer
from molgenis.client import MolgenisRequestError


class Publisher:
    """
    This class is responsible for copying data from the staging areas to the combined
    public tables.
    """

    def __init__(self, session: EricSession, printer: Printer):
        self.session = session
        self.printer = printer
        self.warnings: List[EricWarning] = []
        self.quality_info: QualityInfo = session.get_quality_info()

    def publish(self, node_data: NodeData) -> List[EricWarning]:
        """
        Publishes data from the provided node to the production tables. Before being
        copied over, the data is enriched with additional information.
        """
        self.warnings = []
        self.printer.print(f"✏️ Enriching data of node {node_data.node.code}")
        self.printer.indent()
        Enricher(node_data, self.quality_info, self.printer).enrich()
        self.printer.dedent()

        self.printer.print(f"✉️ Copying data of node {node_data.node.code}")
        self._copy_node_data(node_data)
        return self.warnings

    def _copy_node_data(self, node_data: NodeData):
        """
        Copies the data of a staging area to the combined tables. This happens in two
        phases:
        1. New/existing rows are upserted in the combined tables
        2. Removed rows are deleted from the combined tables
        """
        self.printer.indent()
        for table in node_data.import_order:
            self.printer.print(f"Upserting rows in {table.type.base_id}")
            try:
                #print(table.rows)
                self.session.upsert_batched(table.type.base_id, table.rows)
            except MolgenisRequestError as e:
                raise EricError(f"Error upserting rows to {table.type.base_id}") from e

        for table in reversed(node_data.import_order):
            self.printer.print(f"Deleting rows in {table.type.base_id}")
            try:
                self._delete_rows(table, node_data.node)
            except MolgenisRequestError as e:
                raise EricError(f"Error deleting rows from {table.type.base_id}") from e
        self.printer.dedent()

    def _delete_rows(self, table: Table, node: Node):
        """
        Deletes rows from a combined table that are not present in the staging area's
        table. If a row is referenced from the quality info tables, it is not deleted
        but a warning will be raised.

        :param Table table: the staging area's table
        :node Node node: the Node that is being published
        """
        # Compare the ids from staging and production to see what was deleted
        staging_ids = {row["id"] for row in table.rows}
        production_ids = self._get_production_ids(table, node)
        print('node', node)
        print('table is', table.type.base_id)
        print('aantal staging_ids', type(staging_ids), len(staging_ids))
        print('aantal production_ids', type(production_ids), len(production_ids))
        deleted_ids = production_ids.difference(staging_ids)

        print('deleted_list', deleted_ids)
        # Remove ids that we are not allowed to delete
        undeletable_ids = self.quality_info.get_qualities(table.type).keys()

        print('aantal undeletable_ids', len(undeletable_ids))

        deletable_ids = deleted_ids.difference(undeletable_ids)
        print('deletable_ids', deletable_ids)

        # Actually delete the rows in the combined tables
        if deletable_ids:
            self.printer.print(f"Deleting {len(deletable_ids)} rows in {table.type.base_id}")
            self.session.delete_list(table.type.base_id, list(deletable_ids))

        # Show warning for every id that we prevented deletion of
        if deleted_ids != deletable_ids:
            for id_ in undeletable_ids:
                if id_ in deleted_ids:
                    warning = EricWarning(
                        f"Prevented the deletion of a row that is referenced from "
                        f"the quality info: {table.type.value} {id_}."
                    )
                    self.printer.print_warning(warning)
                    self.warnings.append(warning)

    def _get_production_ids(self, table: Table, node: Node) -> Set[str]:
        try:
            rows = self.session.get(
                table.type.base_id, batch_size=10000, attributes="id,national_node"
            )
        except MolgenisRequestError as e:
            raise EricError(f"Error getting rows from {table.type.base_id}") from e

#        return {row["id"] for row in rows if row.get("national_node", "") == node.code}
        return {row["id"] for row in rows if row.get("national_node", {}).get("id", "") == node.code}
