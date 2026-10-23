// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.listview_settings["Work Item Status"] = {
	add_fields: ["color", "is_active"],
	formatters: {
		color: (value) => (value ? auri_pms.ui.dot(value, value) : ""),
	},
};
