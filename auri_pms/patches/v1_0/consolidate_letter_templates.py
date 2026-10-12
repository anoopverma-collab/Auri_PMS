"""Keep one ready-made letter design: rename "Auriga Blue" to "Blue" and remove the other three."""

import frappe

OLD_BLUE, NEW_BLUE = "PMS Letter - Auriga Blue", "PMS Letter - Blue"
REMOVED = ("PMS Letter - Royal Light", "PMS Letter - Emerald Gold", "PMS Letter - Royal Purple")


def execute() -> None:
	if frappe.db.exists("Email Template", OLD_BLUE) and not frappe.db.exists("Email Template", NEW_BLUE):
		frappe.rename_doc("Email Template", OLD_BLUE, NEW_BLUE, force=True)
	for name in REMOVED:
		if frappe.db.exists("Email Template", name):
			frappe.delete_doc("Email Template", name, force=True, ignore_permissions=True)
	frappe.clear_cache(doctype="PMS Settings")
