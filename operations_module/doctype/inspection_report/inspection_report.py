import frappe
from frappe.model.document import Document


class InspectionReport(Document):
    def validate(self):
        self._set_overall_status()
        self._set_report_no()

    def _set_overall_status(self):
        if not self.findings:
            self.overall_status = "Satisfactory"
            return
        severities = [f.severity for f in self.findings]
        if "Critical" in severities:
            self.overall_status = "Critical"
        elif "Major" in severities:
            self.overall_status = "Needs Attention"
        else:
            self.overall_status = "Satisfactory"

    def _set_report_no(self):
        if not self.report_no:
            count = frappe.db.count("Inspection Report", {"project": self.project})
            self.report_no = f"{self.project}-INS-{str(count + 1).zfill(3)}"
