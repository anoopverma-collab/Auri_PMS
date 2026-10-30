"""The Auri PMS tab of the Project was laid out again: delete the Custom Fields the new layout no longer uses."""

import frappe

REMOVED = (
	"tracker_report_bcc",  # BCC was removed from the status report
	"pms_custom_row_1",
	"pms_custom_row_2",
	"pms_custom_row_3",
	"pms_custom_row_4",
	"pms_custom_col_5",
	"pms_custom_col_6",
	"pms_custom_col_8",
	"pms_custom_col_9",
)


def execute() -> None:
	for fieldname in REMOVED:
		name = f"Project-{fieldname}"
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
