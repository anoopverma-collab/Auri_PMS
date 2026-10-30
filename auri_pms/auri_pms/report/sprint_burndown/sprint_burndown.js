// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Sprint Burndown"] = {
	filters: [
		{fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project",
			get_query: () => ({query: "auri_pms.auri_pms.api.project_link_query", filters: { pms_enabled: 1 }}),
			// a sprint of another project no longer applies
			on_change: () => {
				frappe.query_report.set_filter_value("sprint", "");
				frappe.query_report.refresh();
			}},
		{fieldname: "sprint", label: __("Sprint"), fieldtype: "Link", options: "Sprint", reqd: 1,
			get_query: () => {
				const project = frappe.query_report.get_filter_value("project");
				return {filters: {status: ["in", ["Active", "Completed"]], ...(project ? {project} : {})}};
			}},
	],
};
