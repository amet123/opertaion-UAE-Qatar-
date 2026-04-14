"""
Weekly Off Planner
------------------
Auto-assigns weekly off dates based on rotation rules.
Runs daily via scheduler.
"""
import frappe
from frappe.utils import nowdate, add_days, getdate, get_weekday


def assign_weekly_off():
    """
    For each active Weekly Off Planner rule,
    compute next off day for each employee in the group.
    """
    rules = frappe.get_all(
        "Weekly Off Planner",
        filters={"is_active": 1},
        fields=["name", "employee_group", "cycle_days", "pattern",
                "effective_date", "company"]
    )
    for rule in rules:
        _process_rule(rule)


def _process_rule(rule):
    """Process one rotation rule — assign weekly off for the upcoming week."""
    employees = _get_employee_group(rule.employee_group, rule.company)
    effective = getdate(rule.effective_date or nowdate())
    today = getdate(nowdate())
    cycle = int(rule.cycle_days or 7)

    for emp in employees:
        joining = getdate(
            frappe.db.get_value("Employee", emp.name, "date_of_joining") or effective
        )
        # Days since effective date
        days_elapsed = (today - effective).days
        # Position in current cycle
        cycle_pos = days_elapsed % cycle
        # Off day = last day of cycle
        off_day_offset = cycle - 1 - cycle_pos
        next_off = add_days(today, off_day_offset)

        _upsert_shift_assignment(emp.name, next_off, rule)


def _upsert_shift_assignment(employee, off_date, rule):
    """Create or update Shift Assignment with weekly off."""
    existing = frappe.db.get_value(
        "Shift Assignment",
        {"employee": employee, "start_date": off_date, "custom_is_weekly_off": 1},
        "name"
    )
    if existing:
        return  # Already assigned

    # Get employee's current shift
    current_shift = frappe.db.get_value(
        "Shift Assignment",
        {"employee": employee, "docstatus": 1},
        "shift_type",
        order_by="start_date desc"
    )
    if not current_shift:
        return

    frappe.get_doc({
        "doctype": "Shift Assignment",
        "employee": employee,
        "shift_type": current_shift,
        "start_date": off_date,
        "end_date": off_date,
        "status": "Active",
        "company": rule.company,
        "custom_is_weekly_off": 1,
        "custom_planner_rule": rule.name,
    }).insert(ignore_permissions=True)


def _get_employee_group(group_name, company):
    if group_name:
        return frappe.get_all(
            "Employee",
            filters={"employee_group": group_name, "status": "Active", "company": company},
            fields=["name", "employee_name"]
        )
    return frappe.get_all(
        "Employee",
        filters={"status": "Active", "company": company},
        fields=["name", "employee_name"]
    )


@frappe.whitelist()
def preview_off_schedule(rule_name, weeks=4):
    """Preview upcoming off days for a rule — used in UI."""
    rule = frappe.get_doc("Weekly Off Planner", rule_name)
    employees = _get_employee_group(rule.employee_group, rule.company)
    today = getdate(nowdate())
    effective = getdate(rule.effective_date or today)
    cycle = int(rule.cycle_days or 7)
    result = []

    for emp in employees[:20]:  # limit for preview
        schedule = []
        for w in range(int(weeks)):
            check_date = add_days(today, w * 7)
            days_elapsed = (check_date - effective).days
            cycle_pos = days_elapsed % cycle
            off_offset = cycle - 1 - cycle_pos
            off_day = add_days(check_date, off_offset)
            schedule.append(str(off_day))
        result.append({"employee": emp.name, "employee_name": emp.employee_name, "off_days": schedule})

    return result
