// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Sprint Summary"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", get_query: () => ({filters: {pms_enabled: 1}})},
		{fieldname: "status", label: __("Status"), fieldtype: "Select", options: ["", "Planned", "Active", "Completed"]},
	],
};
