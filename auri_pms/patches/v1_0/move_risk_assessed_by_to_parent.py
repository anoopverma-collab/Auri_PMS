from collections import defaultdict

import frappe
from frappe.utils import escape_html

MARKER = "Assessment history"


def execute():
	"""Keep the last assessor as Assessed By and the old history as a comment, then drop the Risk Assessment table."""
	frappe.reload_doc("auri_pms", "doctype", "risk_register")

	if frappe.db.table_exists("Risk Assessment"):
		rows = frappe.get_all(
			"Risk Assessment",
			filters={"parenttype": "Risk Register"},
			fields=[
				"parent",
				"assessed_on",
				"assessed_by",
				"probability",
				"impact",
				"risk_score",
				"risk_level",
			],
			order_by="parent, idx",
		)
		history = defaultdict(list)
		for row in rows:
			history[row.parent].append(row)
		for risk, entries in history.items():
			if not frappe.db.exists("Risk Register", risk):
				continue
			last = next((e.assessed_by for e in reversed(entries) if e.assessed_by), None)
			if last and not frappe.db.get_value("Risk Register", risk, "assessed_by"):
				frappe.db.set_value("Risk Register", risk, "assessed_by", last, update_modified=False)
			if not frappe.db.exists(
				"Comment",
				{
					"reference_doctype": "Risk Register",
					"reference_name": risk,
					"content": ["like", f"{MARKER}%"],
				},
			):
				items = "".join(
					f"<li>{e.assessed_on} · {escape_html(e.assessed_by or '')} · {escape_html(e.probability or '')}"
					f" x {escape_html(e.impact or '')} = {e.risk_score} ({escape_html(e.risk_level or '')})</li>"
					for e in entries
				)
				frappe.get_doc(
					{
						"doctype": "Comment",
						"comment_type": "Info",
						"reference_doctype": "Risk Register",
						"reference_name": risk,
						"content": f"{MARKER} (moved from the removed table):<ul>{items}</ul>",
					}
				).insert(ignore_permissions=True)

	if frappe.db.exists("DocType", "Risk Assessment"):
		frappe.delete_doc("DocType", "Risk Assessment", force=True, ignore_missing=True)
	frappe.db.sql_ddl("drop table if exists `tabRisk Assessment`")
