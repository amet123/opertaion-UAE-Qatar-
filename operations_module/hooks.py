app_name = "operations_module"
app_title = "Operations Module"
app_publisher = "Your Company"
app_description = "Operations Module for ERPNext 15 — Qatar/UAE Manpower & Construction"
app_email = "admin@yourcompany.com"
app_license = "MIT"
app_version = "1.0.0"

# Required apps
required_apps = ["frappe", "erpnext"]

# ── No frontend bundles (backend-only app) ──────────────────────
# This tells bench build to skip this app
app_include_js = []
app_include_css = []

# ── DocType event hooks ──────────────────────────────────────────
doc_events = {
    "Daily Manpower Schedule": {
        "on_submit": "operations_module.api.attendance_sync.on_manpower_schedule_submit",
        "on_cancel": "operations_module.api.attendance_sync.on_manpower_schedule_cancel",
    },
    "Client Feedback Form": {
        "after_insert": "operations_module.api.kpi_engine.trigger_feedback_kpi",
    },
    "Audit Checklist": {
        "on_submit": "operations_module.api.notifications.on_audit_submit",
    },
    "Inspection Report": {
        "on_submit": "operations_module.api.notifications.on_inspection_submit",
    },
}

# ── Scheduled Tasks ──────────────────────────────────────────────
scheduler_events = {
    "daily": [
        "operations_module.api.kpi_engine.run_daily_kpis",
        "operations_module.api.notifications.check_visa_expiry",
        "operations_module.api.weekly_off_planner.assign_weekly_off",
    ],
    "weekly": [
        "operations_module.api.kpi_engine.run_weekly_kpis",
    ],
    "monthly": [
        "operations_module.api.kpi_engine.run_monthly_kpis",
        "operations_module.api.feedback.send_monthly_feedback_request",
    ],
}

# ── Fixtures ────────────────────────────────────────────────────
fixtures = [
    "Custom Field",
    "Property Setter",
    "Workspace",
    {
        "doctype": "Role",
        "filters": [["role_name", "in", [
            "Operations Manager",
            "Operations Supervisor",
            "Operations Viewer"
        ]]]
    },
]

# ── Website ─────────────────────────────────────────────────────
website_route_rules = [
    {"from_route": "/client-feedback/<n>", "to_route": "client-feedback"},
]

# ── Jinja ───────────────────────────────────────────────────────
jinja = {
    "methods": ["operations_module.api.utils.get_ops_setting"],
}
