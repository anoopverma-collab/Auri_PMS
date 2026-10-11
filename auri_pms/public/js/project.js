// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Auri PMS tab UX on the ERPNext Project form. Rules are enforced on the server.
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
		}
		if (frm.doc.pms_enabled && !frm.is_new()) {
			frm.add_custom_button(__("Project Hub"), () => frappe.set_route("project-hub", frm.doc.name));
		}
	},
	pms_enabled(frm) {
		// Switching Auri PMS on selects every active Ticket Type by default (the server does the same on save).
		if (!frm.doc.pms_enabled || (frm.doc.enabled_trackers || []).length) return;
		frappe.db.get_list("Ticket Type", { filters: { is_active: 1 }, pluck: "name", limit: 0 }).then((names) => {
			names.forEach((name) => frm.add_child("enabled_trackers", { tracker: name }));
			frm.refresh_field("enabled_trackers");
		});
	},
	tracker_identifier(frm) {
		if (frm.doc.tracker_identifier) {
			frm.set_value("tracker_identifier", frm.doc.tracker_identifier.toUpperCase().trim());
		}
	},
});
