"""
Attendance Sync API
-------------------
Manual mode: on Daily Manpower Schedule submit,
auto-create ERPNext Attendance + Additional Salary (OT) records.
"""
import frappe
from frappe.utils import nowdate, getdate
from operations_module.api.utils import get_ops_setting
from operations_module.api.labour_law import calculate_ot_amount


def on_manpower_schedule_submit(doc, method=None):
    """Triggered on_submit of Daily Manpower Schedule."""
    for row in doc.employees:
        _create_attendance(doc, row)
        if (row.ot_hours or 0) > 0:
            _create_ot_salary(doc, row)


def on_manpower_schedule_cancel(doc, method=None):
    """Cancel linked attendance records when schedule is cancelled."""
    for row in doc.employees:
        att_name = frappe.db.get_value(
            "Attendance",
            {"employee": row.employee, "attendance_date": doc.date,
             "custom_manpower_schedule": doc.name},
            "name"
        )
        if att_name:
            att = frappe.get_doc("Attendance", att_name)
            if att.docstatus == 1:
                att.cancel()


def _create_attendance(doc, row):
    """Create or update an Attendance record for one employee row."""
    existing = frappe.db.get_value(
        "Attendance",
        {"employee": row.employee, "attendance_date": doc.date},
        "name"
    )
    if existing:
        frappe.db.set_value("Attendance", existing, {
            "status": row.status,
            "shift": doc.shift,
            "custom_project": doc.project,
            "custom_manpower_schedule": doc.name,
        })
        return

    att = frappe.get_doc({
        "doctype": "Attendance",
        "employee": row.employee,
        "employee_name": row.employee_name,
        "attendance_date": doc.date,
        "status": row.status,
        "shift": doc.shift,
        "company": doc.company,
        "custom_project": doc.project,
        "custom_site_location": doc.site_location,
        "custom_manpower_schedule": doc.name,
    })
    att.insert(ignore_permissions=True)
    att.submit()


def _create_ot_salary(doc, row):
    """Create Additional Salary record for overtime pay."""
    ot_amount = calculate_ot_amount(
        employee=row.employee,
        ot_hours=row.ot_hours,
        shift_start=doc.shift_start_time,
        day_of_week=getdate(doc.date).weekday()
    )
    if not ot_amount:
        return

    salary_component = get_ops_setting("ot_salary_component") or "Overtime Pay"
    frappe.get_doc({
        "doctype": "Additional Salary",
        "employee": row.employee,
        "salary_component": salary_component,
        "amount": ot_amount,
        "payroll_date": doc.date,
        "company": doc.company,
        "overwrite_salary_structure_amount": 0,
        "custom_reference": doc.name,
        "remarks": f"OT {row.ot_hours} hrs — Project {doc.project}",
    }).insert(ignore_permissions=True)


@frappe.whitelist()
def get_schedule_summary(date=None, project=None):
    """Dashboard API — attendance summary for a date/project."""
    filters = {}
    if date:
        filters["date"] = date
    if project:
        filters["project"] = project

    schedules = frappe.get_all(
        "Daily Manpower Schedule",
        filters=filters,
        fields=["name", "project", "shift", "date", "total_employees",
                "total_present", "total_absent", "docstatus"]
    )
    return schedules
