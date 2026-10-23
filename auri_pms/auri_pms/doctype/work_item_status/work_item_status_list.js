// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.listview_settings["Work Item Status"] = {
	add_fields: ["color", "is_active"],
	formatters: {
		status_name: (value, df, doc) => auri_pms.ui.dot(doc && doc.color, value),
	},
};
