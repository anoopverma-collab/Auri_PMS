// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Release", {
	refresh(frm) {
		if (frm.is_new()) return;
		const colors = { Open: "green", Locked: "orange", Closed: "gray" };
		frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");
		frm.dashboard.set_headline(
			auri_pms.ui.chips([
				frm.doc.due_date && `${__("Due")} ${auri_pms.ui.due(frm.doc.due_date, frm.doc.status === "Closed")}`,
				`${cint(frm.doc.closed_items)} / ${cint(frm.doc.total_items)} ${__("items closed")}`,
			])
		);
		frm.dashboard.add_progress(__("% Complete"), flt(frm.doc.percent_complete));
	},
});
