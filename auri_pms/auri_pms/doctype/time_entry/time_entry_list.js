// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.listview_settings["Time Entry"] = {
	add_fields: ["date", "user", "project", "work_item", "hours", "activity_type", "is_billable"],
	get_indicator(doc) {
		return cint(doc.is_billable)
			? [__("Billable"), "green", "is_billable,=,1"]
			: [__("Non-billable"), "gray", "is_billable,=,0"];
	},
	formatters: {
		hours: (value) => `<span class="text-right">${flt(value, 2)} ${__("h")}</span>`,
	},
};
