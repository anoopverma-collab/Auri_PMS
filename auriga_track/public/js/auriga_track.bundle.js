// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

// Loaded on every desk page so the custom Quick Entry exists before the first Work Item form is opened.
const WI_API = "auriga_track.tracking.api";

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

// Searching "tracker" in the Awesome Bar offers the Project Hub, the landing screen of the app.
$(document).on("startup", () => {
	const search = frappe.search && frappe.search.utils;
	if (search && search.make_function_searchable) {
		const open_hub = () => frappe.set_route("project-hub");
		search.make_function_searchable(open_hub, __("Tracker"));
		search.make_function_searchable(open_hub, __("Tracker Project Hub"));
	}
});
