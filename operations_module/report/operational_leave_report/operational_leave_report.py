"""
Operational Leave Report
------------------------
Consolidated sick leave, vacation, and other leave by employee/project.
Includes Qatar/UAE entitlement comparison.
"""
import frappe
from frappe.utils import getdate
from operations_module.api.labour_law import get_annual_leave_days
from operations_module.api.utils import get_ops_setting


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Employee",       "fieldname": "employee",       "fieldtype": "Link",  "options": "Employee", "width": 130},
        {"label": "Employee Name",  "fieldname": "employee_name",  "fieldtype": "Data",  "width": 150},
        {"label": "Project",        "fieldname": "project",        "fieldtype": "Link",  "options": "Project",  "width": 140},
        {"label": "Department",     "fieldname": "department",     "fieldtype": "Data",  "width": 120},
        {"label": "Leave Type",     "fieldname": "leave_type",     "fieldtype": "Link",  "options": "Leave Type", "width": 130},
        {"label": "From Date",      "fieldname": "from_date",      "fieldtype": "Date",  "width": 100},
        {"label": "To Date",        "fieldname": "to_date",        "fieldtype": "Date",  "width": 100},
        {"label": "Days",           "fieldname": "total_leave_days","fieldtype": "Float", "width": 70},
        {"label": "Status",         "fieldname": "status",         "fieldtype": "Data",  "width": 90},
        {"label": "Annual Entitlement","fieldname": "entitlement",  "fieldtype": "Int",   "width": 140},
        {"label": "Used This Year", "fieldname": "used_this_year", "fieldtype": "Float", "width": 130},
        {"label": "Balance",        "fieldname": "balance",        "fieldtype": "Float", "width": 90},
    ]


def get_data(filters):
    conditions = "WHERE la.docstatus = 1"
    values = {}

    if filters.get("from_date"):
        conditions += " AND la.from_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND la.to_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]
    if filters.get("employee"):
        conditions += " AND la.employee = %(employee)s"
        values["employee"] = filters["employee"]
    if filters.get("leave_type"):
        conditions += " AND la.leave_type = %(leave_type)s"
        values["leave_type"] = filters["leave_type"]
    if filters.get("department"):
        conditions += " AND emp.department = %(department)s"
        values["department"] = filters["department"]

    rows = frappe.db.sql(f"""
        SELECT
            la.employee,
            la.employee_name,
            emp.custom_project AS project,
            emp.department,
            la.leave_type,
            la.from_date,
            la.to_date,
            la.total_leave_days,
            la.status
        FROM `tabLeave Application` la
        LEFT JOIN `tabEmployee` emp ON emp.name = la.employee
        {conditions}
        ORDER BY la.from_date DESC
    """, values, as_dict=True)

    # Enrich with entitlement and balance
    emp_cache = {}
    for r in rows:
        if r.leave_type in ("Annual Leave", "Privilege Leave", "Earned Leave"):
            if r.employee not in emp_cache:
                try:
                    entitlement = get_annual_leave_days(r.employee)
                except Exception:
                    entitlement = 0
                used = frappe.db.get_value(
                    "Leave Ledger Entry",
                    {"employee": r.employee, "leave_type": r.leave_type,
                     "transaction_type": "Leave Application",
                     "from_date": [">=", frappe.utils.get_first_day(frappe.utils.nowdate())]},
                    "SUM(leaves)"
                ) or 0
                emp_cache[r.employee] = {"entitlement": entitlement, "used": abs(float(used))}
            cached = emp_cache[r.employee]
            r.entitlement = cached["entitlement"]
            r.used_this_year = cached["used"]
            r.balance = max(0, r.entitlement - r.used_this_year)
        else:
            r.entitlement = "-"
            r.used_this_year = r.total_leave_days
            r.balance = "-"

    return rows


def get_chart(data):
    from collections import defaultdict
    by_type = defaultdict(float)
    for r in data:
        by_type[r.leave_type] = by_type[r.leave_type] + float(r.total_leave_days or 0)
    if not by_type:
        return None
    labels = list(by_type.keys())
    values = [round(by_type[l], 1) for l in labels]
    return {
        "data": {"labels": labels, "datasets": [{"values": values}]},
        "type": "pie",
        "colors": ["#2490EF","#E65C00","#28a745","#dc3545","#6f42c1"],
    }


def get_summary(data):
    total_days   = sum(float(r.total_leave_days or 0) for r in data)
    sick_days    = sum(float(r.total_leave_days or 0) for r in data if "Sick" in (r.leave_type or ""))
    annual_days  = sum(float(r.total_leave_days or 0) for r in data if "Annual" in (r.leave_type or "") or "Privilege" in (r.leave_type or ""))
    return [
        {"label": "Total Leave Days", "value": round(total_days, 1),  "datatype": "Float"},
        {"label": "Sick Leave Days",  "value": round(sick_days, 1),   "datatype": "Float"},
        {"label": "Annual Leave Days","value": round(annual_days, 1), "datatype": "Float"},
        {"label": "Employees on Leave","value": len(set(r.employee for r in data)), "datatype": "Int"},
    ]
