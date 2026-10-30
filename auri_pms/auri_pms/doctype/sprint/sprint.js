// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sprint", {
	setup(frm) {
		frm.set_query("project", () => ({ query: "auri_pms.auri_pms.api.project_link_query" }));
		frm.set_query("carry_over_to", () => ({
			filters: { project: frm.doc.project, status: ["in", ["Planned", "Active"]], name: ["!=", frm.doc.name || ""] },
		}));
	},

	refresh(frm) {
		if (frm.is_new()) return;
		const colors = { Planned: "blue", Active: "green", Completed: "gray" };
		frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");
		// set_headline appends a block on every call and a new document refreshes more than once after its first save, so start clean.
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(
			auri_pms.ui.chips([
				frm.doc.start_date && frm.doc.end_date &&
					`${frappe.datetime.str_to_user(frm.doc.start_date)} - ${frappe.datetime.str_to_user(frm.doc.end_date)}`,
				`${cint(frm.doc.closed_items)} / ${cint(frm.doc.total_items)} ${__("items closed")}`,
			])
		);
		frm.dashboard.show_progress(__("% Complete"), flt(frm.doc.percent_complete)); // updates in place on every refresh
		const completed = frm.doc.status === "Completed";
		if (frm.doc.status === "Planned") {
			frm.add_custom_button(__("Start Sprint"), () => sprint_set_status(frm, "Active")).addClass("btn-primary");
		}
		if (completed && frm.doc.__onload && cint(frm.doc.__onload.allow_reopen_sprint)) {
			frm.add_custom_button(__("Reopen Sprint"), () =>
				frappe.confirm(__("Reopen {0}? Tickets already carried over to another sprint stay there.", [frm.doc.name]), () => sprint_set_status(frm, "Active"))
			).addClass("btn-primary");
		}
		if (frm.doc.status === "Active") {
			frm.add_custom_button(__("Complete Sprint"), () => sprint_complete(frm)).addClass("btn-primary");
		}
		frm.add_custom_button(__("Sprint Board"), () => {
			// The Kanban view only takes filters from the URL query (route options keep the previous filters).
			window.location.assign(
				`/desk/work-item/view/kanban/Work%20Items%20by%20Status?sprint=${encodeURIComponent(frm.doc.name)}`
			);
		}, __("View"));
		frm.add_custom_button(__("Sprint Items"), () => {
			frappe.route_options = { sprint: frm.doc.name };
			frappe.set_route("List", "Work Item", "List");
		}, __("View"));
		if (frm.doc.status !== "Planned") {
			frm.add_custom_button(__("Burndown"), () => {
				frappe.route_options = { sprint: frm.doc.name };
				frappe.set_route("query-report", "Sprint Burndown");
			}, __("View"));
		}
		frm.set_df_property("carry_over_to", "hidden", completed ? 1 : 0);
		const $box = frm.fields_dict.tickets_html && frm.fields_dict.tickets_html.$wrapper;
		if ($box) {
			frappe.xcall("auri_pms.auri_pms.doctype.sprint.sprint.get_sprint_tickets", { sprint: frm.doc.name }).then((d) =>
				auri_pms.ui.ticketsPanel($box, d, __("No tickets are allocated to this sprint yet. Set the Sprint field on a Work Item."))
			);
		}
	},
});

function sprint_set_status(frm, status) {
	frm.set_value("status", status).then(() => frm.save());
}

function sprint_complete(frm) {
	frappe
		.xcall("frappe.client.get_count", { doctype: "Work Item", filters: { sprint: frm.doc.name, is_closed: 0 } })
		.then((open_items) => {
			const dialog = new frappe.ui.Dialog({
				title: __("Complete {0}", [frm.doc.name]),
				fields: [
					{
						fieldtype: "HTML",
						options: `<p>${__("{0} unfinished items will leave this sprint.", [open_items])}</p>`,
					},
					{
						fieldname: "carry_over_to",
						label: __("Move unfinished items to"),
						fieldtype: "Link",
						options: "Sprint",
						description: __("Leave blank to send them back to the backlog"),
						get_query: () => ({
							filters: { project: frm.doc.project, status: ["in", ["Planned", "Active"]], name: ["!=", frm.doc.name] },
						}),
					},
				],
				primary_action_label: __("Complete Sprint"),
				primary_action(values) {
					dialog.hide();
					frm.set_value("carry_over_to", values.carry_over_to || null)
						.then(() => frm.set_value("status", "Completed"))
						.then(() => frm.save());
				},
			});
			dialog.show();
		});
}
