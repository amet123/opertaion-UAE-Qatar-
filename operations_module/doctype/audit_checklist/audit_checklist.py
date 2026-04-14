import frappe
from frappe.model.document import Document


class AuditChecklist(Document):
    def validate(self):
        total = len(self.items)
        if not total:
            return
        compliant = sum(1 for i in self.items if i.is_compliant)
        self.score = round((compliant / total) * 100, 2)
        self.total_non_compliant = total - compliant
