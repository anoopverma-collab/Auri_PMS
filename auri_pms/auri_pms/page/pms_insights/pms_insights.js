// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

/* global auri_pms */
// Insights: a gallery of ready-made analytical dashboards (delivery, workload, releases, quality, client, time) on Auri PMS data.
const INSIGHTS_API = "auri_pms.auri_pms.insights";
let ui; // shared UI kit (auri_hub.bundle.js)

frappe.pages["pms-insights"].on_page_load = function (wrapper) {
	frappe.require("auri_hub.bundle.js", () => {
		ui = auri_pms.ui;
		wrapper.insights = new Insights(wrapper);
		wrapper.insights.show(frappe.get_route()[1]);
	});
};

frappe.pages["pms-insights"].on_page_show = function (wrapper) {
	if (wrapper.insights) wrapper.insights.show(frappe.get_route()[1]);
};

const ICONS = {
	truck: "M3 7h11v9H3zM14 10h4l3 3v3h-7zM7 19a1.5 1.5 0 100-3 1.5 1.5 0 000 3zM17 19a1.5 1.5 0 100-3 1.5 1.5 0 000 3z",
	users: "M9 11a3 3 0 100-6 3 3 0 000 6zM3 19c0-3 3-5 6-5s6 2 6 5M17 11a2.5 2.5 0 100-5M18 14c2 .5 3 2 3 5",
	package: "M12 3l8 4v10l-8 4-8-4V7zM4 7l8 4 8-4M12 11v10",
	bug: "M9 8a3 3 0 016 0v1H9zM7 11h10v4a5 5 0 01-10 0zM3 12h4M17 12h4M4 18l3-2M20 18l-3-2",
	clock: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2",
	timer: "M10 3h4M12 7v6l3 2M12 21a8 8 0 100-16 8 8 0 000 16z",
};
const icon = (name) => `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="${ICONS[name] || ICONS.package}"/></svg>`;

// a chart with nothing but zeros is an empty state, not a flat chart
const has_values = (v) => (v.datasets ? v.datasets.some((d) => (d.values || []).some((x) => flt(x))) : (v.values || []).some((x) => flt(x)));

class Insights {
	constructor(wrapper) {
		const { page, $body } = ui.initPage(wrapper, "Auri Insights");
		this.page = page;
		this.$body = $body;
		this.project_names = [];
		// only the Auri PMS projects the person is allocated to (all of them for an admin) are offered
		this.project_field = page.add_field({
			fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", change: () => this.show(this.report),
			get_query: () => ({ query: "auri_pms.auri_pms.api.project_link_query", filters: { name: ["in", this.project_names.length ? this.project_names : [""]] } }),
		});
	}

	show(report) {
		this.report = report || "";
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		if (!frappe.boot.auri_pms_insights) {
			// Project Role > Can See Auri Insights
			this.$body.html(`<div class="hub-panel p-4"><h6>${__("Auri Insights")}</h6><div class="text-muted">${__("Auri Insights is for Auri PMS Admins and for members whose Project Role can see it.")}</div></div>`);
			return;
		}
		ui.applyTheme(this.$body);
		ui.addPeriodMenu(this.page, () => this.show(this.report));
		ui.addThemeMenu(this.page, () => this.show(this.report));
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub"));
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		frappe.xcall(`${INSIGHTS_API}.get_insight_projects`).then((names) => (this.project_names = names));
		frappe.xcall(`${INSIGHTS_API}.get_reports`).then((reports) => {
			this.reports = reports;
			if (!this.report || !reports.some((r) => r.key === this.report)) return this.gallery();
			this.load(this.report);
		});
	}

	nav() {
		const base = window.location.pathname.split("/pms-insights")[0] + "/pms-insights";
		return `<nav class="pt-tabs ins-nav"><a class="pt-tab ${this.report ? "" : "pt-on"}" href="${base}">${__("All dashboards")}</a>
			${this.reports.map((r) => `<a class="pt-tab ${this.report === r.key ? "pt-on" : ""}" href="${base}/${r.key}">${r.title}</a>`).join("")}</nav>`;
	}

	gallery() {
		const base = window.location.pathname.split("/pms-insights")[0] + "/pms-insights";
		this.$body.html(`<div class="ph2 ins">${this.nav()}
			<div class="ins-hero"><h3>${__("Auri Insights")}</h3><p>${__("Ready-made dashboards on your Auri PMS data. Pick a project above to focus on one, or leave it empty to see every project you can access.")}</p></div>
			<div class="ins-gallery">${this.reports.map((r) => `<a class="ins-card" href="${base}/${r.key}"><span class="ins-ico">${icon(r.icon)}</span><b>${r.title}</b><p>${r.about}</p><em>${__("Open dashboard")} →</em></a>`).join("")}</div></div>`);
	}

	load(report) {
		const project = this.project_field.get_value() || "";
		frappe.xcall(`${INSIGHTS_API}.get_insight`, { report, project, period: ui.getPeriod() }).then((d) => {
			this.data = d;
			this.draw(d);
		});
	}

	draw(d) {
		const esc = ui.esc;
		const p = ui.PALETTE;
		const goto = (r) => (r ? ui.go(r.doctype, r.filters) : null);
		const head = `<div class="hub-title ins-title"><h4>${esc(d.title)}</h4><span class="text-muted">${esc(d.subtitle)}</span></div>`;
		if (d.note) {
			this.$body.html(`<div class="ph2 ins">${this.nav()}${head}<div class="hub-panel ph2-card"><div class="ph2-empty">${esc(d.note)}</div></div></div>`);
			return;
		}
		const tiles = d.kpis.map((k) => ui.tile(esc(k.value), esc(k.label), `hub-${k.tone}`, esc(k.sub || ""), goto(k.route))).join("");
		const cards = d.visuals.map((v, n) => {
			const id = `ins-v${n}`;
			let body = "";
			if (["line", "bar", "donut"].includes(v.kind)) body = v.labels && v.labels.length && has_values(v) ? `<div class="hub-chart" id="${id}"></div>` : `<div class="ph2-empty">${__("Nothing yet")}</div>`;
			else if (v.kind === "stack") body = ui.stack(v.rows, v.names, v.tones.map((t) => `seg-${t}`));
			else if (v.kind === "table") {
				body = ui.table(v.rows, v.columns, (r) => `<tr>${r.map((cell, i) => `<td>${i === 0 && v.doctype && v.kind === "table" && String(cell).match(/^[A-Z]+-/) ? ui.link(v.doctype, cell) : esc(cell)}</td>`).join("")}</tr>`);
			}
			return `<div class="hub-panel ph2-card ph2-in ins-v ins-span${v.span || 1}"><div class="ph2-card-head"><h6>${esc(v.title)}</h6></div>${body}</div>`;
		});
		this.$body.html(`<div class="ph2 ins">${this.nav()}${head}<div class="hub-tiles ins-kpis">${tiles}</div><div class="ins-grid">${cards.join("")}</div></div>`);
		ui.bindTiles(this.$body);
		d.visuals.forEach((v, n) => {
			if (!["line", "bar", "donut"].includes(v.kind) || !(v.labels && v.labels.length && has_values(v))) return;
			const colors = (v.colors || []).map((c) => p[c] || c);
			const config = v.kind === "donut"
				? { type: "donut", height: 250, data: { labels: v.labels, datasets: [{ values: v.values }] }, colors: [p.blue, p.purple, p.green, p.orange, p.cyan, p.pink, p.red, "#94a3b8"] }
				: { type: v.kind, height: v.span >= 2 ? 250 : 230, data: { labels: v.labels, datasets: v.datasets }, colors, axisOptions: { xIsSeries: 1 }, barOptions: { spaceRatio: 0.45 }, lineOptions: { regionFill: 1 } };
			ui.chart(this.$body, `#ins-v${n}`, config);
		});
	}
}
