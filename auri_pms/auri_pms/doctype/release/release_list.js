// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.listview_settings["Release"] = {
	add_fields: ["status", "due_date", "percent_complete"],
	get_indicator(doc) {
		const colors = { Open: "green", Locked: "orange", Closed: "gray" };
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
	formatters: {
		percent_complete: (value) => auri_pms.ui.progress(value),
		due_date: (value, df, doc) => auri_pms.ui.due(value, doc && doc.status === "Closed"),
	},
};
