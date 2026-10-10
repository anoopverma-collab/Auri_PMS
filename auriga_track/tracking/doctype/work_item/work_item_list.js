// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

// Plain Tracker Users start on their open items; Frappe applies `filters` only when the user has no saved filters.
const wi_is_plain_user =
	frappe.user.has_role("Tracker User") &&
	!frappe.user.has_role("Tracker Manager") &&
	!frappe.user.has_role("System Manager");

frappe.listview_settings["Work Item"] = {
	add_fields: ["status", "priority", "assigned_to", "due_date", "is_closed", "project"],
	filters: wi_is_plain_user ? [["is_closed", "=", 0]] : [],

	get_indicator(doc) {
		const colors = frappe.work_item_colors || {};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},

	onload(listview) {
		// Indicator colours come from the server (Work Item Status colour); refresh once they are known.
		frappe.xcall("auriga_track.tracking.api.get_status_indicators").then((colors) => {
			frappe.work_item_colors = colors;
			listview.refresh();
		});
	},
};
