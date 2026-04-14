"""
Audit Compliance Report
-----------------------
Shows audit scores, non-compliance breakdown, trend per project.
"""
import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    chart   = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Date",               "fieldname": "date",              "fieldtype": "Date",  "width": 100},
        {"label": "Project",            "fieldname": "project",           "fieldtype": "Link",  "options": "Project", "width": 150},
        {"label": "Category",           "fieldname": "category",          "fieldtype": "Data",  "width": 110},
        {"label": "Inspector",          "fieldname": "inspector",         "fieldtype": "Data",  "width": 130},
        {"label": "Score (%)",          "fieldname": "score",             "fieldtype": "Float", "width": 90},
        {"label": "Pass Threshold (%)", "fieldname": "pass_threshold",    "fieldtype": "Float", "width": 130},
        {"label": "Result",             "fieldname": "result",            "fieldtype": "Data",  "width": 90},
        {"label": "Non-Compliant",      "fieldname": "total_non_compliant","fieldtype": "Int",  "width": 110},
        {"label": "Critical NC",        "fieldname": "critical_nc",       "fieldtype": "Int",   "width": 90},
        {"label": "Audit Ref",          "fieldname": "name",              "fieldtype": "Link",  "options": "Audit Checklist", "width": 130},
    ]


def get_data(filters):
    conditions = "WHERE ac.docstatus = 1"
    values = {}
    if filters.get("project"):
        conditions += " AND ac.project = %(project)s"
        values["project"] = filters["project"]
    if filters.get("from_date"):
        conditions += " AND ac.date >= %(from_date)s"
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND ac.date <= %(to_date)s"
        values["to_date"] = filters["to_date"]
    if filters.get("category"):
        conditions += " AND ac.category = %(category)s"
        values["category"] = filters["category"]

    rows = frappe.db.sql(f"""
        SELECT
            ac.name, ac.date, ac.project, ac.category, ac.inspector,
            ac.score, ac.pass_threshold, ac.total_non_compliant,
            SUM(CASE WHEN aci.severity = 'Critical' AND aci.is_compliant = 0
                THEN 1 ELSE 0 END) AS critical_nc
        FROM `tabAudit Checklist` ac
        LEFT JOIN `tabAudit Checklist Item` aci ON aci.parent = ac.name
        {conditions}
        GROUP BY ac.name
        ORDER BY ac.date DESC
    """, values, as_dict=True)

    for r in rows:
        score     = float(r.score or 0)
        threshold = float(r.pass_threshold or 70)
        r.result  = "Pass" if score >= threshold else "Fail"
        r.critical_nc = r.critical_nc or 0

    return rows


def get_chart(data):
    if not data:
        return None
    rows = list(reversed(data[-15:]))
    labels = [str(r.date) for r in rows]
    scores = [float(r.score or 0) for r in rows]
    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Audit Score %", "values": scores, "chartType": "line"}]
        },
        "type": "line",
        "colors": ["#28a745"],
        "lineOptions": {"regionFill": 1},
    }


def get_summary(data):
    if not data:
        return []
    passed    = sum(1 for r in data if r.result == "Pass")
    failed    = sum(1 for r in data if r.result == "Fail")
    avg_score = round(sum(float(r.score or 0) for r in data) / len(data), 1)
    critical  = sum(int(r.critical_nc or 0) for r in data)
    return [
        {"label": "Audits Passed",       "value": passed,    "datatype": "Int", "color": "green"},
        {"label": "Audits Failed",        "value": failed,    "datatype": "Int", "color": "red"},
        {"label": "Avg Score",            "value": f"{avg_score}%", "datatype": "Data"},
        {"label": "Total Critical NC",    "value": critical,  "datatype": "Int", "color": "red"},
    ]
