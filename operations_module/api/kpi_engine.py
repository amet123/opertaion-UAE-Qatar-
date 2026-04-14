"""
KPI Script Engine
-----------------
Runs Python scripts stored in KPI Master records.
Results saved to KPI Log. Alerts triggered on breach.
"""
import frappe
from frappe.utils import nowdate, getdate, add_days
from operations_module.api.utils import get_ops_setting
from operations_module.api.notifications import send_kpi_alert


def run_daily_kpis():
    _run_kpis_by_frequency("Daily")


def run_weekly_kpis():
    _run_kpis_by_frequency("Weekly")


def run_monthly_kpis():
    _run_kpis_by_frequency("Monthly")


def _run_kpis_by_frequency(frequency):
    """Get all KPI assignments for given frequency and compute each."""
    assignments = frappe.get_all(
        "Project KPI Assignment",
        filters={"frequency": frequency, "is_active": 1},
        fields=["project", "kpi", "target_value", "alert_threshold", "alert_email"]
    )
    for a in assignments:
        try:
            run_single_kpi(a.project, a.kpi, nowdate(), a.target_value, a.alert_threshold, a.alert_email)
        except Exception as e:
            frappe.log_error(
                f"KPI compute failed: {a.kpi} / {a.project}\n{str(e)}",
                "KPI Engine Error"
            )


def run_single_kpi(project, kpi_name, date, target_value=None, alert_threshold=None, alert_email=None):
    """Execute the script stored in KPI Master and save result to KPI Log."""
    method = get_ops_setting("kpi_compute_method") or "Script"
    kpi = frappe.get_doc("KPI Master", kpi_name)

    if method == "Script" and kpi.compute_script:
        actual = _exec_kpi_script(kpi.compute_script, project, date)
    else:
        # Simple mode — manual entry only, no auto-compute
        return

    if actual is None:
        return

    t_val = target_value or frappe.db.get_value(
        "Project KPI Assignment",
        {"project": project, "kpi": kpi_name},
        "target_value"
    ) or 0

    variance = round(float(actual) - float(t_val), 4)

    # Save log — avoid duplicates
    existing = frappe.db.get_value(
        "KPI Log",
        {"kpi": kpi_name, "project": project, "date": date},
        "name"
    )
    if existing:
        frappe.db.set_value("KPI Log", existing, {
            "actual_value": actual,
            "target_value": t_val,
            "variance": variance,
        })
    else:
        frappe.get_doc({
            "doctype": "KPI Log",
            "kpi": kpi_name,
            "project": project,
            "date": date,
            "actual_value": actual,
            "target_value": t_val,
            "variance": variance,
            "unit": kpi.unit,
        }).insert(ignore_permissions=True)

    # Alert check
    thresh = alert_threshold or kpi.alert_threshold
    if thresh and float(actual) < float(thresh):
        send_kpi_alert(kpi_name, project, actual, t_val, alert_email)

    return actual


def _exec_kpi_script(script, project, date):
    """
    Safely execute the KPI compute script.
    Script MUST set: result = <numeric value>
    Context provides: frappe, project, date, result=None
    """
    context = {
        "frappe": frappe,
        "project": project,
        "date": getdate(date),
        "result": None,
    }
    try:
        exec(compile(script, "<KPI Script>", "exec"), context)  # nosec
    except Exception as e:
        frappe.log_error(f"Script error: {str(e)}\n{script}", "KPI Script Error")
        return None
    return context.get("result")


def trigger_feedback_kpi(doc, method=None):
    """Called after Client Feedback Form insert — triggers feedback score KPI."""
    run_single_kpi(
        project=doc.project,
        kpi_name="Avg Client Feedback Score",
        date=nowdate()
    )


@frappe.whitelist()
def get_kpi_dashboard_data(project=None, from_date=None, to_date=None):
    """Return KPI log data for dashboard charts."""
    filters = {}
    if project:
        filters["project"] = project
    if from_date:
        filters["date"] = ["between", [from_date, to_date or nowdate()]]

    logs = frappe.get_all(
        "KPI Log",
        filters=filters,
        fields=["kpi", "project", "date", "actual_value", "target_value", "variance", "unit"],
        order_by="date asc",
        limit=500
    )
    return logs
