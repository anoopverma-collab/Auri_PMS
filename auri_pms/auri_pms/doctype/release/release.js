// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Release", {
	refresh(frm) {
		if (frm.is_new()) return;
		const colors = { Open: "green", Locked: "orange", Closed: "gray" };
		frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");
		// set_headline appends a block on every call and a new document refreshes more than once after its first save, so start clean.
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(
			auri_pms.ui.chips([
				frm.doc.due_date && `${__("Due")} ${auri_pms.ui.due(frm.doc.due_date, frm.doc.status === "Closed")}`,
				`${cint(frm.doc.closed_items)} / ${cint(frm.doc.total_items)} ${__("items closed")}`,
			])
		);
		frm.dashboard.show_progress(__("% Complete"), flt(frm.doc.percent_complete)); // updates in place on every refresh
		frm.add_custom_button(__("View tickets"), () => {
			frappe.route_options = { release: frm.doc.name };
			frappe.set_route("List", "Work Item", "List");
		});
		render_tickets(frm);
	},
});

function render_tickets(frm) {
	const $box = frm.fields_dict.tickets_html && frm.fields_dict.tickets_html.$wrapper;
	if (!$box) return;
	frappe.xcall("auri_pms.auri_pms.doctype.release.release.get_release_tickets", { release: frm.doc.name }).then((d) =>
		auri_pms.ui.ticketsPanel($box, d, __("No tickets are allocated to this release yet. Set the Release field on a Work Item."))
	);
}
