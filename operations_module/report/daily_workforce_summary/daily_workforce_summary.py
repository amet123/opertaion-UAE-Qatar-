"""
Daily Workforce Summary
-----------------------
Shows attendance breakdown per project per date.
Filters: from_date, to_date, project, company
"""
import frappe
from frappe.utils import getdate, nowdate


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Date",             "fieldname": "date",            "fieldtype": "Date",    "width": 100},
        {"label": "Project",          "fieldname": "project",         "fieldtype": "Link",    "options": "Project", "width": 160},
        {"label": "Shift",            "fieldname": "shift",           "fieldtype": "Data",    "width": 120},
        {"label": "Site Location",    "fieldname": "site_location",   "fieldtype": "Data",    "width": 120},
        {"label": "Total Scheduled",  "fieldname": "total_employees", "fieldtype": "Int",     "width": 120},
        {"label": "Present",          "fieldname": "total_present",   "fieldtype": "Int",     "width": 80},
        {"label": "Absent",           "fieldname": "total_absent",    "fieldtype": "Int",     "width": 80},
        {"label": "Half Day",         "fieldname": "half_day",        "fieldtype": "Int",     "width": 80},
        {"label": "On Leave",         "fieldname": "on_leave",        "fieldtype": "Int",     "width": 80},
        {"label": "OT Hours",         "fieldname": "total_ot_hours",  "fieldtype": "Float",   "width": 90},
        {"label": "Attendance %",     "fieldname": "attendance_pct",  "fieldtype": "Percent", "width": 100},
        {"label": "Schedule Ref",     "fieldname": "name",            "fieldtype": "Link",    "options": "Daily Manpower Schedule", "width": 140},
    ]


def get_data(filters):
    conditions = "WHERE dms.docstatus = 1"
    values = {}

    if filters.get("from_date"):
        conditions += " AND dms.date >= %(from_date)s"
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND dms.date <= %(to_date)s"
        values["to_date"] = filters["to_date"]
    if filters.get("project"):
        conditions += " AND dms.project = %(project)s"
        values["project"] = filters["project"]
    if filters.get("company"):
        conditions += " AND dms.company = %(company)s"
        values["company"] = filters["company"]

    rows = frappe.db.sql(f"""
        SELECT
            dms.name,
            dms.date,
            dms.project,
            dms.shift,
            dms.site_location,
            dms.total_employees,
            dms.total_present,
            dms.total_absent,
            SUM(CASE WHEN med.status = 'Half Day' THEN 1 ELSE 0 END) AS half_day,
            SUM(CASE WHEN med.status = 'On Leave' THEN 1 ELSE 0 END) AS on_leave,
            COALESCE(SUM(med.ot_hours), 0) AS total_ot_hours
        FROM `tabDaily Manpower Schedule` dms
        LEFT JOIN `tabManpower Employee Detail` med ON med.parent = dms.name
        {conditions}
        GROUP BY dms.name
        ORDER BY dms.date DESC, dms.project
    """, values, as_dict=True)

    for r in rows:
        total = r.total_employees or 0
        present = r.total_present or 0
        r.attendance_pct = round((present / total * 100) if total else 0, 1)
        r.total_ot_hours = round(r.total_ot_hours or 0, 2)

    return rows


def get_chart(data):
    if not data:
        return None
    labels = [str(r.date) for r in data[:15]]
    present = [r.total_present for r in data[:15]]
    absent  = [r.total_absent  for r in data[:15]]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Present", "values": present, "chartType": "bar"},
                {"name": "Absent",  "values": absent,  "chartType": "bar"},
            ]
        },
        "type": "bar",
        "colors": ["#28a745", "#dc3545"],
        "barOptions": {"stacked": True},
    }


def get_summary(data):
    if not data:
        return []
    total_scheduled = sum(r.total_employees or 0 for r in data)
    total_present   = sum(r.total_present   or 0 for r in data)
    total_ot        = sum(r.total_ot_hours  or 0 for r in data)
    avg_att         = round((total_present / total_scheduled * 100) if total_scheduled else 0, 1)
    return [
        {"label": "Total Scheduled", "value": total_scheduled, "datatype": "Int"},
        {"label": "Total Present",   "value": total_present,   "datatype": "Int"},
        {"label": "Avg Attendance",  "value": f"{avg_att}%",   "datatype": "Data", "color": "green" if avg_att >= 90 else "orange"},
        {"label": "Total OT Hours",  "value": round(total_ot, 1), "datatype": "Float"},
    ]
