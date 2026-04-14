import frappe


@frappe.whitelist()
def get_dashboard_data(project=None, date_range="30"):
    """Single API call returns all dashboard widget data."""
    from frappe.utils import nowdate, add_days
    from_date = add_days(nowdate(), -int(date_range))
    to_date   = nowdate()

    filters_base = {}
    if project:
        filters_base["project"] = project

    # ── Workforce numbers ───────────────────────────────────────────
    sched_filters = {**filters_base, "docstatus": 1,
                     "date": ["between", [from_date, to_date]]}
    schedules = frappe.get_all(
        "Daily Manpower Schedule", filters=sched_filters,
        fields=["total_employees", "total_present", "total_absent", "date", "project"]
    )
    total_scheduled = sum(s.total_employees or 0 for s in schedules)
    total_present   = sum(s.total_present   or 0 for s in schedules)
    avg_attendance  = round((total_present / total_scheduled * 100)
                            if total_scheduled else 0, 1)

    # ── Open inspections ───────────────────────────────────────────
    open_inspections = frappe.db.count(
        "Inspection Report",
        {**filters_base, "docstatus": 1,
         "overall_status": ["in", ["Critical", "Needs Attention"]]}
    )

    # ── Pending audits ─────────────────────────────────────────────
    pending_audits = frappe.db.count(
        "Audit Checklist",
        {**filters_base, "docstatus": 0}  # draft = pending submission
    )

    # ── KPI on-track count ─────────────────────────────────────────
    kpi_logs = frappe.get_all(
        "KPI Log",
        filters={**filters_base, "date": ["between", [from_date, to_date]]},
        fields=["actual_value", "target_value"]
    )
    kpi_on_track = sum(
        1 for k in kpi_logs
        if (k.target_value or 0) > 0
        and (k.actual_value or 0) >= (k.target_value or 0)
    )
    kpi_total = len(kpi_logs)

    # ── Visa alerts ────────────────────────────────────────────────
    from operations_module.api.utils import get_ops_setting
    from frappe.utils import add_days
    alert_days  = int(get_ops_setting("visa_alert_days") or 30)
    visa_alerts = frappe.db.count(
        "Employee",
        {"status": "Active",
         "custom_visa_expiry_date": ["between", [nowdate(), add_days(nowdate(), alert_days)]]}
    )

    # ── Active projects ────────────────────────────────────────────
    active_projects = frappe.db.count("Project", {"status": "Open"})

    # ── Attendance trend (last 14 days) ────────────────────────────
    trend_data = frappe.db.sql("""
        SELECT date, SUM(total_present) AS present, SUM(total_absent) AS absent
        FROM `tabDaily Manpower Schedule`
        WHERE docstatus=1 AND date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY date ORDER BY date
    """, {"from_date": add_days(to_date, -14), "to_date": to_date}, as_dict=True)

    # ── Site visit status breakdown ────────────────────────────────
    sv_stats = frappe.db.sql("""
        SELECT status, COUNT(*) AS cnt FROM `tabSite Visit`
        WHERE date(planned_date) BETWEEN %(f)s AND %(t)s
        GROUP BY status
    """, {"f": from_date, "t": to_date}, as_dict=True)

    # ── Recent feedback scores ─────────────────────────────────────
    feedback = frappe.get_all(
        "Client Feedback Form",
        filters={"status": "Submitted"},
        fields=["month_year", "project", "overall_score", "client_name"],
        order_by="creation desc", limit=5
    )

    return {
        "cards": {
            "active_projects":   active_projects,
            "avg_attendance":    avg_attendance,
            "open_inspections":  open_inspections,
            "pending_audits":    pending_audits,
            "kpi_on_track":      f"{kpi_on_track}/{kpi_total}",
            "visa_alerts":       visa_alerts,
        },
        "attendance_trend":  trend_data,
        "site_visit_status": sv_stats,
        "recent_feedback":   feedback,
        "settings":          get_ops_setting("country_labour_law"),
    }
