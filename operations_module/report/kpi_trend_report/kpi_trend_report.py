"""
KPI Trend Report
----------------
Shows actual vs target trend per KPI per project.
Filters: project, kpi, from_date, to_date
"""
import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data, filters)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Date",         "fieldname": "date",          "fieldtype": "Date",  "width": 100},
        {"label": "Project",      "fieldname": "project",       "fieldtype": "Link",  "options": "Project", "width": 160},
        {"label": "KPI",          "fieldname": "kpi",           "fieldtype": "Link",  "options": "KPI Master", "width": 160},
        {"label": "Unit",         "fieldname": "unit",          "fieldtype": "Data",  "width": 60},
        {"label": "Actual",       "fieldname": "actual_value",  "fieldtype": "Float", "width": 90},
        {"label": "Target",       "fieldname": "target_value",  "fieldtype": "Float", "width": 90},
        {"label": "Variance",     "fieldname": "variance",      "fieldtype": "Float", "width": 90},
        {"label": "Status",       "fieldname": "status",        "fieldtype": "Data",  "width": 100},
        {"label": "Remarks",      "fieldname": "remarks",       "fieldtype": "Data",  "width": 200},
    ]


def get_data(filters):
    conditions = {}
    if filters.get("project"):
        conditions["project"] = filters["project"]
    if filters.get("kpi"):
        conditions["kpi"] = filters["kpi"]
    if filters.get("from_date") and filters.get("to_date"):
        conditions["date"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        conditions["date"] = [">=", filters["from_date"]]

    rows = frappe.get_all(
        "KPI Log",
        filters=conditions,
        fields=["date", "project", "kpi", "unit", "actual_value",
                "target_value", "variance", "remarks"],
        order_by="date desc, project, kpi"
    )

    for r in rows:
        actual  = float(r.actual_value  or 0)
        target  = float(r.target_value  or 0)
        if target > 0:
            pct = round((actual / target) * 100, 1)
            if pct >= 100:
                r.status = f"On Track ({pct}%)"
            elif pct >= 80:
                r.status = f"At Risk ({pct}%)"
            else:
                r.status = f"Below Target ({pct}%)"
        else:
            r.status = "No Target Set"

    return rows


def get_chart(data, filters):
    if not data:
        return None
    # Group by date for first KPI found
    kpi_filter = filters.get("kpi")
    subset = [r for r in data if not kpi_filter or r.kpi == kpi_filter][:20]
    subset.reverse()
    labels  = [str(r.date)         for r in subset]
    actuals = [r.actual_value or 0 for r in subset]
    targets = [r.target_value or 0 for r in subset]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Actual", "values": actuals, "chartType": "line"},
                {"name": "Target", "values": targets, "chartType": "line"},
            ]
        },
        "type": "line",
        "colors": ["#2490EF", "#E65C00"],
        "lineOptions": {"regionFill": 0, "hideDots": 0},
        "axisOptions": {"xAxisMode": "tick"},
    }


def get_summary(data):
    if not data:
        return []
    on_track     = sum(1 for r in data if "On Track" in (r.status or ""))
    at_risk      = sum(1 for r in data if "At Risk" in (r.status or ""))
    below_target = sum(1 for r in data if "Below Target" in (r.status or ""))
    return [
        {"label": "On Track",     "value": on_track,     "datatype": "Int", "color": "green"},
        {"label": "At Risk",      "value": at_risk,      "datatype": "Int", "color": "orange"},
        {"label": "Below Target", "value": below_target, "datatype": "Int", "color": "red"},
    ]
