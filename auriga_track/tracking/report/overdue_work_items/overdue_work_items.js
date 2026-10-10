// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

frappe.query_reports["Overdue Work Items"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "assigned_to", label: __("Assigned To"), fieldtype: "Link", options: "User"},
	],
};
