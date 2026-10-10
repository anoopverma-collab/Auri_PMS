// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.listview_settings["Sprint"] = {
	add_fields: ["status", "start_date", "end_date", "percent_complete"],
	get_indicator(doc) {
		const colors = { Planned: "blue", Active: "green", Completed: "gray" };
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
