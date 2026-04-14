"""
Notifications API
-----------------
Visa expiry alerts, KPI breach, audit non-compliance, inspection alerts.
"""
import frappe
from frappe.utils import nowdate, add_days, getdate, date_diff
from operations_module.api.utils import get_ops_setting


def check_visa_expiry():
    """Daily: check employees whose visa expires within alert window."""
    alert_days = int(get_ops_setting("visa_alert_days") or 30)
    alert_date = add_days(nowdate(), alert_days)

    employees = frappe.get_all(
        "Employee",
        filters={
            "status": "Active",
            "custom_visa_expiry_date": ["between", [nowdate(), alert_date]]
        },
        fields=["name", "employee_name", "custom_visa_expiry_date",
                "custom_project", "company_email", "cell_number"]
    )

    if not employees:
        return

    ops_emails = get_ops_setting("notification_email") or ""
    recipients = [e.strip() for e in ops_emails.split(",") if e.strip()]

    for emp in employees:
        days_left = date_diff(emp.custom_visa_expiry_date, nowdate())
        _create_system_notification(
            title=f"Visa Expiry Alert — {emp.employee_name}",
            message=f"Visa expires in {days_left} days ({emp.custom_visa_expiry_date}). Project: {emp.custom_project or 'N/A'}",
            for_user=frappe.db.get_single_value("System Settings", "setup_complete") and "Administrator" or "Administrator",
            document_type="Employee",
            document_name=emp.name,
        )

    if recipients:
        frappe.sendmail(
            recipients=recipients,
            subject=f"[OPS Alert] {len(employees)} Visa(s) Expiring Soon",
            message=_visa_alert_email_body(employees),
            now=True
        )


def on_audit_submit(doc, method=None):
    """Alert if audit score below pass threshold."""
    if doc.score < (doc.pass_threshold or 70):
        ops_emails = get_ops_setting("notification_email") or ""
        recipients = [e.strip() for e in ops_emails.split(",") if e.strip()]
        subject = f"[Audit Alert] Non-compliance — {doc.project} — Score: {doc.score}%"
        message = f"""
<p>Audit checklist submitted with score <strong>{doc.score}%</strong>
(threshold: {doc.pass_threshold}%).</p>
<p>Project: {doc.project}<br>Date: {doc.date}<br>Inspector: {doc.inspector}</p>
<p>Non-compliant items: {doc.total_non_compliant or 0}</p>
"""
        if recipients:
            frappe.sendmail(recipients=recipients, subject=subject, message=message, now=True)
        _create_system_notification(
            title=subject, message=f"Score {doc.score}% — below threshold {doc.pass_threshold}%",
            document_type="Audit Checklist", document_name=doc.name
        )


def on_inspection_submit(doc, method=None):
    """Alert if critical findings exist in inspection report."""
    critical = [f for f in doc.findings if f.severity == "Critical"]
    if not critical:
        return
    ops_emails = get_ops_setting("notification_email") or ""
    recipients = [e.strip() for e in ops_emails.split(",") if e.strip()]
    subject = f"[Inspection Alert] {len(critical)} Critical Finding(s) — {doc.project}"
    if recipients:
        frappe.sendmail(
            recipients=recipients, subject=subject,
            message=f"<p>{len(critical)} critical finding(s) in Inspection Report {doc.name}. Project: {doc.project}. Inspector: {doc.inspector}.</p>",
            now=True
        )


def send_kpi_alert(kpi_name, project, actual, target, alert_email=None):
    """Send KPI breach notification."""
    ops_emails = get_ops_setting("notification_email") or ""
    recipients = [e.strip() for e in ops_emails.split(",") if e.strip()]
    if alert_email:
        recipients.append(alert_email)

    subject = f"[KPI Alert] {kpi_name} below target — {project}"
    message = f"""
<p>KPI <strong>{kpi_name}</strong> for project <strong>{project}</strong>
has fallen below target.</p>
<p>Actual: <strong>{actual}</strong> &nbsp;|&nbsp; Target: <strong>{target}</strong></p>
"""
    if recipients:
        frappe.sendmail(recipients=list(set(recipients)), subject=subject, message=message, now=True)

    _create_system_notification(
        title=subject,
        message=f"Actual {actual} vs Target {target}",
        document_type="KPI Log",
    )


def _create_system_notification(title, message, for_user="Administrator",
                                 document_type=None, document_name=None):
    n = frappe.get_doc({
        "doctype": "Notification Log",
        "subject": title,
        "email_content": message,
        "for_user": for_user,
        "type": "Alert",
        "document_type": document_type,
        "document_name": document_name,
    })
    n.insert(ignore_permissions=True)


def _visa_alert_email_body(employees):
    rows = "".join(
        f"<tr><td>{e.employee_name}</td><td>{e.custom_visa_expiry_date}</td>"
        f"<td>{date_diff(e.custom_visa_expiry_date, nowdate())} days</td>"
        f"<td>{e.custom_project or '-'}</td></tr>"
        for e in employees
    )
    return f"""
<p>The following employees have visas expiring soon:</p>
<table border="1" cellpadding="6" cellspacing="0">
<tr><th>Name</th><th>Expiry Date</th><th>Days Left</th><th>Project</th></tr>
{rows}
</table>
"""
