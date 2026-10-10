// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.query_reports["Sprint Burndown"] = {
	filters: [
		{fieldname: "sprint", label: __("Sprint"), fieldtype: "Link", options: "Sprint", reqd: 1,
			get_query: () => ({filters: {status: ["in", ["Active", "Completed"]]}})},
	],
};
