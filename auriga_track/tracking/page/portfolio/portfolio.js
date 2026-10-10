// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

/* global auriga_track */
// Portfolio: health, delivery and effort of every project the user can see, on one screen.
let ui; // shared UI kit (auriga_hub.bundle.js)

frappe.pages["portfolio"].on_page_load = function (wrapper) {
	frappe.require("auriga_hub.bundle.js", () => {
		ui = auriga_track.ui;
		wrapper.portfolio = new Portfolio(wrapper);
		wrapper.portfolio.load();
	});
};

frappe.pages["portfolio"].on_page_show = function (wrapper) {
	if (wrapper.portfolio) wrapper.portfolio.load();
};

class Portfolio {
	constructor(wrapper) {
		const { page, $body } = ui.initPage(wrapper, "Portfolio");
		this.page = page;
		this.$body = $body;
		this.filter = "all";
		this.query = "";
		this.sort = { key: "level", asc: true };
	}

	load() {
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		ui.applyTheme(this.$body);
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub"));
		this.page.add_inner_button(__("Refresh"), () => this.load());
		ui.addPeriodMenu(this.page, () => this.load());
		ui.addThemeMenu(this.page, () => this.load());
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		frappe.xcall("auriga_track.tracking.api.get_portfolio", { period: ui.getPeriod() }).then((data) => {
			this.data = data;
			this.render();
		});
	}

	render() {
		const d = this.data;
		const k = d.kpis;
		const { tile, panel, stack, bar } = ui;
		const burn_text = k.burn_pct === null ? "-" : `${k.burn_pct}%`;
		this.$body.html(`
			<div class="hub-title"><h4>${__("Portfolio")}</h4>
				<span class="text-muted">${__("{0} projects", [k.projects])} · ${__(ui.PERIOD_NOTE[d.period])} · ${frappe.datetime.str_to_user(frappe.datetime.get_today())}</span></div>
			<div class="hub-tiles">
				${tile(k.projects, __("Projects"), "hub-blue", `${k.red} ${__("off track")} · ${k.amber} ${__("at risk")} · ${k.green} ${__("on track")}`)}
				${tile(k.red, __("Off track"), "hub-red", "", "red")}
				${tile(k.open, __("Open tickets"), "hub-purple", `${k.closed} ${__("closed")}`)}
				${tile(k.overdue, __("Overdue"), k.overdue ? "hub-orange" : "hub-teal")}
				${tile(k.client_dependent, __("Waiting on client"), "hub-cyan")}
				${tile(k.hours_period, __("Hours in range"), "hub-teal", `${k.hours_spent} ${__("h in total")}`)}
				${tile(`${k.billable_pct}%`, __("Billable"), "hub-green")}
				${tile(burn_text, __("Budget burn"), k.burn_pct > 100 ? "hub-red" : "hub-blue", __("hours spent / estimated"))}
			</div>
			<div class="hub-panel"><h6>${__("Projects")}</h6>
				<div class="hub-toolbar"><div class="hub-search"><input type="text" class="form-control" placeholder="${__("Search projects")}" value="${ui.esc(this.query)}"></div></div>
				<div class="hub-chips">${[["all", __("All")], ["red", __("Off track")], ["amber", __("At risk")], ["green", __("On track")]]
					.map(([key, text]) => `<span class="hub-chip ${this.filter === key ? "active" : ""}" data-filter="${key}">${text}</span>`)
					.join("")}</div>
				<div class="hub-projects" style="overflow-x:auto"></div></div>
			<div class="hub-cols hub-cols-even">
				<div class="hub-col">
					${panel(__("Health mix"), `<div class="hub-chart" id="pf-mix"></div>`)}
					${panel(__("Open and closed tickets by project"), stack(d.projects.slice(0, 12).map((p) => [p.project_name, p.open, p.closed]), [__("Open"), __("Closed")], ["seg-blue", "seg-green"]))}
					${panel(__("Budget burn by project (% of estimate)"), d.projects.filter((p) => p.burn_pct !== null).map((p) => bar(p.project_name, p.burn_pct, Math.max(100, ...d.projects.map((x) => x.burn_pct || 0)), p.burn_pct > 100 ? "seg-orange" : "")).join("") || `<div class="text-muted small">${__("No estimates yet")}</div>`)}
				</div>
				<div class="hub-col">
					${panel(`${__("Tickets created vs resolved")} (${d.bucket === "month" ? __("monthly") : __("weekly")})`, `<div class="hub-chart" id="pf-flow"></div>`)}
					${panel(__("Hours: billable vs non-billable"), `<div class="hub-chart" id="pf-time"></div>`)}
				</div>
			</div>`);
		this.$body.find(".hub-tile[data-route='red']").on("click", () => this.set_filter("red"));
		this.$body.find(".hub-search input").on("input", (e) => {
			this.query = $(e.target).val();
			this.render_table();
		});
		this.$body.find(".hub-chip").on("click", (e) => this.set_filter($(e.currentTarget).data("filter")));
		this.render_table();
		const palette = ui.PALETTE;
		ui.chart(this.$body, "#pf-mix", { type: "donut", height: 200, data: { labels: [__("Off track"), __("At risk"), __("On track"), __("No data")], datasets: [{ values: [k.red, k.amber, k.green, k.none] }] }, colors: [palette.red, palette.orange, palette.green, "#9ca3af"] });
		ui.chart(this.$body, "#pf-flow", { type: "bar", data: { labels: d.labels, datasets: [{ name: __("Created"), values: d.series.created }, { name: __("Resolved"), values: d.series.resolved }] }, colors: [palette.blue, palette.green] });
		ui.chart(this.$body, "#pf-time", { type: "bar", data: { labels: d.labels, datasets: [{ name: __("Billable"), values: d.series.billable }, { name: __("Non-billable"), values: d.series.non_billable }] }, colors: [palette.green, palette.orange], barOptions: { stacked: 1 } });
	}

	set_filter(key) {
		this.filter = key;
		this.$body.find(".hub-chip").each((_i, el) => $(el).toggleClass("active", $(el).data("filter") === key));
		this.render_table();
	}

	render_table() {
		const q = this.query.toLowerCase();
		const order = { red: 0, amber: 1, green: 2, none: 3 };
		let rows = this.data.projects.filter(
			(p) => (this.filter === "all" || p.level === this.filter) && `${p.project_name} ${p.identifier}`.toLowerCase().includes(q)
		);
		const { key, asc } = this.sort;
		const value = (p) => (key === "level" ? [order[p.level], p.score === null ? 101 : p.score] : key === "project_name" ? p.project_name.toLowerCase() : flt(p[key]));
		rows = rows.sort((a, b) => {
			const x = value(a);
			const y = value(b);
			const cmp = Array.isArray(x) ? x[0] - y[0] || x[1] - y[1] : x < y ? -1 : x > y ? 1 : 0;
			return asc ? cmp : -cmp;
		});
		const cols = [["project_name", __("Project")], ["level", __("Health")], ["open", __("Open"), 1], ["overdue_pct", __("Overdue %"), 1], ["completion_pct", __("Done %"), 1], ["burn_pct", __("Burn %"), 1], ["billable_pct", __("Billable %"), 1], ["client_dependent", __("Client"), 1], ["hours_period", __("Hours"), 1]];
		const head = cols.map(([k, label, num]) => `<th class="${num ? "num" : ""} ${key === k ? `sorted ${asc ? "asc" : ""}` : ""}" data-key="${k}">${label}</th>`).join("");
		const dash = (v, suffix) => (v === null || v === undefined ? "-" : `${v}${suffix || ""}`);
		const body = rows.length
			? rows
					.map(
						(p) => `<tr class="hub-clickrow" data-project="${ui.esc(p.name)}">
						<td><b>${ui.esc(p.project_name)}</b> <span class="hub-sub">${ui.esc(p.identifier)}</span>${p.sprint ? `<div class="hub-sub">${ui.esc(p.sprint.label)} · ${flt(p.sprint.percent, 0)}%</div>` : ""}</td>
						<td title="${ui.esc(p.headline)}"><span class="hub-dot ${p.level}"></span>${ui.esc(p.label)}${p.score === null ? "" : ` <span class="hub-sub">${p.score}</span>`}</td>
						<td class="num">${p.open}</td><td class="num">${p.overdue_pct}%</td><td class="num">${p.completion_pct}%</td>
						<td class="num ${p.burn_pct > 100 ? "text-danger" : ""}">${dash(p.burn_pct, "%")}</td><td class="num">${p.billable_pct}%</td>
						<td class="num">${p.client_dependent || "-"}</td><td class="num">${p.hours_period}</td></tr>`
					)
					.join("")
			: `<tr><td colspan="9" class="text-muted">${__("No projects match.")}</td></tr>`;
		const $box = this.$body.find(".hub-projects").html(`<table class="table table-sm hub-table sortable"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`);
		$box.find("th").on("click", (e) => {
			const k = $(e.currentTarget).data("key");
			this.sort = { key: k, asc: this.sort.key === k ? !this.sort.asc : k === "project_name" || k === "level" };
			this.render_table();
		});
		$box.find("tr[data-project]").on("click", (e) => frappe.set_route("project-hub", $(e.currentTarget).data("project"), "health"));
	}
}
