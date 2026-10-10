// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Tracker tab UX on the ERPNext Project form. Rules are enforced on the server.
frappe.ui.form.on("Project", {
	setup(frm) {
		frm.set_query("parent_project", () => ({ filters: { name: ["!=", frm.doc.name] } }));
		frm.set_query("user", "tracker_members", () => ({ filters: { enabled: 1 } }));
		// enabled_trackers is a Table MultiSelect (no grid): the query goes on the field itself.
		frm.set_query("enabled_trackers", () => ({ filters: { is_active: 1 } }));
	},
	refresh(frm) {
		// The identifier is fixed once saved (set-only-once rule R-02).
		if (frm.doc.tracker_identifier && !frm.is_new()) {
			frm.set_df_property("tracker_identifier", "read_only", 1);
			frm.add_custom_button(__("Project Hub"), () => frappe.set_route("project-hub", frm.doc.name));
		}
	},
	tracker_identifier(frm) {
		if (frm.doc.tracker_identifier) {
			frm.set_value("tracker_identifier", frm.doc.tracker_identifier.toUpperCase().trim());
		}
	},
});
