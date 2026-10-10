// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Release", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.dashboard.add_progress(__("% Complete"), flt(frm.doc.percent_complete));
	},
});
