// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

/* global auriga_track */
// Quality: defect flow, fix time, reopen rate and critical bugs for all projects or one project.
let ui; // shared UI kit (auriga_hub.bundle.js)

frappe.pages["quality-dashboard"].on_page_load = function (wrapper) {
	frappe.require("auriga_hub.bundle.js", () => {
		ui = auriga_track.ui;
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
		frappe.xcall("auriga_track.tracking.api.get_quality", { project: this.project, period: ui.getPeriod() }).then((data) => {
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
		const per = d.bucket === "month" ? __("monthly") : __("weekly");
		const dash = (v, suffix) => (v === null || v === undefined ? "-" : `${v}${suffix || ""}`);
		const critical = table(d.critical, [__("Bug"), __("Summary"), __("Priority"), __("Age"), __("Owner")], (b) =>
			`<tr><td style="white-space:nowrap">${ui.link("Work Item", b.name)}</td><td>${esc(b.subject)}<div class="hub-sub">${esc(b.project)}</div></td><td>${esc(__(b.priority))}</td><td class="${b.age_days > 7 ? "text-danger" : ""}">${__("{0} days", [b.age_days])}</td><td>${esc(b.assignee)}</td></tr>`);
		const projects = d.by_project.length
			? panel(__("Bugs by project"), table(d.by_project, [__("Project"), __("Open"), __("Closed"), __("New tickets")], (p) =>
				`<tr class="hub-clickrow" data-project="${esc(p.project)}"><td>${esc(p.label)}</td><td>${p.open}</td><td>${p.closed}</td><td>${p.created_period}</td></tr>`))
			: "";
		this.$body.html(`
			<div class="hub-title"><h4>${__("Quality")}</h4><span class="text-muted">${scope} · ${__(ui.PERIOD_NOTE[d.period])} · ${__("defect trackers: {0}", [esc(d.defect_trackers.join(", "))])}</span></div>
			${ui.statusBanner(d.status, __("quality score"))}
			<div class="hub-tiles">
				${tile(t.open, __("Open bugs"), "hub-blue", `${t.closed} ${__("fixed so far")}`)}
				${tile(t.critical_open, __("Critical open"), t.critical_open ? "hub-red" : "hub-teal")}
				${tile(t.opened_period, __("Opened in range"), "hub-orange")}
				${tile(t.fixed_period, __("Fixed in range"), "hub-green")}
				${tile(dash(t.avg_fix_days), __("Avg days to fix"), "hub-purple")}
				${tile(`${t.bug_share_pct}%`, __("Bugs among new tickets"), "hub-cyan")}
				${tile(dash(t.density), __("Bugs per 100 hours"), "hub-teal")}
				${tile(`${t.reopen_rate}%`, __("Reopen rate"), t.reopen_rate > 15 ? "hub-red" : "hub-green", __("{0} reopened", [t.reopened]))}
			</div>
			<div class="hub-cols hub-cols-even">
				<div class="hub-col">
					${panel(`${__("Bugs opened vs fixed")} (${per})`, `<div class="hub-chart" id="q-flow"></div>`)}
					${panel(__("Time to fix by priority (days)"), d.fix_time.length ? d.fix_time.map((r) => bar(`${__(r.priority)} (${r.count})`, r.days, Math.max(...d.fix_time.map((x) => x.days)))).join("") : `<div class="text-muted small">${__("Nothing fixed in this range")}</div>`)}
					${panel(__("Bugs by category"), stack(d.by_category.map((r) => [r.label, r.open, r.closed]), [__("Open"), __("Fixed")], ["seg-orange", "seg-green"]))}
					${projects}
				</div>
				<div class="hub-col">
					${panel(`${__("Open bug backlog")} (${per})`, `<div class="hub-chart" id="q-trend"></div>`)}
					${panel(`${__("Bugs reopened")} (${per})`, `<div class="hub-chart" id="q-reopen"></div>`)}
					${panel(__("Open bugs by priority"), `<div class="hub-chart" id="q-priority"></div>`)}
					${panel(__("Age of open bugs"), `<div class="hub-chart" id="q-aging"></div>`)}
					${panel(__("Critical bugs still open"), critical)}
				</div>
			</div>`);
		this.$body.find("tr[data-project]").on("click", (e) => this.project_field.set_value($(e.currentTarget).data("project")));
		const p = ui.PALETTE;
		ui.chart(this.$body, "#q-flow", { type: "bar", data: { labels: d.labels, datasets: [{ name: __("Opened"), values: d.flow.opened }, { name: __("Fixed"), values: d.flow.fixed }] }, colors: [p.orange, p.green] });
		ui.chart(this.$body, "#q-trend", { type: "line", data: { labels: d.labels, datasets: [{ name: __("Open bugs"), values: d.flow.open_trend }] }, colors: [p.red], lineOptions: { regionFill: 1 } });
		ui.chart(this.$body, "#q-reopen", { type: "bar", height: 180, data: { labels: d.labels, datasets: [{ name: __("Reopened"), values: d.flow.reopened }] }, colors: [p.purple], barOptions: { spaceRatio: 0.5 } });
		ui.chart(this.$body, "#q-aging", { type: "bar", height: 200, data: { labels: d.aging.map((a) => a.label), datasets: [{ name: __("Open bugs"), values: d.aging.map((a) => a.count) }] }, colors: [p.orange], barOptions: { spaceRatio: 0.5 } });
		if (d.open_by_priority.length) ui.chart(this.$body, "#q-priority", { type: "donut", height: 200, data: { labels: d.open_by_priority.map((r) => __(r.label)), datasets: [{ values: d.open_by_priority.map((r) => r.count) }] }, colors: [p.red, p.orange, p.blue, p.green, p.purple] });
	}
}
