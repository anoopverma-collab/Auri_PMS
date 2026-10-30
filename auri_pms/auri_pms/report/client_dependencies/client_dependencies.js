// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Client Dependencies"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", get_query: () => ({query: "auri_pms.auri_pms.api.project_link_query", filters: { pms_enabled: 1 }})},
		{fieldname: "assigned_to", label: __("Assigned To"), fieldtype: "Link", options: "User"},
		{fieldname: "min_days", label: __("Waiting at least (days)"), fieldtype: "Int", default: 0},
	],
	formatter: (value, row, column, data, default_formatter) => auri_pms.ui.reportCell(value, row, column, data, default_formatter),
};
