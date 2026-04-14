import frappe
from frappe.model.document import Document
from frappe.utils import add_months, add_days, getdate


class TrainingSchedule(Document):
    def validate(self):
        self._calc_next_due()
        self._calc_completion()

    def _calc_next_due(self):
        if not self.start_date:
            return
        freq_map = {
            "One-time": None, "Monthly": 1,
            "Quarterly": 3, "Annual": 12
        }
        months = freq_map.get(self.frequency)
        if months:
            self.next_due_date = add_months(self.start_date, months)

    def _calc_completion(self):
        if not self.sessions:
            self.completion_pct = 0
            return
        done = sum(1 for s in self.sessions if s.status == "Completed")
        self.completion_pct = round((done / len(self.sessions)) * 100, 1)
