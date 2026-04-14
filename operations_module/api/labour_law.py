"""
Labour Law Calculator
---------------------
Supports: Qatar (Law No. 14 of 2004, amended 2020)
          UAE   (Federal Decree-Law No. 33 of 2021)
Switched via Operations Settings → country_labour_law
"""
import frappe
from frappe.utils import getdate
from operations_module.api.utils import get_ops_setting


# ─── OT RATES ────────────────────────────────────────────────────────────────

QATAR_OT_NORMAL      = 1.25   # 25% above basic
QATAR_OT_NIGHT_FRI   = 1.50   # night (21:00-04:00) or Friday
QATAR_OT_ALLOWANCE   = 25.0   # QAR per OT hour (Art. 74)
QATAR_NIGHT_START    = 21
QATAR_NIGHT_END      = 4

UAE_OT_NORMAL        = 1.25   # 25% above basic
UAE_OT_NIGHT_WEEKEND = 1.50   # night (22:00-04:00) or weekend
UAE_NIGHT_START      = 22
UAE_NIGHT_END        = 4


def calculate_ot_amount(employee, ot_hours, shift_start, day_of_week):
    """
    Calculate OT pay for one employee.
    shift_start: datetime.time object
    day_of_week: 0=Monday … 6=Sunday
    Returns float (amount in local currency)
    """
    law = get_ops_setting("country_labour_law") or "Qatar"
    hourly_rate = _get_hourly_rate(employee)

    if not hourly_rate:
        frappe.log_error(
            f"No hourly rate for employee {employee}",
            "OT Calculation Error"
        )
        return 0

    if law == "Qatar":
        return _qatar_ot(hourly_rate, ot_hours, shift_start, day_of_week)
    elif law == "UAE":
        return _uae_ot(hourly_rate, ot_hours, shift_start, day_of_week)
    else:  # "Both" — return higher of two (protective interpretation)
        qa = _qatar_ot(hourly_rate, ot_hours, shift_start, day_of_week)
        ae = _uae_ot(hourly_rate, ot_hours, shift_start, day_of_week)
        return max(qa, ae)


def _qatar_ot(hourly_rate, ot_hours, shift_start, day_of_week):
    hour = shift_start.hour if shift_start else 8
    is_night = hour >= QATAR_NIGHT_START or hour < QATAR_NIGHT_END
    is_friday = (day_of_week == 4)
    rate = QATAR_OT_NIGHT_FRI if (is_night or is_friday) else QATAR_OT_NORMAL
    base_ot = hourly_rate * rate * ot_hours
    allowance = QATAR_OT_ALLOWANCE * ot_hours
    return round(base_ot + allowance, 2)


def _uae_ot(hourly_rate, ot_hours, shift_start, day_of_week):
    hour = shift_start.hour if shift_start else 8
    is_night = hour >= UAE_NIGHT_START or hour < UAE_NIGHT_END
    is_weekend = (day_of_week >= 4)  # Fri/Sat in UAE
    rate = UAE_OT_NIGHT_WEEKEND if (is_night or is_weekend) else UAE_OT_NORMAL
    return round(hourly_rate * rate * ot_hours, 2)


def _get_hourly_rate(employee):
    rate = frappe.db.get_value("Employee", employee, "custom_hourly_rate")
    if rate:
        return float(rate)
    # Fallback: derive from basic salary ÷ 208 (26 days × 8 hrs)
    basic = frappe.db.get_value("Employee", employee, "one_fm_basic_salary") or 0
    return round(float(basic) / 208, 4)


# ─── END OF SERVICE ───────────────────────────────────────────────────────────

def calculate_eos(employee, termination_date=None):
    """
    End of Service Gratuity calculation.
    Qatar: Art. 54 — 3 weeks/year (≤5yrs), 4 weeks/year (>5yrs)
    UAE:   Art. 51 — 21 days/year (≤5yrs), 30 days/year (>5yrs)
    """
    law = get_ops_setting("country_labour_law") or "Qatar"
    emp = frappe.get_doc("Employee", employee)
    end_date = getdate(termination_date or frappe.utils.nowdate())
    joining = getdate(emp.date_of_joining)
    years = (end_date - joining).days / 365.0
    basic = float(emp.one_fm_basic_salary or 0)
    daily_rate = basic / 30

    if law == "Qatar":
        if years <= 5:
            gratuity = daily_rate * 21 * years
        else:
            gratuity = (daily_rate * 21 * 5) + (daily_rate * 28 * (years - 5))
    else:  # UAE
        if years <= 5:
            gratuity = daily_rate * 21 * years
        else:
            gratuity = (daily_rate * 21 * 5) + (daily_rate * 30 * (years - 5))

    return {
        "employee": employee,
        "law": law,
        "years_of_service": round(years, 2),
        "basic_salary": basic,
        "daily_rate": round(daily_rate, 4),
        "gratuity_amount": round(gratuity, 2),
        "termination_date": str(end_date),
    }


# ─── ANNUAL LEAVE ENTITLEMENT ─────────────────────────────────────────────────

def get_annual_leave_days(employee):
    """
    Qatar: 3 weeks (yr 1-5), 4 weeks (5+ yrs)
    UAE:   30 calendar days (after 1 yr), 2 days/month (< 1 yr)
    """
    law = get_ops_setting("country_labour_law") or "Qatar"
    joining = getdate(frappe.db.get_value("Employee", employee, "date_of_joining"))
    years = (getdate(frappe.utils.nowdate()) - joining).days / 365.0

    if law == "Qatar":
        return 28 if years >= 5 else 21
    else:  # UAE
        if years >= 1:
            return 30
        else:
            months = (getdate(frappe.utils.nowdate()) - joining).days / 30
            return int(months * 2)


@frappe.whitelist()
def calculate_eos_api(employee, termination_date=None):
    """Whitelisted for use from client-side / Print Format."""
    return calculate_eos(employee, termination_date)
