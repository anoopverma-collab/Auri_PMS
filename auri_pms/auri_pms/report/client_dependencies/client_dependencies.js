// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Client Dependencies"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "assigned_to", label: __("Assigned To"), fieldtype: "Link", options: "User"},
		{fieldname: "min_days", label: __("Waiting at least (days)"), fieldtype: "Int", default: 0},
	],
};
