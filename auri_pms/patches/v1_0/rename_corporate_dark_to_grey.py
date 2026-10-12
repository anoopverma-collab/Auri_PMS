"""The Corporate Dark email template now has a grey background: rename it to Corporate Grey."""

import frappe

OLD, NEW = "PMS Status Report - Corporate Dark", "PMS Status Report - Corporate Grey"


def execute() -> None:
	if frappe.db.exists("Email Template", OLD) and not frappe.db.exists("Email Template", NEW):
		frappe.rename_doc("Email Template", OLD, NEW, force=True)
	frappe.clear_cache(doctype="PMS Settings")
