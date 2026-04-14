# Operations Module — ERPNext 15
### Qatar / UAE — Manpower & Construction Industry

---

## Features

| Feature | Type | Status |
|---|---|---|
| Global Settings (law/attendance/KPI switch) | Single DocType | ✅ |
| Daily Manpower Schedule + Auto Attendance | Custom DocType | ✅ |
| Manual OT Entry → Additional Salary | hook | ✅ |
| Qatar Labour Law (Art. 74, OT + EOS) | calculator | ✅ |
| UAE Labour Law (Decree 33/2021) | calculator | ✅ |
| Dual-law switch via Global Settings | setting | ✅ |
| KPI Master + Script Engine | Custom DocType + exec | ✅ |
| KPI Log + Scheduler auto-compute | scheduled task | ✅ |
| KPI Breach Email Alert | notification | ✅ |
| Client Feedback Form (Web, token-secured) | www page + API | ✅ |
| Monthly Feedback Email (scheduler) | scheduler | ✅ |
| Site Visit Planning + Image Upload | Custom DocType | ✅ |
| Inspection Report + Severity + Images | Custom DocType | ✅ |
| Audit Checklist + Score Auto-calc | Custom DocType | ✅ |
| Weekly Off Planner (7-day rotation) | Custom DocType + scheduler | ✅ |
| Machinery Register | Custom DocType | ✅ |
| Visa Expiry Alert | daily scheduler | ✅ |
| Daily Workforce Summary Report | Script Report | ✅ |
| KPI Trend Report | Script Report | ✅ |
| Operational Leave Report (EOS aware) | Script Report | ✅ |
| Audit Compliance Report | Script Report | ✅ |
| Operations Dashboard (Page) | frappe.Chart | ✅ |
| Custom Fields on Employee/Project/Attendance | fixtures | ✅ |
| Roles: Manager / Supervisor / Viewer | fixtures | ✅ |

---

## Installation

```bash
# 1. Get the app
cd /path/to/frappe-bench
bench get-app operations_module /path/to/operations_module
# OR from git:
# bench get-app operations_module https://github.com/yourorg/operations_module

# 2. Install on site
bench --site yoursite.local install-app operations_module

# 3. Run migrations + fixtures
bench --site yoursite.local migrate
bench --site yoursite.local import-fixtures --app operations_module

# 4. Clear cache
bench --site yoursite.local clear-cache
bench --site yoursite.local clear-website-cache
```

---

## First-time Setup

### Step 1 — Operations Settings
Go to: **Operations → Settings → Operations Settings**

| Field | Recommended Value |
|---|---|
| Country / Labour Law | Qatar / UAE / Both |
| Attendance Mode | Manual |
| KPI Compute Method | Script |
| OT Rate Qatar | 1.25 |
| OT Rate UAE | 1.25 |
| OT Salary Component | Overtime Pay (create in Payroll) |
| Notification Email | ops.manager@company.com |
| Visa Alert Days Before | 30 |

### Step 2 — Employee Custom Fields
- `custom_hourly_rate` — set for every employee (used for OT calc)
- `custom_visa_expiry_date` — mandatory for Qatar/UAE compliance
- `custom_trade` — e.g. Mason, Electrician, Driver

### Step 3 — Project Custom Fields
- `custom_client_country` — Qatar or UAE
- `custom_client_email` — for monthly feedback emails
- `custom_feedback_enabled` — check to enable monthly feedback

### Step 4 — KPI Setup
1. Create **KPI Master** records (pre-built scripts in this README below)
2. Create **Project KPI Assignment** for each project + KPI
3. Set target values and alert thresholds

### Step 5 — Roles & Permissions
Assign roles:
- **Operations Manager** — full access + settings
- **Operations Supervisor** — create/submit daily schedules, inspections
- **Operations Viewer** — read-only, reports, dashboard

---

## Built-in KPI Scripts (copy into KPI Master → compute_script)

### Workforce Utilization %
```python
scheduled = frappe.db.sql(
    "SELECT SUM(total_employees) FROM `tabDaily Manpower Schedule` WHERE project=%s AND date=%s AND docstatus=1",
    (project, date)
)[0][0] or 0
present = frappe.db.sql(
    "SELECT SUM(total_present) FROM `tabDaily Manpower Schedule` WHERE project=%s AND date=%s AND docstatus=1",
    (project, date)
)[0][0] or 0
result = round((present / scheduled * 100) if scheduled else 0, 2)
```

### Audit Pass Rate %
```python
audits = frappe.get_all("Audit Checklist",
    filters={"project": project, "date": date, "docstatus": 1},
    fields=["score", "pass_threshold"])
passed = sum(1 for a in audits if (a.score or 0) >= (a.pass_threshold or 70))
result = round((passed / len(audits) * 100) if audits else 100, 2)
```

### Avg Client Feedback Score (Monthly)
```python
from frappe.utils import get_first_day, get_last_day
scores = frappe.get_all("Client Feedback Form",
    filters={"project": project, "status": "Submitted",
             "creation": ["between", [get_first_day(date), get_last_day(date)]]},
    fields=["overall_score"])
result = round(sum(s.overall_score or 0 for s in scores) / len(scores), 2) if scores else 0
```

### Open Critical Inspection Findings
```python
result = frappe.db.count("Inspection Finding",
    {"parent": ["in",
        frappe.get_all("Inspection Report",
            filters={"project": project, "docstatus": 1},
            pluck="name")
    ], "severity": "Critical", "status": ["!=", "Closed"]})
```

---

## Scheduler Events Summary

| Event | Task |
|---|---|
| Daily | Run Daily KPIs, Visa Expiry Alert, Weekly Off Assignment |
| Weekly | Run Weekly KPIs |
| Monthly | Run Monthly KPIs, Send Client Feedback Emails |

---

## Labour Law Reference

### Qatar — Law No. 14 of 2004 (amended 2020)
- Normal OT: Basic × 1.25 + QAR 25/hr allowance
- Night OT (21:00–04:00): Basic × 1.50
- Friday OT: Basic × 1.50
- Max OT: 2 hrs/day
- Annual Leave: 21 days (yr 1–5), 28 days (5+ yrs)
- EOS: 21 days/year (≤5 yrs), 28 days/year (>5 yrs)

### UAE — Federal Decree-Law No. 33 of 2021
- Normal OT: Basic × 1.25
- Night OT (22:00–04:00): Basic × 1.50
- Weekend OT (Fri/Sat): Basic × 1.50
- Max OT: 2 hrs/day, 144 hrs/quarter
- Annual Leave: 30 calendar days (after 1 yr), 2 days/month (<1 yr)
- EOS: 21 days/year (≤5 yrs), 30 days/year (>5 yrs)

---

## File Structure

```
operations_module/
├── setup.py
├── README.md
├── requirements.txt
└── operations_module/
    ├── __init__.py
    ├── hooks.py
    ├── api/
    │   ├── utils.py              # get_ops_setting() helper
    │   ├── attendance_sync.py    # Manual attendance creation
    │   ├── labour_law.py         # Qatar/UAE OT + EOS + leave calc
    │   ├── kpi_engine.py         # Script execution + KPI logging
    │   ├── feedback.py           # Monthly email + token verify
    │   ├── notifications.py      # Visa/audit/inspection/KPI alerts
    │   └── weekly_off_planner.py # 7-day rotation logic
    ├── doctype/
    │   ├── operations_settings/
    │   ├── daily_manpower_schedule/
    │   ├── manpower_employee_detail/  (child)
    │   ├── kpi_master/
    │   ├── kpi_log/
    │   ├── project_kpi_assignment/
    │   ├── client_feedback_form/
    │   ├── client_feedback_rating/    (child)
    │   ├── site_visit/
    │   ├── site_visit_image/          (child)
    │   ├── inspection_report/
    │   ├── inspection_finding/        (child)
    │   ├── audit_checklist/
    │   ├── audit_checklist_item/      (child)
    │   ├── weekly_off_planner/
    │   └── machinery_register/
    ├── report/
    │   ├── daily_workforce_summary/
    │   ├── kpi_trend_report/
    │   ├── operational_leave_report/
    │   └── audit_compliance_report/
    ├── page/
    │   └── operations_dashboard/
    │       ├── operations_dashboard.json
    │       ├── operations_dashboard.py
    │       └── operations_dashboard.js
    ├── www/
    │   └── client-feedback.html
    └── fixtures/
        ├── custom_fields.json
        ├── workspace.json
        └── roles.json
```
