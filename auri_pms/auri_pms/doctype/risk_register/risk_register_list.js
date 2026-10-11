// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.listview_settings["Risk Register"] = {
	add_fields: ["status", "risk_level", "risk_score"],
	get_indicator(doc) {
		const colors = { Critical: "red", High: "orange", Medium: "yellow", Low: "green" };
		if (doc.status === "Closed") return [__("Closed"), "gray", "status,=,Closed"];
		return [`${__(doc.risk_level)} (${doc.risk_score})`, colors[doc.risk_level] || "gray", `risk_level,=,${doc.risk_level}`];
	},
};
