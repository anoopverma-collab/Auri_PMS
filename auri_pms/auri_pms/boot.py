"""Boot data: the risk score thresholds and whether the Portfolio is open to the user, without a server round trip."""

from __future__ import annotations

import frappe

from auri_pms.auri_pms.risk import risk_thresholds
from auri_pms.auri_pms.utils import (
	create_permissions,
	health_cost_projects,
	insight_projects,
	portfolio_projects,
)

SIDEBAR = "Auri PMS"


def drop_stale_generated_sidebar() -> bool:
	"""Make the app's own sidebar win over the one Frappe generates for the module.

	Frappe builds a sidebar for every module without a sidebar of its own and keeps that list in each worker's memory
	for good. A site that booted before this app's sidebar existed (a first deploy, a worker that was not restarted
	after migrate) keeps showing the generated one, because it replaces the real one of the same name. When the
	cached list still holds a generated "Auri PMS" sidebar although the real one exists, the cache is cleared so the
	list is built again. Returns True when it did.
	"""
	try:
		from frappe.desk.doctype.workspace_sidebar import workspace_sidebar as ws

		generate = getattr(ws, "auto_generate_sidebar_from_module", None)
		if generate is None:  # a Frappe version that does not generate sidebars from modules
			return False
		if not any(getattr(sidebar, "title", None) == SIDEBAR for sidebar in generate()):
			return False
		if not frappe.db.exists("Workspace Sidebar", {"name": SIDEBAR, "for_user": ["is", "not set"]}):
			return False
		generate.clear_cache()
		return True
	except Exception:
		frappe.log_error("Auri PMS: could not refresh the generated sidebar list")
		return False


# the roles that may open My Work: the Auri PMS roles and System Manager (who can open every Auri PMS page)
PMS_ROLES = frozenset({"Auri PMS User", "Auri PMS Manager", "Auri PMS Admin", "System Manager"})


def boot_session(bootinfo) -> None:
	"""Expose the risk thresholds of PMS Settings and the Portfolio access to the client."""
	drop_stale_generated_sidebar()
	if frappe.session.user != "Guest":
		bootinfo.auri_pms_risk_thresholds = risk_thresholds()
		# Auri PMS Admins, and everyone who is a member of at least one Auri PMS project
		bootinfo.auri_pms_portfolio = bool(portfolio_projects())
		# the Health and cost tab and Auri Insights follow the Project Role ticks
		bootinfo.auri_pms_health_cost = bool(health_cost_projects())
		bootinfo.auri_pms_insights = bool(insight_projects())
		# the My Work button: an Auri PMS role or System Manager, and the module not blocked on the User
		blocked = frappe.db.exists("Block Module", {"parent": frappe.session.user, "module": "Auri PMS"})
		bootinfo.auri_pms_my_work = bool(PMS_ROLES & set(frappe.get_roles())) and not blocked
		# the New button of each project record follows the same table as the server (CREATE_RULES)
		bootinfo.auri_pms_can_create = create_permissions()
