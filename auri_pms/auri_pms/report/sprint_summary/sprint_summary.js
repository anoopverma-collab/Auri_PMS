// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Sprint Summary"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", get_query: () => ({query: "auri_pms.auri_pms.api.project_link_query", filters: { pms_enabled: 1 }})},
		{fieldname: "status", label: __("Status"), fieldtype: "Select", options: ["", "Planned", "Active", "Completed"]},
	],
	formatter: (value, row, column, data, default_formatter) => auri_pms.ui.reportCell(value, row, column, data, default_formatter),
};
