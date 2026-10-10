// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Plain Tracker Users start on their open items; Frappe applies `filters` only when the user has no saved filters.
const wi_is_plain_user =
	frappe.user.has_role("Tracker User") &&
	!frappe.user.has_role("Tracker Manager") &&
	!frappe.user.has_role("System Manager");

frappe.listview_settings["Work Item"] = {
	add_fields: ["status", "priority", "assigned_to", "due_date", "is_closed", "project"],
	filters: wi_is_plain_user ? [["is_closed", "=", 0]] : [],

	get_indicator(doc) {
		const colors = frappe.work_item_colors || {};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},

	onload(listview) {
		listview.page.add_actions_menu_item(__("Move to Sprint"), () => wi_move_to_sprint(listview, false), false);
		listview.page.add_actions_menu_item(__("Move to Backlog"), () => wi_move_to_sprint(listview, true), false);
		// Indicator colours come from the server (Work Item Status colour); refresh once they are known.
		frappe.xcall("auriga_track.tracking.api.get_status_indicators").then((colors) => {
			frappe.work_item_colors = colors;
			listview.refresh();
		});
	},
};

// Bulk planning: move the ticked work items (of one project) into a sprint, or back to the backlog.
function wi_move_to_sprint(listview, to_backlog) {
	const checked = listview.get_checked_items();
	const projects = [...new Set(checked.map((d) => d.project))];
	if (!checked.length) return frappe.msgprint(__("Select at least one work item"));
	if (projects.length > 1) return frappe.msgprint(__("Select work items of a single project"));
	const run = (sprint) =>
		frappe
			.xcall("auriga_track.tracking.api.move_to_sprint", {
				work_items: checked.map((d) => d.name),
				sprint: sprint || null,
			})
			.then((result) => {
				const failed = result.failed.map((f) => `${f.name}: ${f.error}`).join("<br>");
				frappe.show_alert({
					message: __("{0} items moved", [result.moved]),
					indicator: result.failed.length ? "orange" : "green",
				});
				if (failed) frappe.msgprint({ title: __("Some items were not moved"), message: failed, indicator: "orange" });
				listview.clear_checked_items();
				listview.refresh();
			});
	if (to_backlog) return frappe.confirm(__("Move {0} items to the backlog?", [checked.length]), () => run(null));
	frappe.prompt(
		{
			fieldname: "sprint",
			label: __("Sprint"),
			fieldtype: "Link",
			options: "Sprint",
			reqd: 1,
			get_query: () => ({ filters: { project: projects[0], status: ["in", ["Planned", "Active"]] } }),
		},
		(values) => run(values.sprint),
		__("Move {0} items to a sprint", [checked.length]),
		__("Move")
	);
}
