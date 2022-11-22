import csv
import json
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from time import sleep
from typing import List, Optional
from urllib.parse import quote_plus
from zipfile import ZipFile

import requests

from molgenis.bbmri_eric import utils
from molgenis.bbmri_eric.model import (
    EricData,
    ExternalServerNode,
    MixedData,
    Node,
    NodeData,
    OntologyTable,
    QualityInfo,
    Source,
    Table,
    TableMeta,
    TableType,
)
from molgenis.client import MolgenisRequestError, Session


@dataclass
class AttributesRequest:
    persons: List[str]
    networks: List[str]
    also_known_in: List[str]
    biobanks: List[str]
    collections: List[str]


class MolgenisImportError(MolgenisRequestError):
    pass


class ImportDataAction(Enum):
    """Enum of MOLGENIS import actions"""

    ADD = "add"
    ADD_UPDATE_EXISTING = "add_update_existing"
    UPDATE = "update"
    ADD_IGNORE_EXISTING = "add_ignore_existing"


class ImportMetadataAction(Enum):
    """Enum of MOLGENIS import metadata actions"""

    ADD = "add"
    UPDATE = "update"
    UPSERT = "upsert"
    IGNORE = "ignore"


class ExtendedSession(Session):
    """
    Class containing functionality that the base molgenis python client Session class
    does not have. Methods in this class could be moved to molgenis-py-client someday.
    """

    IMPORT_API_LOC = "plugin/importwizard/importFile/"

    def __init__(self, url: str, token: Optional[str] = None):
        super(ExtendedSession, self).__init__(url, token)
        self.url = self._root_url
        self.import_api = self._root_url + self.IMPORT_API_LOC

    def _raise_exception(self, ex):
        """Raises an exception with error message from molgenis, extends the original
        one as it does not account for KeyError"""
        message = ex.args[0]
        if ex.response.content:
            try:
                error = json.loads(ex.response.content.decode("utf-8"))["errors"][0][
                    "message"
                ]
            except ValueError:  # Cannot parse JSON
                error = ex.response.content
            except KeyError:  # Cannot parse JSON
                error = json.loads(ex.response.content.decode("utf-8"))["detail"]
            error_msg = "{}: {}".format(message, error)
            raise MolgenisRequestError(error_msg, ex.response)
        else:
            raise MolgenisRequestError("{}".format(message))

    def get_uploadable_data(self, entity_type_id: str, *args, **kwargs) -> List[dict]:
        """
        Returns all the rows of an entity type, transformed to the uploadable format.
        """
        rows = self.get(entity_type_id, *args, **kwargs)
        return utils.to_upload_format(rows)

    def update(self, entity_type_id: str, entities: List[dict]):
        """Updates multiple entities."""
        response = self._session.put(
            self._api_url + "v2/" + quote_plus(entity_type_id),
            headers=self._get_token_header_with_content_type(),
            data=json.dumps({"entities": entities}),
        )

        try:
            response.raise_for_status()
        except requests.RequestException as ex:
            self._raise_exception(ex)

        return response

    def get_meta(self, entity_type_id: str) -> TableMeta:
        """Similar to get_entity_meta_data() of the parent Session class, but uses the
        newer Metadata API instead of the REST API V1."""
        response = self._session.get(
            self._api_url + "metadata/" + quote_plus(entity_type_id),
            headers=self._get_token_header(),
        )
        try:
            response.raise_for_status()
        except requests.RequestException as ex:
            self._raise_exception(ex)

        return TableMeta(meta=response.json())

    def import_emx_file(
        self,
        file: Path,
        action: ImportDataAction,
        metadata_action: ImportMetadataAction,
    ):
        """
        Imports a file with the Import API.
        :param file: the Path to the file
        :param action: the ImportDataAction to use when importing
        :param metadata_action: the ImportMetadataAction to use when importing
        """
        response = self._session.post(
            self.import_api,
            headers=self._get_token_header(),
            files={"file": open(file, "rb")},
            params={"action": action.value, "metadataAction": metadata_action.value},
        )

        try:
            response.raise_for_status()
        except requests.RequestException as ex:
            self._raise_exception(ex)

        self._await_import_job(response.text.split("/")[-1])

    def _await_import_job(self, job: str):
        while True:
            sleep(5)
            import_run = self.get_by_id(
                "sys_ImportRun", job, attributes="status,message"
            )
            if import_run["status"] == "FAILED":
                raise MolgenisImportError(import_run["message"])
            if import_run["status"] != "RUNNING":
                return


class EricSession(ExtendedSession):
    """
    A session with a BBMRI ERIC directory. Contains methods to get national nodes,
    their (staging) data and quality information.
    """

    def __init__(self, *args, **kwargs):
        super(EricSession, self).__init__(*args, **kwargs)

    NODES_TABLE = "eu_bbmri_eric_national_nodes"

    def get_ontology(
        self,
        entity_type_id: str,
        parent_attr: str = "parentId",
    ) -> OntologyTable:
        """
        Retrieves an ontology table.
        :param entity_type_id: the identifier of the table
        :param parent_attr: the name of the attribute that contains the parent relation
        :return: an OntologyTable
        """
        rows = self.get_uploadable_data(
            entity_type_id, batch_size=10000, attributes=f"id,{parent_attr},ontology"
        )
        meta = self.get_meta(entity_type_id)
        return OntologyTable.of(meta, rows, parent_attr)

    def get_quality_info(self) -> QualityInfo:
        """
        Retrieves the quality information identifiers for biobanks and collections.
        :return: a QualityInfo object
        """

        biobank_qualities = self.get(
            "eu_bbmri_eric_bio_qual_info",
            batch_size=10000,
            attributes="id,biobank,assess_level_bio",
        )
        collection_qualities = self.get(
            "eu_bbmri_eric_col_qual_info",
            batch_size=10000,
            attributes="id,collection,assess_level_col",
        )

        biobanks = utils.to_upload_format(biobank_qualities)
        collections = utils.to_upload_format(collection_qualities)

        bb_qual = defaultdict(list)
        bb_level = defaultdict(list)
        coll_qual = defaultdict(list)
        coll_level = defaultdict(list)
        for row in biobanks:
            bb_qual[row["biobank"]].append(row["id"])
            bb_level[row["biobank"]].append(row["assess_level_bio"])
        for row in collections:
            coll_qual[row["collection"]].append(row["id"])
            coll_level[row["collection"]].append(row["assess_level_col"])

        return QualityInfo(
            biobanks=bb_qual,
            collections=coll_qual,
            biobank_levels=bb_level,
            collection_levels=coll_level,
        )

    def get_node(self, code: str) -> Node:
        """
        Retrieves a single Node object from the national nodes table.
        :param code: node to get by code
        :return: Node object
        """
        nodes = self.get(self.NODES_TABLE, q=f"id=={code}")
        self._validate_codes([code], nodes)
        return self._to_nodes(nodes)[0]

    def get_nodes(self, codes: List[str] = None) -> List[Node]:
        """
        Retrieves a list of Node objects from the national nodes table. Will return
        all nodes or some nodes if 'codes' is specified.
        :param codes: nodes to get by code
        :return: list of Node objects
        """
        if codes:
            nodes = self.get(self.NODES_TABLE, q=f"id=in=({','.join(codes)})")
        else:
            nodes = self.get(self.NODES_TABLE)

        if codes:
            self._validate_codes(codes, nodes)
        return self._to_nodes(nodes)

    def get_external_node(self, code: str) -> ExternalServerNode:
        """
        Retrieves a single ExternalServerNode object from the national nodes table.
        :param code: node to get by code
        :return: ExternalServerNode object
        """
        nodes = self.get(self.NODES_TABLE, q=f"id=={code};dns!=''")
        self._validate_codes([code], nodes)
        return self._to_nodes(nodes)[0]

    def get_external_nodes(self, codes: List[str] = None) -> List[ExternalServerNode]:
        """
        Retrieves a list of ExternalServerNode objects from the national nodes table.
        Will return all nodes or some nodes if 'codes' is specified.
        :param codes: nodes to get by code
        :return: list of ExternalServerNode objects
        """
        if codes:
            nodes = self.get(self.NODES_TABLE, q=f"id=in=({','.join(codes)});dns!=''")
        else:
            nodes = self.get(self.NODES_TABLE, q="dns!=''")

        if codes:
            self._validate_codes(codes, nodes)
        return self._to_nodes(nodes)

    @staticmethod
    def _validate_codes(codes: List[str], nodes: List[dict]):
        """Raises a KeyError if a requested node code was not found."""
        retrieved_codes = {node["id"] for node in nodes}
        for code in codes:
            if code not in retrieved_codes:
                raise KeyError(f"Unknown code: {code}")

    @staticmethod
    def _to_nodes(nodes: List[dict]):
        """Maps rows to Node or ExternalServerNode objects."""
        result = list()
        for node in nodes:
            if "dns" not in node:
                result.append(Node(code=node["id"], description=node["description"]))
            else:
                result.append(
                    ExternalServerNode(
                        code=node["id"],
                        description=node["description"],
                        url=node["dns"],
                    )
                )
        return result

    def get_staging_node_data(self, node: Node) -> NodeData:
        """
        Gets the five tables that belong to a single node's staging area.

        :param Node node: the node to get the staging data for
        :return: a NodeData object
        """
        tables = dict()
        for table_type in TableType.get_import_order():
            id_ = node.get_staging_id(table_type)
            meta = self.get_meta(id_)

            tables[table_type.value] = Table.of(
                table_type=table_type,
                meta=meta,
                rows=self.get_uploadable_data(id_, batch_size=10000),
            )

        return NodeData.from_dict(node=node, source=Source.STAGING, tables=tables)

    def get_published_node_data(self, node: Node) -> NodeData:
        """
        Gets the five tables that belong to a single node from the published tables.
        Filters the rows based on the national_node field.

        :param Node node: the node to get the published data for
        :return: a NodeData object
        """

        tables = dict()
        for table_type in TableType.get_import_order():
            id_ = table_type.base_id
            meta = self.get_meta(id_)

            tables[table_type.value] = Table.of(
                table_type=table_type,
                meta=meta,
                rows=self.get_uploadable_data(
                    id_, batch_size=10000, q=f"national_node=={node.code}"
                ),
            )

        return NodeData.from_dict(node=node, source=Source.PUBLISHED, tables=tables)

    def get_published_data(
        self, nodes: List[Node], attributes: AttributesRequest
    ) -> MixedData:
        """
        Gets the five tables that belong to one or more nodes from the published tables.
        Filters the rows based on the national_node field.

        :param List[Node] nodes: the node(s) to get the published data for
        :param AttributesRequest attributes: the attributes to get for each table
        :return: an EricData object
        """

        if len(nodes) == 0:
            raise ValueError("No nodes provided")

        attributes = asdict(attributes)
        codes = [node.code for node in nodes]
        tables = dict()
        for table_type in TableType.get_import_order():
            id_ = table_type.base_id
            meta = self.get_meta(id_)
            attrs = attributes[table_type.value]

            tables[table_type.value] = Table.of(
                table_type=table_type,
                meta=meta,
                rows=self.get_uploadable_data(
                    id_,
                    batch_size=10000,
                    q=f"national_node=in=({','.join(codes)})",
                    attributes=",".join(attrs),
                ),
            )

        return MixedData.from_mixed_dict(source=Source.PUBLISHED, tables=tables)

    def import_as_csv(self, data: EricData):
        """
        Converts the five tables of an EricData object to CSV, bundles them in
        a ZIP archive and imports them through the import API.
        :param data: an EricData object
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = self._create_emx_archive(data, tmpdir)
            self.import_emx_file(
                archive,
                action=ImportDataAction.ADD_UPDATE_EXISTING,
                metadata_action=ImportMetadataAction.IGNORE,
            )

    @classmethod
    def _create_emx_archive(cls, data: EricData, directory: str) -> Path:
        archive_name = f"{directory}/archive.zip"
        with ZipFile(archive_name, "w") as archive:
            for table in data.import_order:
                file_name = f"{table.full_name}.csv"
                file_path = f"{directory}/{file_name}"
                cls._create_csv(table, file_path)
                archive.write(file_path, file_name)
        return Path(archive_name)

    @staticmethod
    def _create_csv(table: Table, file_name: str):
        with open(file_name, "w", encoding="utf-8") as fp:
            writer = csv.DictWriter(
                fp,
                fieldnames=table.meta.attributes,
                quoting=csv.QUOTE_ALL,
                extrasaction="ignore",
            )
            writer.writeheader()
            for row in table.rows:
                for key, value in row.items():
                    if isinstance(value, list):
                        row[key] = ",".join(value)
                writer.writerow(row)


class ExternalServerSession(ExtendedSession):
    """
    A session with a national node's external server (for example BBMRI-NL).
    """

    def __init__(self, node: ExternalServerNode, *args, **kwargs):
        super(ExternalServerSession, self).__init__(url=node.url, *args, **kwargs)
        self.node = node

    def get_node_data(self) -> NodeData:
        """
        Gets the five tables of this node's external server.

        :return: a NodeData object
        """

        tables = dict()
        for table_type in TableType.get_import_order():
            id_ = table_type.base_id
            if not self.get("sys_md_EntityType", q=f"id=={id_}"):
                tables[table_type.value] = Table.of_placeholder(table_type)
            else:
                meta = self.get_meta(id_)
                tables[table_type.value] = Table.of(
                    table_type=table_type,
                    meta=meta,
                    rows=self.get_uploadable_data(id_, batch_size=10000),
                )

        return NodeData.from_dict(
            node=self.node, source=Source.EXTERNAL_SERVER, tables=tables
        )
