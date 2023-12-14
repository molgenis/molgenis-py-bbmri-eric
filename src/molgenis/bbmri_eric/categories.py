from copy import deepcopy
from enum import Enum
from typing import List, Set

from molgenis.bbmri_eric.model import OntologyTable


class Category(Enum):
    """
    Enum of Collection Categories with identifiers found in the
    eu_bbmri_eric_category table.
    """

    PAEDIATRIC = "paediatric_only"
    PAEDIATRIC_INCLUDED = "paediatric_included"
    RARE_DISEASE = "rare_disease"
    COVID19 = "covid19"
    CANCER = "cancer"


class AgeUnit(Enum):
    """
    Enum of age units with identifiers found in the eu_bbmri_eric_age_units table.
    """

    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"


PAEDIATRIC_AGE_LIMIT = {
    AgeUnit.DAY: 365 * 18,
    AgeUnit.WEEK: 52 * 18,
    AgeUnit.MONTH: 12 * 18,
    AgeUnit.YEAR: 18,
}

CANCER_TERMS = {
    "urn:miriam:icd:C00-C97",
    "urn:miriam:icd:D00-D09",
    "urn:miriam:icd:D37-D48",
}

COVID_TERMS = {
    "urn:miriam:icd:U09",
    "urn:miriam:icd:U08",
    "urn:miriam:icd:U11",
    "urn:miriam:icd:U10",
    "urn:miriam:icd:U12",
    "urn:miriam:icd:U07.1",
    "urn:miriam:icd:U07.2",
}


class CategoryMapper:
    def __init__(self, diseases: OntologyTable):
        self.diseases = diseases

    def map(self, collection: dict) -> List[str]:
        """
        Maps data from a collection to a list of categories that the collection belongs
        to.
        :param collection: the collection to map
        :return: a list of categories
        """
        categories = []

        self._map_paediatric(collection, categories)
        self._map_diseases(collection, categories)
        self._map_collection_types(collection, categories)

        return list(set(categories))

    @classmethod
    def _map_paediatric(cls, collection: dict, categories: List[str]):
        unit = collection.get("age_unit", None)
        if unit:
            low = collection.get("age_low", None)
            high = collection.get("age_high", None)

            if (
                low is not None
                and high is not None
                and ((low == 0 and high == 0) or (low > high))
            ):
                return

            age_limit = PAEDIATRIC_AGE_LIMIT[AgeUnit[unit]]
            if high is not None and (high < age_limit):
                categories.append(Category.PAEDIATRIC.value)
            elif low is not None and (low < age_limit):
                categories.append(Category.PAEDIATRIC_INCLUDED.value)

    @classmethod
    def _map_collection_types(cls, collection: dict, categories: List[str]):
        if "RD" in collection.get("type", []):
            categories.append(Category.RARE_DISEASE.value)

    def _map_diseases(self, collection: dict, categories: List[str]):
        diagnoses = deepcopy(collection.get("diagnosis_available", []))
        if diagnoses:
            if self.diseases.matching_attrs:
                matching_diagnoses = self.diseases.get_matching_ontologies(diagnoses)
                diagnoses.extend(matching_diagnoses)
                diagnoses = set(diagnoses)

            if self._contains_orphanet(diagnoses):
                categories.append(Category.RARE_DISEASE.value)

            if self._contains_descendant_of(diagnoses, CANCER_TERMS):
                categories.append(Category.CANCER.value)

            if self._contains_descendant_of(diagnoses, COVID_TERMS):
                categories.append(Category.COVID19.value)

    def _contains_orphanet(self, diagnoses: List[str]) -> bool:
        for diagnosis in diagnoses:
            term = self.diseases.rows_by_id.get(diagnosis, None)
            if term and term.get("ontology", "") == "orphanet":
                return True

    def _contains_descendant_of(self, diagnoses: List[str], terms: Set[str]):
        for diagnosis in diagnoses:
            if self.diseases.is_descendant_of_any(diagnosis, terms):
                return True
