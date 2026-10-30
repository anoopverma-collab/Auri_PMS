// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work Item Category", {
	setup(frm) {
		frm.set_query("project", () => ({ query: "auri_pms.auri_pms.api.project_link_query" }));
	},
});
