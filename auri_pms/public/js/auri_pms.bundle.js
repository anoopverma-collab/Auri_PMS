// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Loaded on every desk page so the custom Quick Entry exists before the first Work Item form is opened.
const WI_API = "auri_pms.auri_pms.api";

// Quick Entry: subject, project, tracker, priority, assigned_to, due_date (status is set by the server).
frappe.provide("frappe.ui.form");
frappe.ui.form.WorkItemQuickEntryForm = class WorkItemQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	set_meta_and_mandatory_fields() {
		super.set_meta_and_mandatory_fields();
		const order = ["subject", "project", "tracker", "priority", "assigned_to", "due_date"];
		const required = ["subject", "project", "tracker"];
		this.docfields = order
			.map((name) => this.meta.fields.find((df) => df.fieldname === name))
			.filter(Boolean)
			.map((df) => Object.assign({}, df, { reqd: required.includes(df.fieldname) ? 1 : df.reqd }));
	}

	render_dialog() {
		super.render_dialog();
		const get = (fieldname) => this.dialog.get_value(fieldname);
		const fields = this.dialog.fields_dict;
		fields.project.get_query = () => ({ query: `${WI_API}.project_create_query` });
		fields.tracker.get_query = () => ({ query: `${WI_API}.tracker_query`, filters: { project: get("project") } });
		fields.assigned_to.get_query = () => ({
			query: `${WI_API}.assignee_query`,
			filters: { project: get("project") },
		});
	}
};

// Small HTML helpers for the list and form look of Auri PMS doctypes (styles: public/css/auri_pms.bundle.css).
frappe.provide("auri_pms.ui");
Object.assign(auri_pms.ui, {
	// The "Tickets in this release / sprint" panel: totals, a pill per status and per person, then the tickets.
	ticketsPanel($box, d, empty_text) {
		const esc = frappe.utils.escape_html;
		if (!d.total) {
			$box.html(`<div class="text-muted">${esc(empty_text)}</div>`);
			return;
		}
		const chips = Object.entries(d.statuses).map(([s, n]) => `<span class="indicator-pill gray">${esc(__(s))}: ${n}</span>`).join(" ");
		const people = d.open_by_person.map((p) => `<span class="indicator-pill blue">${esc(p.name)}: ${p.open}</span>`).join(" ");
		const hours = d.rows.reduce((t, r) => [t[0] + flt(r.estimated_hours), t[1] + flt(r.spent_hours)], [0, 0]);
		const col = (rows, key) => rows.some((r) => r[key]);
		$box.html(`<div style="margin-bottom:10px"><b>${d.total}</b> ${__("tickets")} · <b>${d.closed}</b> ${__("closed")} · <b>${d.total - d.closed}</b> ${__("open")} · ${flt(hours[0], 1)} h ${__("estimated")} · ${flt(hours[1], 1)} h ${__("spent")}</div>
			<div style="margin-bottom:8px">${chips}</div>${people ? `<div style="margin-bottom:12px"><span class="text-muted">${__("Open per person")}:</span> ${people}</div>` : ""}
			<table class="table table-sm"><thead><tr><th>${__("Ticket")}</th><th>${__("Summary")}</th><th>${__("Status")}</th><th>${__("Owner")}</th><th>${__("Release")}</th><th>${__("Sprint")}</th><th>${__("Due")}</th><th class="text-right">${__("% Done")}</th></tr></thead><tbody>
			${d.rows.map((r) => `<tr><td><a href="/desk/work-item/${encodeURIComponent(r.name)}">${esc(r.name)}</a></td><td>${esc(r.subject)}</td><td>${esc(__(r.status))}</td><td>${esc(r.assignee)}</td><td>${esc((r.release || "").replace(/^.*?-(?=[^-]+$)/, ""))}</td><td>${esc((r.sprint || "").replace(/^.*?-(?=[^-]+$)/, ""))}</td><td>${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}</td><td class="text-right">${flt(r.done_percent, 0)}%</td></tr>`).join("")}
			</tbody></table>`);
	},

	priority(value) {
		if (!value) return "";
		return `<span class="auri-priority auri-priority-${frappe.utils.escape_html(value)}">${__(value)}</span>`;
	},
	// Date cell: red when overdue, orange when due within 3 days; nothing special once the item is closed.
	due(date, closed) {
		if (!date) return `<span class="auri-muted">-</span>`;
		const text = frappe.datetime.str_to_user(date);
		if (cint(closed)) return `<span class="auri-muted">${text}</span>`;
		const days = frappe.datetime.get_diff(date, frappe.datetime.get_today());
		const css = days < 0 ? "auri-due-overdue" : days <= 3 ? "auri-due-soon" : "";
		return `<span class="${css}" title="${days < 0 ? __("{0} days overdue", [-days]) : __("Due in {0} days", [days])}">${text}</span>`;
	},
	progress(percent) {
		const value = Math.max(0, Math.min(100, flt(percent)));
		return `<span class="auri-progress"><span class="auri-progress-track"><span class="auri-progress-fill" style="width:${value}%"></span></span><span class="auri-progress-label">${Math.round(value)}%</span></span>`;
	},
	dot(color, label) {
		return `<span class="auri-dot" style="${color ? `background:${frappe.utils.escape_html(color)}` : ""}"></span>${frappe.utils.escape_html(label || "")}`;
	},
	// Query report cells: priority pill, red/orange day counts. Anything else keeps Frappe's own formatting.
	reportCell(value, row, column, data, default_formatter) {
		const plain = default_formatter(value, row, column, data);
		if (!data || value === null || value === undefined || value === "") return plain;
		const field = column.fieldname;
		if (field === "priority") return auri_pms.ui.priority(value);
		if (field === "days_overdue" || field === "days_waiting") {
			const css = flt(value) > 7 ? "auri-due-overdue" : flt(value) > 0 ? "auri-due-soon" : "";
			return `<span class="${css}">${plain}</span>`;
		}
		if (field === "days_left") {
			const css = flt(value) < 0 ? "auri-due-overdue" : flt(value) <= 3 ? "auri-due-soon" : "";
			return `<span class="${css}">${plain}</span>`;
		}
		if (field === "overdue" && flt(value) > 0) return `<span class="auri-due-overdue">${plain}</span>`;
		if (field === "unassigned" && flt(value) > 0) return `<span class="auri-due-soon">${plain}</span>`;
		return plain;
	},
	chips(items) {
		return `<div class="auri-chips">${items.filter(Boolean).map((html) => `<span class="auri-chip">${html}</span>`).join("")}</div>`;
	},
});

// One rule for every New button: the server sends {doctype: may create} at login (CREATE_RULES) and Frappe asks
// frappe.model.can_create before it shows a New button, a menu shortcut or opens a new form.
if (frappe.model && frappe.model.can_create && !frappe.model._auri_pms_can_create) {
	const can_create = frappe.model.can_create;
	frappe.model._auri_pms_can_create = true;
	frappe.model.can_create = function (doctype) {
		const rules = (frappe.boot && frappe.boot.auri_pms_can_create) || {};
		return can_create.call(this, doctype) && rules[doctype] !== false;
	};
}

// A Project dropdown on an Auri PMS list or form (a list filter, say) that has no query of its own uses the Auri PMS project query:
// Frappe's own Project search would also apply a Company User Permission and hide a project the person belongs to.
if (frappe.ui && frappe.ui.form && frappe.ui.form.ControlLink && !frappe.ui.form.ControlLink.prototype._auri_pms_project_query) {
	const set_custom_query = frappe.ui.form.ControlLink.prototype.set_custom_query;
	frappe.ui.form.ControlLink.prototype._auri_pms_project_query = true;
	frappe.ui.form.ControlLink.prototype.set_custom_query = function (args) {
		set_custom_query.call(this, args);
		if (args.doctype !== "Project" || args.query) return;
		const route = frappe.get_route() || [];
		const own = (frappe.boot && frappe.boot.auri_pms_can_create) || {};
		if (["List", "Form", "Report"].includes(route[0]) && route[1] in own) {
			args.query = "auri_pms.auri_pms.api.project_link_query";
		}
	};
}

// Delivery & Health is for Auri PMS Admins and the members of a project (boot flag); hide its sidebar link from everyone else.
if (frappe.boot && frappe.boot.user && frappe.boot.user.name !== "Guest" && !frappe.boot.auri_pms_portfolio) {
	const style = document.createElement("style");
	style.textContent = '.standard-sidebar-item:has(> a[href="/desk/management-dashboard"]) { display: none !important; }';
	document.head.appendChild(style);
}

// Frappe builds an extra sidebar for every module and the module used to be called "Tracking", so old browsers may remember "Tracking" (or the
// old name "Tracker") in the top-left corner instead of "Auri PMS". Drop that generated sidebar, repair any remembered choice
// that points at it, and switch back whenever one of the two names is shown.
const STALE_SIDEBARS = ["Tracker", "Tracking"];
try {
	if (frappe.boot && frappe.boot.workspace_sidebar_item) delete frappe.boot.workspace_sidebar_item.tracking;
	const remembered = localStorage.getItem("sidebar_item_map");
	if (remembered && STALE_SIDEBARS.some((name) => remembered.includes(`"${name}"`))) {
		localStorage.setItem("sidebar_item_map", remembered.replace(/"(Tracker|Tracking)"/g, '"Auri PMS"'));
	}
} catch (e) {
	/* storage or boot data unavailable: nothing to repair then */
}

// Frappe remembers a sidebar per screen in localStorage and keeps the sidebar that was open before, so after visiting another app
// (for example ERPNext's Projects) our screens could show that app's sidebar until a hard refresh. Our own screens (the dashboards
// and every screen that only the Auri PMS sidebar links to) therefore always switch to the Auri PMS sidebar.
const PMS_PAGES = ["project-hub", "portfolio", "management-dashboard", "pms-insights", "my-work", "quality-dashboard", "status-report"];
const is_pms_screen = (sidebar) => {
	const route = frappe.get_route() || [];
	if (PMS_PAGES.includes(route[0])) return true;
	if (!sidebar.all_sidebar_items) return false;
	const owners = sidebar.get_workspace_sidebars(sidebar.entity_from_route(route));
	return owners.length > 0 && owners.every((name) => name === "Auri PMS");
};
const keep_pms_sidebar = () => {
	try {
		const sidebar = frappe.app && frappe.app.sidebar;
		if (!sidebar) return;
		if (STALE_SIDEBARS.includes(sidebar.sidebar_title) || (sidebar.sidebar_title !== "Auri PMS" && is_pms_screen(sidebar))) {
			sidebar.setup("Auri PMS");
		}
	} catch (e) {
		/* the sidebar is a convenience: never break the page for it */
	}
};
$(document).on("startup", () => {
	if (frappe.router && frappe.router.on) frappe.router.on("change", () => setTimeout(keep_pms_sidebar, 80));
	$(document).on("page-change", () => setTimeout(keep_pms_sidebar, 80));
	setTimeout(keep_pms_sidebar, 300);
});

// Searching "Auri PMS", "PMS" or "Project Hub" in the Awesome Bar offers the Project Hub, the landing screen of the app.
$(document).on("startup", () => {
	const search = frappe.search && frappe.search.utils;
	if (search && search.make_function_searchable) {
		const open_hub = () => frappe.set_route("project-hub");
		search.make_function_searchable(open_hub, __("PMS"));
		search.make_function_searchable(open_hub, __("Open Project Hub"));
		search.make_function_searchable(open_hub, __("Auri PMS"));
		search.make_function_searchable(open_hub, __("Auri PMS Project Hub"));
	}
});
