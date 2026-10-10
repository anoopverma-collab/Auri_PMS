// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Time Log Summary"] = {
	filters: [
		{fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_start()},
		{fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project"},
		{fieldname: "user", label: __("User"), fieldtype: "Link", options: "User"},
		{fieldname: "billable", label: __("Billable"), fieldtype: "Select", options: ["", "Billable", "Non-billable"]},
		{fieldname: "group_by", label: __("Group By"), fieldtype: "Select", options: ["User", "Project", "Activity", "Work Item"], default: "User"},
	],
};
