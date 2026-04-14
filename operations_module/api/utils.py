import frappe


def get_ops_setting(field):
    """Central helper — fetch any field from Operations Settings single DocType."""
    return frappe.db.get_single_value("Operations Settings", field)


def get_labour_law():
    return get_ops_setting("country_labour_law") or "Qatar"


def get_site_url():
    return frappe.utils.get_url()


@frappe.whitelist()
def get_all_settings():
    """Return all ops settings as dict — used by Dashboard JS."""
    doc = frappe.get_single("Operations Settings")
    return {
        "country_labour_law": doc.country_labour_law,
        "attendance_mode": doc.attendance_mode,
        "kpi_compute_method": doc.kpi_compute_method,
        "ot_rate_qatar": doc.ot_rate_qatar,
        "ot_rate_uae": doc.ot_rate_uae,
        "visa_alert_days": doc.visa_alert_days,
    }
