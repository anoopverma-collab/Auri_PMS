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
	tree: "M4 5h5M4 12h5M4 19h5M9 5v14M9 12h4M9 19h4M13 9h7M13 15h7",
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

	// A read-only tree: every node shows its counts, hours and progress; a count opens the matching tickets.
	tree_html(v) {
		const esc = ui.esc;
		const go = (route, html) => (route ? `<a class="ins-t-go" ${ui.goAttr(ui.go(route.doctype, route.filters))}>${html}</a>` : html);
		const num = (n) => `<span class="ins-t-n">${n}</span>`;
		const node = (n, level, top) => {
			const kids = (n.children || []).length;
			const late = flt(n.overdue) ? `<span class="ins-t-n ins-t-late">${go({ doctype: "Work Item", filters: { ...n.route.filters, is_closed: 0, due_date: ["<", frappe.datetime.get_today()] } }, n.overdue)}</span>` : num(0);
			const label = n.kind === "Status"
				? `<i class="ins-t-dot ${esc(n.tone || "gray")}"></i><span class="ins-t-name">${esc(n.label)}</span>`
				: `<span class="ins-t-kind ins-t-${n.kind.toLowerCase()}">${esc(__(n.kind))}</span><b class="ins-t-name">${esc(n.label)}</b>${n.meta ? `<span class="ins-t-meta">${esc(n.meta)}</span>` : ""}`;
			const pct = n.kind === "Status" ? "" : `<span class="ins-t-pct"><span class="ins-t-bar"><i style="width:${n.pct}%"></i></span><b>${n.pct}%</b></span>`;
			const row = `<div class="ins-t-row ins-t-${n.kind.toLowerCase()}-row" style="--lv:${level}"><i class="ins-t-chev ${kids ? "" : "ins-t-leaf"}"></i>${label}<span class="ins-t-grow"></span>${num(go(n.route, n.tickets))}${num(n.closed)}${late}${num(n.est)}${num(n.spent)}${pct || '<span class="ins-t-pct"></span>'}</div>`;
			return `<div class="ins-t-node ${top ? "open" : ""}">${row}${kids ? `<div class="ins-t-kids">${n.children.map((k) => node(k, level + 1, false)).join("")}</div>` : ""}</div>`;
		};
		const cols = [__("Tickets"), __("Closed"), __("Overdue"), __("Est. h"), __("Spent h")];
		return `<div class="ins-t-tools"><button class="btn btn-xs btn-default" data-tree="expand">${__("Expand all")}</button><button class="btn btn-xs btn-default" data-tree="collapse">${__("Collapse all")}</button></div>
			<div class="ins-tree"><div class="ins-t-head"><span>${__("Name")}</span><span class="ins-t-grow"></span>${cols.map((c) => `<span class="ins-t-n">${c}</span>`).join("")}<span class="ins-t-pct">${__("Progress")}</span></div>${v.tree.map((n) => node(n, 0, true)).join("")}</div>
			<div class="ins-t-note">${__("Click a count to open the matching tickets. Read-only: change tickets from the Work Item list.")}</div>`;
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
			else if (v.kind === "tree") body = this.tree_html(v);
			else if (v.kind === "stack") body = `<div id="${id}">${ui.stack(v.rows, v.names, v.tones.map((t) => `seg-${t}`))}</div>`;
			else if (v.kind === "table") {
				// a cell with its own route (cell_routes[row][col]) opens that list; otherwise the first cell opens the row's route
				const route_of = (k, i) => ((v.cell_routes || [])[k] || [])[i] || (i === 0 ? (v.row_routes || [])[k] : null);
				const go = (route, html) => (route ? `<a class="ins-t-go" ${ui.goAttr(goto(route))}>${html}</a>` : html);
				body = ui.table(v.rows, v.columns, (r, k) => `<tr>${r.map((cell, i) => {
					const route = route_of(k, i);
					if (route) return `<td>${go(route, esc(cell))}</td>`;
					return `<td>${i === 0 && v.doctype && v.kind === "table" && String(cell).match(/^[A-Z]+-/) ? ui.link(v.doctype, cell) : esc(cell)}</td>`;
				}).join("")}</tr>`);
			}
			return `<div class="hub-panel ph2-card ph2-in ins-v ins-span${v.span || 1}"><div class="ph2-card-head"><h6>${esc(v.title)}</h6></div>${body}</div>`;
		});
		this.$body.html(`<div class="ph2 ins">${this.nav()}${head}<div class="hub-tiles ins-kpis">${tiles}</div><div class="ins-grid">${cards.join("")}</div></div>`);
		// stack rows: each segment opens its own list (routes[row][segment]); the label and total open the whole row
		d.visuals.forEach((v, n) => {
			if (v.kind !== "stack") return;
			const set = ($el, route, cls) => {
				if (!route) return;
				$el.attr({ "data-go": JSON.stringify(goto(route)), tabindex: 0, role: "link" });
				if (cls) $el.addClass(cls);
			};
			this.$body.find(`#ins-v${n} .hub-stack`).each((k, row) => {
				const $row = $(row);
				const segments = (v.routes || [])[k] || [];
				$row.find("> div > i").each((s, seg) => set($(seg), segments[s]));
				const whole = (v.row_routes || [])[k];
				set($row.children("span").first(), whole, "ins-t-go");
				set($row.children("b").first(), whole, "ins-t-go");
			});
		});
		ui.bindTiles(this.$body);
		this.$body.find(".ins-t-row").on("click", (e) => {
			if ($(e.target).closest("[data-go]").length) return; // a count opens its tickets instead
			$(e.currentTarget).closest(".ins-t-node").toggleClass("open");
		});
		this.$body.find("[data-tree]").on("click", (e) => {
			const open = $(e.currentTarget).attr("data-tree") === "expand";
			this.$body.find(".ins-t-node:has(.ins-t-kids)").toggleClass("open", open);
		});
		d.visuals.forEach((v, n) => {
			if (!["line", "bar", "donut"].includes(v.kind) || !(v.labels && v.labels.length && has_values(v))) return;
			const colors = (v.colors || []).map((c) => p[c] || c);
			const config = v.kind === "donut"
				? { type: "donut", height: 250, data: { labels: v.labels, datasets: [{ values: v.values }] }, colors: [p.blue, p.purple, p.green, p.orange, p.cyan, p.pink, p.red, "#94a3b8"] }
				: { type: v.kind, height: v.span >= 2 ? 250 : 230, data: { labels: v.labels, datasets: v.datasets }, colors, axisOptions: { xIsSeries: 1 }, barOptions: { spaceRatio: 0.45 }, lineOptions: { regionFill: 1 } };
			// routes: donut = one per label; bar and line = one list per dataset, one route per label
			const route_of = (index, dataset) => (v.kind === "donut" ? (v.routes || [])[index] : ((v.routes || [])[dataset] || [])[index]);
			const pick = v.routes ? (index, dataset) => {
				const route = route_of(index, v.kind === "donut" ? 0 : dataset);
				if (route) ui.openTarget(goto(route));
			} : null;
			ui.chart(this.$body, `#ins-v${n}`, config, pick);
		});
	}
}
