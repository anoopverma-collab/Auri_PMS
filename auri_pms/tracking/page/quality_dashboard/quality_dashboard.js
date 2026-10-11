// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

/* global auri_pms */
// Quality: defect flow, fix time, reopen rate and critical bugs for all projects or one project.
let ui; // shared UI kit (auri_hub.bundle.js)

frappe.pages["quality-dashboard"].on_page_load = function (wrapper) {
	frappe.require("auri_hub.bundle.js", () => {
		ui = auri_pms.ui;
		wrapper.quality = new QualityDashboard(wrapper);
		wrapper.quality.load();
	});
};

frappe.pages["quality-dashboard"].on_page_show = function (wrapper) {
	if (!wrapper.quality) return;
	// the Project Hub opens this page with route options {project}
	if (frappe.route_options && frappe.route_options.project !== undefined) {
		wrapper.quality.project_field.set_value(frappe.route_options.project || "");
		frappe.route_options = null;
	}
	wrapper.quality.load();
};

class QualityDashboard {
	constructor(wrapper) {
		const { page, $body } = ui.initPage(wrapper, "Quality Dashboard");
		this.page = page;
		this.$body = $body;
		this.project_field = page.add_field({
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
			change: () => this.load(),
		});
	}

	load() {
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		ui.applyTheme(this.$body);
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub"));
		this.page.add_inner_button(__("Refresh"), () => this.load());
		ui.addPeriodMenu(this.page, () => this.load());
		ui.addThemeMenu(this.page, () => this.load());
		this.project = this.project_field.get_value() || "";
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		frappe.xcall("auri_pms.tracking.api.get_quality", { project: this.project, period: ui.getPeriod() }).then((data) => {
			this.data = data;
			this.render();
		});
	}

	render() {
		const d = this.data;
		const esc = ui.esc;
		const { tile, panel, stack, bar, table } = ui;
		const scope = this.project ? esc(this.project) : __("all projects");
		if (!d.defect_trackers.length) {
			this.$body.html(`<div class="hub-title"><h4>${__("Quality Dashboard")}</h4></div>${panel(__("No defect tracker"), `<div class="text-muted">${__("Open a Ticket Type (for example Bug) and tick \"Counts as Defect\" so its tickets appear here.")}</div>`)}`);
			return;
		}
		if (!d.has_data) {
			this.$body.html(`<div class="hub-title"><h4>${__("Quality Dashboard")}</h4><span class="text-muted">${scope}</span></div>${panel(__("No bugs yet"), `<div class="text-muted">${__("Nothing was reported on the defect trackers ({0}).", [d.defect_trackers.join(", ")])}</div>`)}`);
			return;
		}
		const t = d.tiles;
		const bugs = (filters) => ui.go("Work Item", { tracker: ["in", d.defect_trackers], ...(this.project ? { project: this.project } : {}), ...filters });
		const per = d.bucket === "month" ? __("monthly") : __("weekly");
		const dash = (v, suffix) => (v === null || v === undefined ? "-" : `${v}${suffix || ""}`);
		const critical = table(d.critical, [__("Bug"), __("Summary"), __("Priority"), __("Age"), __("Owner")], (b) =>
			`<tr><td style="white-space:nowrap">${ui.link("Work Item", b.name)}</td><td>${esc(b.subject)} ${cint(b.client) ? `<span class="hub-badge hub-badge-warn">${__("Waiting on client")}</span>` : ""}<div class="hub-sub">${esc(b.project)}</div></td><td>${esc(__(b.priority))}</td><td class="${b.age_days > 7 ? "text-danger" : ""}">${ui.days(b.age_days)}</td><td>${esc(b.assignee)}</td></tr>`);
		const projects = d.by_project.length
			? panel(__("Bugs by project"), table(d.by_project, [__("Project"), __("Open"), __("Closed"), __("New tickets")], (p) =>
				`<tr class="hub-clickrow" data-project="${esc(p.project)}"><td>${esc(p.label)}</td><td>${p.open}</td><td>${p.closed}</td><td>${p.created_period}</td></tr>`))
			: "";
		this.$body.html(`
			<div class="hub-title"><h4>${__("Quality")}</h4><span class="text-muted">${scope} · ${__(ui.PERIOD_NOTE[d.period])} · ${__("defect ticket types: {0}", [esc(d.defect_trackers.join(", "))])}</span></div>
			${ui.statusBanner(d.status, __("quality"))}
			<div class="hub-tiles">
				${tile(t.open, __("Open bugs"), "hub-blue", `${t.client_open ? `${t.client_open} ${__("waiting on client")} · ` : ""}${t.closed} ${__("fixed so far")}`, bugs({ is_closed: 0 }))}
				${tile(t.critical_open, __("Critical open"), t.critical_open ? "hub-red" : "hub-teal", "", bugs({ is_closed: 0, priority: ["in", ["Urgent", "Immediate"]] }))}
				${tile(t.opened_period, __("Opened in range"), "hub-orange", "", bugs({ creation: [">=", d.range_start] }))}
				${tile(t.fixed_period, __("Fixed in range"), "hub-green", "", bugs({ is_closed: 1, closed_on: [">=", d.range_start] }))}
				${tile(dash(t.avg_fix_days), __("Avg days to fix"), "hub-purple", "", bugs({ is_closed: 1 }))}
				${tile(`${t.bug_share_pct}%`, __("Bugs among new tickets"), "hub-cyan", "", ui.go("Work Item", { ...(this.project ? { project: this.project } : {}), creation: [">=", d.range_start] }))}
				${tile(dash(t.density), __("Bugs per 100 hours"), "hub-teal", "", ui.go("Time Entry", this.project ? { project: this.project, date: [">=", d.range_start] } : { date: [">=", d.range_start] }))}
				${tile(`${t.reopen_rate}%`, __("Reopen rate"), t.reopen_rate > 15 ? "hub-red" : "hub-green", __("{0} reopened", [t.reopened]), ui.go("Work Item", { name: ["in", t.reopened_names.length ? t.reopened_names : ["-"]] }))}
			</div>
			<div class="hub-cols hub-cols-even">
				<div class="hub-col">
					${panel(`${__("Bugs opened vs fixed")} (${per})`, `<div class="hub-chart" id="q-flow"></div>`)}
					${panel(__("Time to fix by priority (days)"), d.fix_time.length ? d.fix_time.map((r) => bar(`${__(r.priority)} (${r.count})`, r.days, Math.max(...d.fix_time.map((x) => x.days)))).join("") : `<div class="text-muted small">${__("Nothing fixed in this range")}</div>`)}
					${panel(__("Bugs by category"), stack(d.by_category.map((r) => [r.label, r.open, r.closed]), [__("Open"), __("Fixed")], ["seg-orange", "seg-green"]))}
					${d.by_module.some((r) => r.label !== __("(no module)")) ? panel(__("Bugs by module"), stack(d.by_module.map((r) => [r.label, r.open, r.closed]), [__("Open"), __("Fixed")], ["seg-orange", "seg-green"])) : ""}
					${projects}
				</div>
				<div class="hub-col">
					${panel(`${__("Open bug backlog")} (${per})`, `<div class="hub-chart" id="q-trend"></div>`)}
					${panel(`${__("Bugs reopened")} (${per})`, `<div class="hub-chart" id="q-reopen"></div>`)}
					${panel(__("Open bugs by priority"), stack(d.open_by_priority.map((r) => [__(r.label), r.count - r.client, r.client]), [__("With us"), __("Waiting on client")], ["seg-blue", "seg-orange"]))}
					${panel(__("Age of open bugs"), `<div class="hub-chart" id="q-aging"></div>`)}
					${panel(__("Critical bugs still open"), critical)}
				</div>
			</div>`);
		ui.bindTiles(this.$body);
		this.$body.find("tr[data-project]").on("click", (e) => this.project_field.set_value($(e.currentTarget).data("project")));
		const p = ui.PALETTE;
		ui.chart(this.$body, "#q-flow", { type: "bar", data: { labels: d.labels, datasets: [{ name: __("Opened"), values: d.flow.opened }, { name: __("Fixed"), values: d.flow.fixed }] }, colors: [p.orange, p.green] });
		ui.chart(this.$body, "#q-trend", { type: "line", data: { labels: d.labels, datasets: [{ name: __("Open bugs"), values: d.flow.open_trend }] }, colors: [p.red], lineOptions: { regionFill: 1 } });
		ui.chart(this.$body, "#q-reopen", { type: "bar", height: 180, data: { labels: d.labels, datasets: [{ name: __("Reopened"), values: d.flow.reopened }] }, colors: [p.purple], barOptions: { spaceRatio: 0.5 } });
		ui.chart(this.$body, "#q-aging", { type: "bar", height: 200, data: { labels: d.aging.map((a) => a.label), datasets: [{ name: __("With us"), values: d.aging.map((a) => a.count - a.client) }, { name: __("Waiting on client"), values: d.aging.map((a) => a.client) }] }, colors: [p.blue, p.orange], barOptions: { stacked: 1, spaceRatio: 0.5 } });
	}
}
