"""Summary and Summary Dark now draw Plan, Progress by module and Time spent: refresh the stored copies."""

import hashlib

import frappe

from auri_pms.install import template_html

# sha256 of the previous shipped HTML (stripped); a template that differs was edited by someone and is kept
PREVIOUS = {
	"PMS Status Report - Summary": (
		"pms_status_report_summary.html",
		"00f27b45db7ee2c0c6160e091c7e6a1ff706483029f52a5eab7591b6bcff5014",
	),
	"PMS Status Report - Summary Dark": (
		"pms_status_report_summary_dark.html",
		"c3e01f98b870d9e7ebf707600e10b8cd3383753a788677aa896afdefdc70eca9",
	),
}


def execute() -> None:
	for name, (filename, old_hash) in PREVIOUS.items():
		current = frappe.db.get_value("Email Template", name, "response_html")
		if current is None:
			continue
		if hashlib.sha256(current.strip().encode()).hexdigest() == old_hash:
			frappe.db.set_value("Email Template", name, "response_html", template_html(filename))
