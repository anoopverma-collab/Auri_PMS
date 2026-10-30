// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Work Item Summary"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", get_query: () => ({query: "auri_pms.auri_pms.api.project_link_query", filters: { pms_enabled: 1 }})},
		{fieldname: "tracker", label: __("Ticket Type"), fieldtype: "Link", options: "Ticket Type", get_query: () => ({query: "auri_pms.auri_pms.api.tracker_query"})},
		{
			fieldname: "project_module",
			label: __("Module"),
			fieldtype: "Link",
			options: "Project Module",
			get_query: () => ({ filters: frappe.query_report.get_filter_value("project") ? { project: frappe.query_report.get_filter_value("project") } : {} }),
		},
		{fieldname: "release", label: __("Release"), fieldtype: "Link", options: "Release",
			get_query: () => ({filters: frappe.query_report.get_filter_value("project") ? {project: frappe.query_report.get_filter_value("project")} : {}})},
		{fieldname: "from_date", label: __("Closed From"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -30)},
		{fieldname: "to_date", label: __("Closed To"), fieldtype: "Date", default: frappe.datetime.get_today()},
	],
	formatter: (value, row, column, data, default_formatter) => auri_pms.ui.reportCell(value, row, column, data, default_formatter),
};
