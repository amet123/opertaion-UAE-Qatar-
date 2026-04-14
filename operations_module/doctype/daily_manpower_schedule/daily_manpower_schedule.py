import frappe
from frappe.model.document import Document


class DailyManpowerSchedule(Document):
    def validate(self):
        self._update_counts()
        self._fetch_shift_times()

    def _update_counts(self):
        self.total_employees = len(self.employees)
        self.total_present = sum(1 for e in self.employees if e.status == "Present")
        self.total_absent = sum(1 for e in self.employees if e.status == "Absent")

    def _fetch_shift_times(self):
        if self.shift and not self.shift_start_time:
            st = frappe.db.get_value("Shift Type", self.shift,
                ["start_time", "end_time"], as_dict=True)
            if st:
                self.shift_start_time = st.start_time
                self.shift_end_time = st.end_time

    def on_submit(self):
        from operations_module.api.attendance_sync import on_manpower_schedule_submit
        on_manpower_schedule_submit(self)

    def on_cancel(self):
        from operations_module.api.attendance_sync import on_manpower_schedule_cancel
        on_manpower_schedule_cancel(self)
