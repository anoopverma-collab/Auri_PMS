// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

const RISK_COLORS = { Critical: "red", High: "orange", Medium: "yellow", Low: "green" };

frappe.ui.form.on("Risk Register", {
	refresh(frm) {
		if (frm.is_new()) return;
		const level = frm.doc.risk_level;
		if (level) frm.dashboard.set_headline(`<span class="indicator-pill ${RISK_COLORS[level] || "gray"}">${__(level)} · ${__("score")} ${frm.doc.risk_score}</span>`);
		frm.add_custom_button(__("Project Health"), () => frappe.set_route("project-hub", frm.doc.project, "health"), __("View"));
	},
	probability: (frm) => frm.trigger("preview_score"),
	impact: (frm) => frm.trigger("preview_score"),
	preview_score(frm) {
		const value = (s) => cint((s || "0").split(" ")[0]);
		const score = value(frm.doc.probability) * value(frm.doc.impact);
		frm.set_value("risk_score", score);
		frm.set_value("risk_level", score >= 15 ? "Critical" : score >= 10 ? "High" : score >= 5 ? "Medium" : score ? "Low" : "");
	},
});
