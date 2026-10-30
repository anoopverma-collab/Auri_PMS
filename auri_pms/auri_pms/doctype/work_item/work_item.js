// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

const WI_API = "auri_pms.auri_pms.api";

frappe.ui.form.on("Work Item", {
	setup(frm) {
		frm.set_query("project", () => ({ query: `${WI_API}.project_create_query` }));
		// Every project-bound dropdown waits for the project: say so once, then offer nothing.
		const need_project = (query) => () => {
			if (frm.doc.project) return query();
			if (!frm._project_msg_shown) {
				frm._project_msg_shown = true;
				frappe.show_alert({ message: __("Select a Project first"), indicator: "orange" }, 5);
			}
			return { filters: { name: ["in", [""]] } };
		};
		frm.set_query("tracker", need_project(() => ({
			query: `${WI_API}.tracker_query`,
			filters: { project: frm.doc.project },
		})));
		frm.set_query("status", need_project(() => ({
			query: `${WI_API}.status_query`,
			filters: {
				work_item: frm.is_new() ? "" : frm.doc.name,
				tracker: frm.doc.tracker,
				project: frm.doc.project,
			},
		})));
		frm.set_query("assigned_to", need_project(() => ({
			query: `${WI_API}.assignee_query`,
			filters: { project: frm.doc.project },
		})));
		frm.set_query("user", "additional_assignees", need_project(() => ({
			query: `${WI_API}.assignee_query`,
			filters: { project: frm.doc.project },
		})));
		frm.set_query("category", need_project(() => ({
			query: `${WI_API}.category_link_query`,
			filters: { project: frm.doc.project },
		})));
		frm.set_query("project_module", need_project(() => ({
			query: `${WI_API}.module_query`,
			filters: { project: frm.doc.project },
		})));
		frm.set_query("release", need_project(() => ({ filters: { project: frm.doc.project, status: "Open" } })));
		frm.set_query("sprint", need_project(() => {
			const statuses = ["Planned", "Active"];
			// PMS Settings > Allow Completed Sprint for Closed Tickets
			const closed_ok = frm.doc.__onload && cint(frm.doc.__onload.allow_completed_sprint_for_closed) && cint(frm.doc.is_closed);
			if (closed_ok) statuses.push("Completed");
			return { filters: { project: frm.doc.project, status: ["in", statuses] } };
		}));
		frm.set_query("parent_work_item", need_project(() => ({
			query: `${WI_API}.parent_query`,
			filters: { project: frm.doc.project, work_item: frm.is_new() ? "" : frm.doc.name },
		})));
	},

	refresh(frm) {
		frm.trigger("status_hint");
		frm.trigger("move_connections");
		frm.trigger("set_indicator");
		frm.trigger("summary_chips");
		frm.trigger("client_headline");
		frm.trigger("lock_done_percent");
		// PMS Settings > Keep Closed On Visible and Editable: an editable field is also shown while empty
		if (frm.doc.__onload && cint(frm.doc.__onload.keep_closed_on_editable)) frm.set_df_property("closed_on", "read_only", 0);
		// Project Role > Field Rules: fields the role may only view are locked once the item exists.
		if (!frm.is_new() && frm.doc.__onload) {
			(frm.doc.__onload.view_only_fields || []).forEach((f) => frm.set_df_property(f, "read_only", 1));
		}
		// PMS Settings > Waiting Since Editable
		if (frm.doc.__onload && cint(frm.doc.__onload.waiting_since_editable)) frm.set_df_property("client_dependency_since", "read_only", 0);
		if (frm.is_new()) return;
		frm.add_custom_button(__("Log Time"), () => wi_log_time(frm));
		frm.add_custom_button(__("Add Subtask"), () => {
			frappe.new_doc("Work Item", {
				parent_work_item: frm.doc.name,
				project: frm.doc.project,
				tracker: frm.doc.tracker,
			});
		});
		frappe.xcall(`${WI_API}.get_status_actions`, { work_item: frm.doc.name }).then((actions) => {
			if (actions.close) {
				frm.add_custom_button(__("Close"), () => wi_change_status(frm, actions.close));
			}
			if (actions.reopen) {
				frm.add_custom_button(__("Reopen"), () => wi_change_status(frm, actions.reopen));
			}
		});
	},

	set_indicator(frm) {
		if (frm.is_new()) return;
		const overdue =
			!cint(frm.doc.is_closed) &&
			frm.doc.due_date &&
			frappe.datetime.get_diff(frm.doc.due_date, frappe.datetime.get_today()) < 0;
		if (overdue) {
			frm.page.set_indicator(__("Overdue"), "red");
		} else {
			wi_status_colors().then((colors) => {
				frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");
			});
		}
	},

	// Frappe draws Connections (Subtasks, Time) above the first tab; show them at the end of the first tab instead.
	move_connections(frm) {
		const first = (frm.layout.tabs || [])[0];
		const area = frm.dashboard && frm.dashboard.links_area;
		if (first && area) first.wrapper.append(area.wrapper.addClass("auri-connections"));
	},

	summary_chips(frm) {
		if (frm.is_new()) return;
		frm.dashboard.clear_headline(); // refresh runs more than once after a first save; do not stack the chips
		frm.dashboard.set_headline(
			auri_pms.ui.chips([
				auri_pms.ui.priority(frm.doc.priority),
				frm.doc.tracker && frappe.utils.escape_html(frm.doc.tracker),
				frm.doc.due_date && `${__("Due")} ${auri_pms.ui.due(frm.doc.due_date, frm.doc.is_closed)}`,
				flt(frm.doc.done_percent) ? `${__("Done")} ${cint(frm.doc.done_percent)}%` : "",
			])
		);
	},

	client_headline(frm) {
		if (!cint(frm.doc.dependent_on_client) || cint(frm.doc.is_closed) || frm.is_new()) return;
		const since = frm.doc.client_dependency_since ? frappe.datetime.str_to_user(frm.doc.client_dependency_since) : "";
		const note = frm.doc.client_dependency_note ? ` - ${frappe.utils.escape_html(frm.doc.client_dependency_note)}` : "";
		frm.dashboard.set_headline_alert(`<span>${__("Waiting on the client")}${since ? ` ${__("since {0}", [since])}` : ""}${note}</span>`, "orange");
	},

	dependent_on_client(frm) {
		if (!cint(frm.doc.dependent_on_client)) frm.set_value("client_dependency_note", null);
	},

	lock_done_percent(frm) {
		const has_children = frm.doc.__onload && frm.doc.__onload.has_children;
		frm.set_df_property("done_percent", "read_only", has_children ? 1 : 0);
	},

	tracker(frm) {
		if (!frm.is_new() || !frm.doc.tracker) return;
		frappe.xcall(`${WI_API}.get_default_status`, { tracker: frm.doc.tracker }).then((status) => {
			if (status) frm.set_value("status", status);
		});
	},

	status_hint(frm) {
		// The statuses come from the project, so ask for it first.
		const hint = frm.doc.project ? "" : __("Select a Project first to choose a Status");
		frm.set_df_property("status", "description", hint);
		frm.set_df_property("status", "placeholder", hint);
	},

	project(frm) {
		frm._project_msg_shown = false;
		frm.trigger("status_hint");
		if (!frm.is_new()) return;
		["tracker", "status", "assigned_to", "category", "project_module", "release", "sprint", "parent_work_item"].forEach((f) => {
			if (frm.doc[f] && f !== "parent_work_item") frm.set_value(f, null);
		});
		wi_load_project_custom(frm);
	},
});

// Choosing the project shows its custom fields (Project > Custom Fields) at once, filled with the project's values.
function wi_load_project_custom(frm) {
	const range = Array.from({ length: 10 }, (_, i) => i + 1);
	if (!frm.doc.project) {
		frm.set_value("project_custom_count", 0);
		range.forEach((n) => frm.set_value(`project_custom_${n}`, ""));
		return;
	}
	frappe.db.get_value("Project", frm.doc.project, ["pms_custom_count", ...range.map((n) => `pms_custom_${n}`)]).then(({ message }) => {
		const count = cint(message && message.pms_custom_count);
		frm.set_value("project_custom_count", count);
		range.forEach((n) => frm.set_value(`project_custom_${n}`, n <= count ? (message[`pms_custom_${n}`] || "") : ""));
	});
}

function wi_change_status(frm, status) {
	frm.set_value("status", status).then(() => frm.save());
}

function wi_log_time(frm) {
	frappe.prompt(
		[
			{ fieldname: "hours", label: __("Hours"), fieldtype: "Float", reqd: 1 },
			{ fieldname: "activity_type", label: __("Activity"), fieldtype: "Link", options: "Activity Type", reqd: 1 },
			{ fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
			{ fieldname: "is_billable", label: __("Billable"), fieldtype: "Check", default: 1 },
			{ fieldname: "comment", label: __("Comment"), fieldtype: "Small Text", reqd: 1 },
		],
		(values) => {
			frappe
				.xcall(`${WI_API}.log_time`, { work_item: frm.doc.name, ...values })
				.then(() => {
					frappe.show_alert({ message: __("Time logged"), indicator: "green" });
					frm.reload_doc();
				});
		},
		__("Log Time on {0}", [frm.doc.name]),
		__("Log")
	);
}

// Desk indicator colour per status, computed on the server from the status colour.
let wi_colors_promise = null;
function wi_status_colors() {
	if (!wi_colors_promise) wi_colors_promise = frappe.xcall(`${WI_API}.get_status_indicators`);
	return wi_colors_promise;
}
