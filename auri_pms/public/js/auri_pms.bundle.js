// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Loaded on every desk page so the custom Quick Entry exists before the first Work Item form is opened.
const WI_API = "auri_pms.tracking.api";

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

// Frappe builds an extra sidebar for every module and our module is called "Tracking", so a screen could show "Tracking" (or the
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

const keep_pms_sidebar = () => {
	const sidebar = frappe.app && frappe.app.sidebar;
	if (sidebar && STALE_SIDEBARS.includes(sidebar.sidebar_title)) sidebar.setup("Auri PMS");
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
