import frappe


def execute():
	"""Keep the last assessor of every risk as Assessed By, then drop the Risk Assessment history table."""
	frappe.reload_doc("auri_pms", "doctype", "risk_register")

	if frappe.db.table_exists("Risk Assessment"):
		frappe.db.sql(
			"""
			update `tabRisk Register` r
			join (
				select parent, substring_index(group_concat(assessed_by order by idx desc), ',', 1) as assessed_by
				from `tabRisk Assessment`
				where parenttype = 'Risk Register' and ifnull(assessed_by, '') != ''
				group by parent
			) h on h.parent = r.name
			set r.assessed_by = h.assessed_by
			where ifnull(r.assessed_by, '') = ''
			"""
		)

	if frappe.db.exists("DocType", "Risk Assessment"):
		frappe.delete_doc("DocType", "Risk Assessment", force=True, ignore_missing=True)
	frappe.db.sql_ddl("drop table if exists `tabRisk Assessment`")
