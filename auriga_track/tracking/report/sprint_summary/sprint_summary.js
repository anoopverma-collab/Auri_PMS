// Copyright (c) 2026, Auriga IT and contributors
// For license information, please see license.txt

frappe.query_reports["Sprint Summary"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "status", label: __("Status"), fieldtype: "Select", options: ["", "Planned", "Active", "Completed"]},
	],
};
