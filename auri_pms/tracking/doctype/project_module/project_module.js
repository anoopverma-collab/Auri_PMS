// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project Module", {
	refresh(frm) {
		frm.set_query("module_lead", () => ({ query: "auri_pms.tracking.api.assignee_query", filters: { project: frm.doc.project } }));
	},
});
