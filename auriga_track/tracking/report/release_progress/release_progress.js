// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Release Progress"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "status", label: __("Status"), fieldtype: "Select", options: ["", "Open", "Locked", "Closed"]},
	],
};
