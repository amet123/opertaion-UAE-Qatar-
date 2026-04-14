"""
Client Feedback API
-------------------
Monthly email trigger, token verification, Web Form integration.
"""
import frappe
from frappe.utils import nowdate, add_days, getdate
from operations_module.api.utils import get_ops_setting, get_site_url


def send_monthly_feedback_request():
    """Scheduler: runs monthly — sends feedback URL to all active project clients."""
    projects = frappe.get_all(
        "Project",
        filters={"status": "Open", "custom_feedback_enabled": 1},
        fields=["name", "project_name", "custom_client_email", "custom_client_name"]
    )

    sent = 0
    for p in projects:
        if not p.custom_client_email:
            continue
        token = frappe.generate_hash(length=24)
        expiry = add_days(nowdate(), 7)

        # Create draft feedback form
        form = frappe.get_doc({
            "doctype": "Client Feedback Form",
            "project": p.name,
            "month_year": _current_month_year(),
            "client_email": p.custom_client_email,
            "client_name": p.custom_client_name,
            "access_token": token,
            "token_expiry": expiry,
            "status": "Pending",
        })
        form.insert(ignore_permissions=True)

        portal_url = f"{get_site_url()}/client-feedback?project={p.name}&token={token}"
        _send_feedback_email(p, portal_url, expiry)
        sent += 1

    frappe.logger().info(f"[Feedback] Sent {sent} monthly feedback requests")


def _send_feedback_email(project, url, expiry):
    subject = f"Monthly Service Feedback — {project.project_name}"
    message = f"""
<p>Dear {project.custom_client_name or 'Valued Client'},</p>
<p>Please take a moment to share your feedback for <strong>{project.project_name}</strong>
for {_current_month_year()}.</p>
<p><a href="{url}" style="background:#1a73e8;color:#fff;padding:10px 20px;border-radius:4px;text-decoration:none;">
Submit Feedback</a></p>
<p style="color:#666;font-size:12px;">Link valid until {expiry}.</p>
"""
    frappe.sendmail(
        recipients=[project.custom_client_email],
        subject=subject,
        message=message,
        now=True
    )


@frappe.whitelist(allow_guest=True)
def verify_token(token, project):
    """Web Form calls this to validate the access token."""
    form = frappe.db.get_value(
        "Client Feedback Form",
        {"project": project, "access_token": token, "status": "Pending"},
        ["name", "token_expiry"],
        as_dict=True
    )
    if not form:
        return {"valid": False, "reason": "Token not found"}
    if getdate(form.token_expiry) < getdate(nowdate()):
        return {"valid": False, "reason": "Token expired"}
    return {"valid": True, "form_name": form.name}


@frappe.whitelist(allow_guest=True)
def submit_feedback(token, project, ratings, overall_comment=""):
    """Web Form submit handler."""
    verify = verify_token(token, project)
    if not verify.get("valid"):
        frappe.throw(verify.get("reason", "Invalid token"))

    form = frappe.get_doc("Client Feedback Form", verify["form_name"])
    # Populate ratings from Web Form submission
    import json
    rating_list = json.loads(ratings) if isinstance(ratings, str) else ratings
    for r in rating_list:
        form.append("ratings", {
            "parameter": r.get("parameter"),
            "rating": r.get("rating"),
            "comments": r.get("comments"),
        })

    form.overall_comment = overall_comment
    form.overall_score = round(
        sum(r.get("rating", 0) for r in rating_list) / len(rating_list), 2
    ) if rating_list else 0
    form.status = "Submitted"
    form.save(ignore_permissions=True)

    return {"success": True, "score": form.overall_score}


def _current_month_year():
    from frappe.utils import getdate
    d = getdate(nowdate())
    return d.strftime("%B %Y")
