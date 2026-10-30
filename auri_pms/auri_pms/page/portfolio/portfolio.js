// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// The Portfolio now lives in Delivery & Health ("Health and cost" tab). This page only keeps old links and bookmarks working.
frappe.pages["portfolio"].on_page_show = function () {
	frappe.route_options = { tab: "health" };
	frappe.set_route("management-dashboard");
};
