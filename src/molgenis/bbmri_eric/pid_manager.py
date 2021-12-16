from typing import List

from molgenis.bbmri_eric.errors import EricWarning
from molgenis.bbmri_eric.model import Table
from molgenis.bbmri_eric.pid_service import PidService, Status
from molgenis.bbmri_eric.printer import Printer


class PidManager:
    def __init__(self, pid_service: PidService, printer: Printer, url: str):
        self.pid_service = pid_service
        self.printer = printer
        self.biobank_url_prefix = url.rstrip("/") + "/#/biobank/"

    def assign_biobank_pids(self, biobanks: Table) -> List[EricWarning]:
        warnings = []
        for biobank in biobanks.rows:
            if "pid" not in biobank:
                biobank["pid"] = self._register_biobank_pid(
                    biobank["id"], biobank["name"], warnings
                )

        return warnings

    def update_biobank_pids(self, biobanks: Table, existing_biobanks: Table):
        existing_biobanks = existing_biobanks.rows_by_id
        for biobank in biobanks.rows:
            id_ = biobank["id"]
            if id_ in existing_biobanks:
                if biobank["name"] != existing_biobanks.get(biobank["id"])["name"]:
                    self._update_biobank_name(biobank["pid"], biobank["name"])

    def terminate_biobanks(self, biobanks: List[dict]):
        for biobank in biobanks:
            self.pid_service.set_status(biobank["pid"], Status.TERMINATED)
            self.printer.print(
                f"Set STATUS of {biobank['pid']} to {Status.TERMINATED.value}"
            )

    def _register_biobank_pid(
        self, biobank_id: str, biobank_name: str, warnings: List[EricWarning]
    ) -> str:
        """
        Registers a PID for a new biobank. If one or more PIDs for this biobank already
        exist, warnings will be shown.
        """
        url = self.biobank_url_prefix + biobank_id
        existing_pids = self.pid_service.reverse_lookup(url)

        if existing_pids:
            pid = existing_pids[0]
            warning = EricWarning(
                f'PID(s) already exist for new biobank "{biobank_name}": '
                f"{str(existing_pids)}"
            )
            self.printer.print_warning(warning)
            warnings.append(warning)
        else:
            pid = self.pid_service.register_pid(url=url, name=biobank_name)
            self.printer.print(f'Registered {pid} for new biobank "{biobank_name}"')

        return pid

    def _update_biobank_name(self, pid: str, name: str):
        self.pid_service.set_name(pid, name)
        self.printer.print(f'Updated NAME of {pid} to "{name}"')
