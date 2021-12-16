from molgenis.bbmri_eric.model import NodeData, QualityInfo, Table
from molgenis.bbmri_eric.printer import Printer


class Enricher:
    """
    The published tables have a few extra attributes that the staging tables do not.
    This class is responsible for adding those attributes so the staging tables can be
    published correctly.
    """

    def __init__(
        self,
        node_data: NodeData,
        quality: QualityInfo,
        printer: Printer,
        existing_biobanks: Table,
    ):
        self.node_data = node_data
        self.quality = quality
        self.printer = printer
        self.existing_biobank_pids = existing_biobanks.rows_by_id

    def enrich(self):
        """
        Enriches the data of a node:
        1. Sets the commercial use boolean
        2. Adds the national node code to all rows
        3. Sets the quality info field for biobanks and collections
        4. Adds PIDs to biobanks
        """
        self._set_commercial_use_bool()
        self._set_national_node_code()
        self._set_quality_info()
        self._set_biobank_pids()

    def _set_commercial_use_bool(self):
        """
        Takes the data of a Node and sets the commercial_use boolean of all collections
        based on a set of criteria.
        """

        self.printer.print("Setting 'commercial_use' booleans")
        for collection in self.node_data.collections.rows:

            def is_true(row: dict, attr: str):
                # if the value is not entered, it is also considered true
                return attr not in row or row[attr] is True

            biobank_id = collection["biobank"]
            biobank = self.node_data.biobanks.rows_by_id[biobank_id]

            collection["commercial_use"] = is_true(
                biobank, "collaboration_commercial"
            ) and is_true(collection, "collaboration_commercial")

    def _set_national_node_code(self):
        """
        Adds the national node code to each row of every table of a node.
        """
        self.printer.print("Adding national node codes")
        for table in self.node_data.import_order:
            for row in table.rows:
                row["national_node"] = self.node_data.node.code

    def _set_quality_info(self):
        """
        Adds the one_to_many "quality" field to the biobank and collection tables based
        on the quality info tables.
        """
        self.printer.print("Adding quality information")
        self._set_quality_for_table(self.node_data.biobanks)
        self._set_quality_for_table(self.node_data.collections)

    def _set_quality_for_table(self, table: Table):
        for row in table.rows:
            qualities = self.quality.get_qualities(table.type)
            quality_ids = qualities.get(row["id"], [])
            if quality_ids:
                row["quality"] = quality_ids

    def _set_biobank_pids(self):
        """
        Adds the PIDs for existing biobanks.
        """
        self.printer.print("Adding existing PIDs to biobanks")
        for biobank in self.node_data.biobanks.rows:
            biobank_id = biobank["id"]
            if biobank_id in self.existing_biobank_pids:
                biobank["pid"] = self.existing_biobank_pids[biobank_id]["pid"]
