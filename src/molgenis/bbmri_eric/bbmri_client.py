import json
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from urllib.parse import quote_plus

import requests

from molgenis.bbmri_eric import utils
from molgenis.bbmri_eric.model import (
    ExternalServerNode,
    Node,
    NodeData,
    QualityInfo,
    Source,
    Table,
    TableType,
)
from molgenis.bbmri_eric.utils import batched
from molgenis.client import Session


@dataclass(frozen=True)
class ReferenceAttributeNames:
    """
    Object containing names of all reference attributes of an entity type.
    """

    xrefs: List[str]
    mrefs: List[str]
    categoricals: List[str]
    categorical_mrefs: List[str]
    one_to_manys: List[str]


class ReferenceType(Enum):
    XREF = "XREF"
    MREF = "MREF"
    CATEGORICAL = "CATEGORICAL"
    CATEGORICAL_MREF = "CATEGORICAL_MREF"
    ONE_TO_MANY = "ONE_TO_MANY"


class ExtendedSession(Session):
    """
    Class containing functionality that the base molgenis python client Session class
    does not have. Methods in this class could be moved to molgenis-py-client someday.
    """

    def __init__(self, url: str, token: Optional[str] = None):
        super(ExtendedSession, self).__init__(url, token)
        self.url = url

    def get_reference_attribute_names(self, id_: str) -> ReferenceAttributeNames:
        """
        Gets the names of all reference attributes of an entity type

        Parameters:
            id_ (str): the id of the entity type
        """
        attrs = self.get_entity_meta_data(id_)["attributes"]

        result = defaultdict(list)
        for name, attr in attrs.items():
            try:
                type_ = ReferenceType[attr["fieldType"]]
                result[type_].append(name)
            except KeyError:
                pass

        return ReferenceAttributeNames(
            xrefs=result.get(ReferenceType.XREF, []),
            mrefs=result.get(ReferenceType.MREF, []),
            categoricals=result.get(ReferenceType.CATEGORICAL, []),
            categorical_mrefs=result.get(ReferenceType.CATEGORICAL_MREF, []),
            one_to_manys=result.get(ReferenceType.ONE_TO_MANY, []),
        )

    def get_uploadable_data(self, entity_type_id: str, *args, **kwargs) -> List[dict]:
        """
        Returns all the rows of an entity type, transformed to the uploadable format.
        """
        rows = self.get(entity_type_id, *args, **kwargs)
        ref_names = self.get_reference_attribute_names(entity_type_id)
        return utils.to_upload_format(rows, ref_names.one_to_manys)

    def upsert_batched(self, entity_type_id: str, entities: List[dict]):
        """
        Upserts entities in an entity type (in batches, if needed).
        @param entity_type_id: the id of the entity type to upsert to
        @param entities: the entities to upsert
        """
        # Get the existing identifiers
        meta = self.get_entity_meta_data(entity_type_id)
        id_attr = meta["idAttribute"]
        existing_entities = self.get(
            entity_type_id, batch_size=10000, attributes=id_attr
        )
        existing_ids = {entity[id_attr] for entity in existing_entities}

        # Based on the existing identifiers, decide which rows should be added/updated
        add = list()
        update = list()
        for entity in entities:
            if entity[id_attr] in existing_ids:
                update.append(entity)
            else:
                add.append(entity)

        # Do the adds and updates in batches
        self.add_batched(entity_type_id, add)
        self.update_batched(entity_type_id, update)

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

    def update_batched(self, entity_type_id: str, entities: List[dict]):
        """Updates multiple entities in batches of 1000."""
        # TODO updating things in bulk will fail if there are self-references across
        #  batches. Dependency resolving is needed.
        batches = list(batched(entities, 1000))
        for batch in batches:
            self.update(entity_type_id, batch)

    def add_batched(self, entity_type_id: str, entities: List[dict]):
        """Adds multiple entities in batches of 1000."""
        # TODO adding things in bulk will fail if there are self-references across
        #  batches. Dependency resolving is needed.
        batches = list(batched(entities, 1000))
        for batch in batches:
            self.add_all(entity_type_id, batch)


class EricSession(ExtendedSession):
    """
    A session with a BBMRI ERIC directory. Contains methods to get national nodes,
    their (staging) data and quality information.
    """

    def __init__(self, *args, **kwargs):
        super(EricSession, self).__init__(*args, **kwargs)

    NODES_TABLE = "eu_bbmri_eric_national_nodes"

    def get_quality_info(self) -> QualityInfo:
        """
        Retrieves the quality information identifiers for biobanks and collections.
        :return: a QualityInfo object
        """

        biobank_qualities = self.get(
            "eu_bbmri_eric_bio_qual_info", batch_size=10000, attributes="id,biobank"
        )
        collection_qualities = self.get(
            "eu_bbmri_eric_col_qual_info", batch_size=10000, attributes="id,collection"
        )


        biobanks = utils.to_upload_format(biobank_qualities)
        collections = utils.to_upload_format(collection_qualities)

        bb_qual={}
        {bb_qual.setdefault(row["biobank"], []).append(row["id"]) for row in biobanks}
        coll_qual={}
        {coll_qual.setdefault(row["collection"], []).append(row["id"]) for row in collections}

        return QualityInfo(
             biobanks=bb_qual,
             collections=coll_qual
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
        Gets the four tables that belong to a single node's staging area.

        :param Node node: the node to get the staging data for
        :return: a NodeData object
        """
        tables = dict()
        for table_type in TableType.get_import_order():
            id_ = node.get_staging_id(table_type)

            tables[table_type] = Table.of(
                table_type=table_type,
                full_name=id_,
                rows=self.get_uploadable_data(id_, batch_size=10000),
            )

        return NodeData.from_dict(node=node, source=Source.STAGING, tables=tables)

    def get_published_node_data(self, node: Node) -> NodeData:
        """
        Gets the four tables that belong to a single node from the published tables.
        Filters the rows based on the national_node field.

        :param Node node: the node to get the published data for
        :return: a NodeData object
        """

        tables = dict()
        for table_type in TableType.get_import_order():
            id_ = table_type.base_id

            tables[table_type] = Table.of(
                table_type=table_type,
                full_name=id_,
                rows=self.get_uploadable_data(
                    id_, batch_size=10000, q=f"national_node=={node.code}"
                ),
            )

        return NodeData.from_dict(node=node, source=Source.PUBLISHED, tables=tables)


class ExternalServerSession(ExtendedSession):
    """
    A session with a national node's external server (for example BBMRI-NL).
    """

    def __init__(self, node: ExternalServerNode, *args, **kwargs):
        super(ExternalServerSession, self).__init__(url=node.url, *args, **kwargs)
        self.node = node

    def get_node_data(self) -> NodeData:
        """
        Gets the four tables of this node's external server.

        :return: a NodeData object
        """

        tables = dict()
        for table_type in TableType.get_import_order():
            id_ = table_type.base_id

            tables[table_type] = Table.of(
                table_type=table_type,
                full_name=id_,
                rows=self.get_uploadable_data(id_, batch_size=10000),
            )

        return NodeData.from_dict(
            node=self.node, source=Source.EXTERNAL_SERVER, tables=tables
        )
