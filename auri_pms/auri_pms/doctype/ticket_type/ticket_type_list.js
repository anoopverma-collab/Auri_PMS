// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.listview_settings["Ticket Type"] = {
	add_fields: ["color", "is_active"],
	formatters: {
		tracker_name: (value, df, doc) => auri_pms.ui.dot(doc && doc.color, value),
	},
};
