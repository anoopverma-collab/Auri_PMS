// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.views.calendar["Work Item"] = {
	field_map: {
		start: "start_date",
		end: "due_date",
		id: "name",
		title: "subject",
		allDay: "allDay",
		progress: "done_percent",
	},
	gantt: true,
	filters: [
		{ fieldtype: "Link", fieldname: "project", options: "Project", label: __("Project"), get_query: () => ({query: "auri_pms.auri_pms.api.project_link_query", filters: { pms_enabled: 1 }}) },
		{ fieldtype: "Link", fieldname: "assigned_to", options: "User", label: __("Assigned To") },
	],
	get_events_method: "frappe.desk.calendar.get_events",
};
