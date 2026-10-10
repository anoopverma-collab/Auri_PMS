// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

frappe.ui.form.on("Time Entry", {
	setup(frm) {
		frm.set_query("work_item", () => ({
			filters: frm.doc.project ? { project: frm.doc.project } : {},
		}));
	},
	refresh(frm) {
		// Project is derived from the work item; it is only editable without one.
		frm.set_df_property("project", "read_only", frm.doc.work_item ? 1 : 0);
		if (frm.is_new() && !frm.doc.user) frm.set_value("user", frappe.session.user);
	},
	work_item(frm) {
		frm.set_df_property("project", "read_only", frm.doc.work_item ? 1 : 0);
		if (!frm.doc.work_item) return;
		frappe.db.get_value("Work Item", frm.doc.work_item, ["project", "release"]).then((r) => {
			if (r.message) {
				frm.set_value("project", r.message.project);
				frm.set_value("release", r.message.release);
			}
		});
	},
});
