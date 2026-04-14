/**
 * Operations Dashboard
 * ERPNext 15 — Qatar/UAE Manpower & Construction
 */
frappe.pages["operations-dashboard"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Operations Dashboard",
        single_column: true,
    });

    // ── Filters ──────────────────────────────────────────────────
    const project_filter = page.add_field({
        fieldtype: "Link",
        fieldname: "project",
        options:   "Project",
        label:     "Project",
        change() { load_dashboard(); },
    });

    const range_filter = page.add_field({
        fieldtype: "Select",
        fieldname: "date_range",
        label:     "Period",
        options:   ["7 Days", "30 Days", "90 Days"],
        default:   "30 Days",
        change() { load_dashboard(); },
    });

    page.add_action_btn("Refresh", () => load_dashboard(), "octicon octicon-sync");

    // ── Layout ───────────────────────────────────────────────────
    const $body = $(wrapper).find(".layout-main-section");
    $body.html(`
        <div id="ops-dash" style="padding:16px">
            <!-- Law badge -->
            <div id="law-badge" style="margin-bottom:16px"></div>

            <!-- Number cards -->
            <div id="cards" class="row" style="margin-bottom:20px"></div>

            <!-- Charts row -->
            <div class="row">
                <div class="col-sm-8">
                    <div class="frappe-card" style="padding:16px">
                        <h6 class="text-muted" style="margin-bottom:12px">Attendance Trend (last 14 days)</h6>
                        <div id="att-chart"></div>
                    </div>
                </div>
                <div class="col-sm-4">
                    <div class="frappe-card" style="padding:16px">
                        <h6 class="text-muted" style="margin-bottom:12px">Site Visit Status</h6>
                        <div id="sv-chart"></div>
                    </div>
                </div>
            </div>

            <!-- Feedback table -->
            <div class="frappe-card" style="padding:16px;margin-top:16px">
                <h6 class="text-muted" style="margin-bottom:12px">Recent Client Feedback</h6>
                <div id="feedback-table"></div>
            </div>
        </div>
    `);

    // ── Load ─────────────────────────────────────────────────────
    function load_dashboard() {
        const project    = project_filter.get_value();
        const range_val  = (range_filter.get_value() || "30 Days").split(" ")[0];

        frappe.show_progress("Loading dashboard...", 0, 100);

        frappe.call({
            method: "operations_module.page.operations_dashboard.operations_dashboard.get_dashboard_data",
            args: { project: project || null, date_range: range_val },
            callback(r) {
                frappe.hide_progress();
                if (!r.message) return;
                render_all(r.message);
            },
        });
    }

    // ── Render ───────────────────────────────────────────────────
    function render_all(data) {
        render_law_badge(data.settings);
        render_cards(data.cards);
        render_attendance_chart(data.attendance_trend);
        render_sv_chart(data.site_visit_status);
        render_feedback(data.recent_feedback);
    }

    function render_law_badge(law) {
        const color = law === "Qatar" ? "#6941C6" : law === "UAE" ? "#027A48" : "#B54708";
        $("#law-badge").html(`
            <span style="background:${color}15;color:${color};
                border:1px solid ${color}40;border-radius:6px;
                padding:4px 12px;font-size:12px;font-weight:500">
                Active Law: ${law || "Qatar"}
            </span>
        `);
    }

    function render_cards(c) {
        if (!c) return;
        const cards = [
            { label: "Active Projects",    value: c.active_projects,  icon: "building", color: "#2490EF" },
            { label: "Avg Attendance",     value: c.avg_attendance + "%", icon: "users", color: "#28a745" },
            { label: "Open Inspections",   value: c.open_inspections, icon: "alert-circle", color: c.open_inspections > 0 ? "#E65C00" : "#28a745" },
            { label: "Pending Audits",     value: c.pending_audits,   icon: "clipboard", color: c.pending_audits > 0 ? "#E65C00" : "#28a745" },
            { label: "KPIs On Track",      value: c.kpi_on_track,     icon: "trending-up", color: "#2490EF" },
            { label: "Visa Alerts",        value: c.visa_alerts,      icon: "alert-triangle", color: c.visa_alerts > 0 ? "#dc3545" : "#28a745" },
        ];
        const html = cards.map(card => `
            <div class="col-sm-2">
                <div class="frappe-card text-center" style="padding:16px;cursor:default">
                    <div style="font-size:22px;font-weight:600;color:${card.color}">${card.value}</div>
                    <div class="text-muted" style="font-size:11px;margin-top:4px">${card.label}</div>
                </div>
            </div>
        `).join("");
        $("#cards").html(html);
    }

    function render_attendance_chart(trend) {
        if (!trend || !trend.length) {
            $("#att-chart").html('<p class="text-muted" style="font-size:12px">No data</p>');
            return;
        }
        new frappe.Chart("#att-chart", {
            data: {
                labels:   trend.map(t => frappe.datetime.str_to_user(t.date)),
                datasets: [
                    { name: "Present", values: trend.map(t => t.present || 0), chartType: "bar" },
                    { name: "Absent",  values: trend.map(t => t.absent  || 0), chartType: "bar" },
                ],
            },
            type:        "bar",
            height:      220,
            colors:      ["#28a745", "#dc3545"],
            barOptions:  { stacked: true },
            axisOptions: { xAxisMode: "tick" },
            tooltipOptions: { formatTooltipX: d => d },
        });
    }

    function render_sv_chart(sv_stats) {
        if (!sv_stats || !sv_stats.length) {
            $("#sv-chart").html('<p class="text-muted" style="font-size:12px">No visits</p>');
            return;
        }
        new frappe.Chart("#sv-chart", {
            data: {
                labels:   sv_stats.map(s => s.status),
                datasets: [{ values: sv_stats.map(s => s.cnt) }],
            },
            type:   "pie",
            height: 220,
            colors: ["#2490EF", "#28a745", "#E65C00", "#dc3545"],
        });
    }

    function render_feedback(feedback) {
        if (!feedback || !feedback.length) {
            $("#feedback-table").html('<p class="text-muted" style="font-size:12px">No feedback submitted yet</p>');
            return;
        }
        const rows = feedback.map(f => {
            const score = parseFloat(f.overall_score || 0);
            const color = score >= 4 ? "#28a745" : score >= 3 ? "#E65C00" : "#dc3545";
            return `<tr>
                <td>${f.month_year || "-"}</td>
                <td>${f.project || "-"}</td>
                <td>${f.client_name || "-"}</td>
                <td><strong style="color:${color}">${score.toFixed(1)} / 5</strong></td>
            </tr>`;
        }).join("");
        $("#feedback-table").html(`
            <table class="table table-condensed" style="font-size:13px">
                <thead><tr>
                    <th>Period</th><th>Project</th><th>Client</th><th>Score</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `);
    }

    // ── Initial load ─────────────────────────────────────────────
    load_dashboard();
};
