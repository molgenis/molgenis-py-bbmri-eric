"""
Import CRC data from https://crc.molgeniscloud.org into https://catalogue.bbmri.nl
"""

import numpy as np
import pandas as pd

from molgenis.bbmri_eric.bbmri_client import (
    EricSession,
    ImportDataAction,
    ImportMetadataAction,
)
from molgenis.bbmri_eric.errors import EricError, EricWarning, ErrorReport
from molgenis.bbmri_eric.model import (
    Node,
    NodeData,
    Source,
    Table,
    TableMeta,
    TableType,
)
from molgenis.bbmri_eric.printer import Printer
from molgenis.client import MolgenisRequestError


def modified_crc_data(entity_type_id: str):
    crc_meta = crc_session.get_meta(entity_type_id)
    int_columns = ["durationStatus", "order_of_magnitude_donors"]
    for attribute in crc_meta["attributes"]["items"]:
        if attribute["data"]["type"] == "int":
            int_columns.append(attribute["data"]["name"])

    data = crc_session.get(entity_type_id, batch_size=10000, uploadable=True)
    df_crc = pd.DataFrame(data)

    if entity_type_id == "eu_bbmri_eric_collections":
        with printer.indentation():
            printer.print("Modify CRC collections")
            with printer.indentation():
                printer.print("Replace unknown Data Category Types by OTHER")
                for unknown_type in [
                    "WGS",
                    "WES",
                    "MRI",
                    "LONGITUDINAL_CLINICAL_DATA",
                    "CLINICAL_DATA",
                    "CNV",
                    "SNP_DATA",
                    "VIDEO_OF_SURGERY",
                    "NTRK_FUSION_DATA",
                    "CLINICAL_RESPONSE_INFORMATION",
                    "clinical_followUp",
                    "CMS_STATUS",
                    "NGS_RNAbased",
                    "ORGANOID_DRUG_RESPOSE_DATA",
                    "PATIENT_REPORTED_OUTCOMES",
                    "treatment_data",
                    "diagnostic_data",
                    "TUMOR_STROMA_RATIO",
                ]:
                    df_crc["data_categories"] = df_crc["data_categories"].apply(
                        lambda categories: [
                            category.replace(unknown_type, "OTHER")
                            for category in categories
                        ]
                        if categories is not np.nan
                        else categories
                    )
                printer.print("Replace unknown Materials by OTHER")
                for unknown_type in [
                    "ASCITES",
                    "BIOPSY",
                    "TISSUE_CRYOPRESERVED",
                    "ctDNA",
                    "CELL_PELLET",
                    "CTCs",
                    "H&E_SLIDES",
                    "SWAB",
                    "TMA",
                    "CIRCULATING_ENDOTHELIAL_CELL",
                    "ORGANOIDS",
                    "TISSUE FRESH",
                ]:
                    df_crc["materials"] = df_crc["materials"].apply(
                        lambda materials: [
                            material.replace(unknown_type, "OTHER")
                            for material in materials
                        ]
                        if materials is not np.nan
                        else materials
                    )
                printer.print("Replace unknown Collection Types by OTHER")
                for unknown_type in [
                    "RCT",
                    "PATIENT_PREFERENCE_STUDY",
                    "gwas",
                    "INTERVENTIONAL_STUDY",
                    "CLINICAL_EFFECTIVENESS_TRIAL",
                    "TWICS",
                    "MULTICENTER",
                    "OBSERVATIONAL_STUDY",
                    "EXPLORATORY_STUDY",
                    "CLINICAL_INTERVENTION",
                    "DOSE_ESCALATION_STUDY",
                ]:
                    df_crc["type"] = df_crc["type"].apply(
                        lambda types: [
                            coll_type.replace(unknown_type, "OTHER")
                            for coll_type in types
                        ]
                        if types is not np.nan
                        else types
                    )

        # Make sure the columns contain a list with unique values
        df_crc["data_categories"] = df_crc["data_categories"].apply(
            lambda categories: list(pd.unique(categories))
        )
        df_crc["materials"] = df_crc["materials"].apply(
            lambda materials: list(pd.unique(materials))
        )
        df_crc["type"] = df_crc["type"].apply(lambda types: list(pd.unique(types)))

    # Turn pd.DataFrame to list of dictionaries
    uploadable_data = df_crc.to_dict("records")

    # Remove (NaN) missing values
    for row in uploadable_data:
        for column in df_crc.columns:
            if row[column] != row[column]:
                del row[column]

            if column in int_columns and column in row:
                row[column] = int(row[column])

    return uploadable_data


# Initiate the two sessions
crc_session = EricSession(url="${crc_url}")
nl_session = EricSession(url="http://localhost:8080", token="${molgenisToken}")

crc = Node("CRC", "CRC", None)
printer = Printer()
report = ErrorReport([crc])
warnings = []

tables = dict()
for table_type in TableType.get_import_order():
    id_ = table_type.base_id
    printer.print(f"Get CRC {id_.replace('eu_bbmri_eric_', '')}")
    if not crc_session.get("sys_md_EntityType", q=f"id=={id_}"):
        tables[table_type.value] = Table.of_placeholder(table_type)
        warning = EricWarning(f"CRC has no {table_type.value} table")
        printer.print_warning(warning)
    else:
        meta = TableMeta(crc_session.get_meta(id_))

        tables[table_type.value] = Table.of(
            table_type=table_type,
            meta=meta,
            rows=modified_crc_data(id_),
        )

crc_data = NodeData.from_dict(node=crc, source=Source.STAGING, tables=tables)

printer.print("Remove existing CRC data from BBMRI-NL")
# First delete existing data
for table in reversed(crc_data.import_order):
    entity_type = table.type.base_id.replace("eu_bbmri_eric_", "")
    if entity_type in ["networks", "also_known_in"]:
        continue
    try:
        with printer.indentation():
            # Get the CRC data from BBMRI-NL
            nl_crc = nl_session.get(
                table.type.base_id,
                batch_size=10000,
                attributes="id",
                q="id=like='NL_CRC'",
                uploadable=True,
            )

            if len(nl_crc) == 0:
                printer.print(f"There are no existing CRC {entity_type} in BBMRI-NL")
                continue
            crc_ids = set({row["id"] for row in table.rows})
            nl_ids = set({row["id"] for row in nl_crc})
            deleted_ids = nl_ids.difference(crc_ids)

            if deleted_ids:
                warning = EricWarning(
                    f"{len(deleted_ids)} CRC {entity_type} in BBMRI-NL "
                    f"{entity_type} are not in CRC anymore."
                )
                printer.print_warning(warning)
                warnings.append(warning)
                warning = EricWarning(f"The deleted IDs are: {deleted_ids}")
                printer.print_warning(warning)
                warnings.append(warning)
            printer.print(
                f"Remove {len(nl_ids)} existing CRC " f"{entity_type} from BBMRI-NL"
            )

            nl_session.delete_list(table.type.base_id, list(nl_ids))

    except MolgenisRequestError as e:
        # report.add_error("CRC",
        # EricError(f"Error deleting CRC {entity_type} from BBMRI-NL"))
        raise EricError(f"Error deleting CRC {entity_type} from BBMRI-NL") from e

report.add_node_warnings(crc_data.node, warnings)

# Add CRC data to BBMRI-NL
printer.print("Add CRC data to BBMRI-NL")
importable_data = dict()
for table in crc_data.import_order:
    entity_type = table.full_name.replace("eu_bbmri_eric_", "")
    if entity_type in ["also_known_in", "networks"]:
        continue
    with printer.indentation():
        printer.print(f"Add {len(table.rows)} CRC {entity_type} to BBMRI-NL")
    importable_data[table.full_name] = table.rows

try:
    nl_session.import_data(
        importable_data,
        data_action=ImportDataAction.ADD,
        metadata_action=ImportMetadataAction.IGNORE,
    )

except MolgenisRequestError as e:
    raise EricError("Error importing CRC data") from e

printer.print_summary(report)

if report.has_warnings():
    raise ValueError("Import CRC data resulted in warnings")
