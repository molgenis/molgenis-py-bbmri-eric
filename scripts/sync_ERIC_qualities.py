"""
This script updates the biobank and collection quality information on an external
server with the quality information from the BBMRI-ERIC Directory.

The script can be placed and scheduled on an external server
with the ${molgenisToken} security token activated.
"""

from molgenis.client import Session

tables = {
    "eu_bbmri_eric_biobanks": ["eu_bbmri_eric_bio_qual_info", "biobank"],
    "eu_bbmri_eric_collections": ["eu_bbmri_eric_col_qual_info", "collection"],
}
session = Session(url="http://localhost:8080", token="${molgenisToken}")
eric_session = Session(url="${eric_url}")

for table in tables:
    print(f"Add Qualities to {table}")
    quals = []
    qual_table = tables[table][0]
    ids = session.get(table, attributes="id", uploadable=True)
    eric_quals = eric_session.get(qual_table, uploadable=True)
    for id in ids:
        quals.extend(
            [qual for qual in eric_quals if qual[tables[table][1]] == id["id"]]
        )
    session.delete(qual_table)
    session.add_all(qual_table, quals)
