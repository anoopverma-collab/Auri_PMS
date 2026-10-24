"""Boot data: the risk score thresholds and whether the Portfolio is open to the user, without a server round trip."""

from __future__ import annotations

import frappe

from auri_pms.auri_pms.risk import risk_thresholds
from auri_pms.auri_pms.utils import portfolio_projects

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

		if not any(
			getattr(sidebar, "title", None) == SIDEBAR for sidebar in ws.auto_generate_sidebar_from_module()
		):
			return False
		if not frappe.db.exists("Workspace Sidebar", {"name": SIDEBAR, "for_user": ["is", "not set"]}):
			return False
		ws.auto_generate_sidebar_from_module.clear_cache()
		return True
	except Exception:
		frappe.log_error("Auri PMS: could not refresh the generated sidebar list")
		return False


def boot_session(bootinfo) -> None:
	"""Expose the risk thresholds of PMS Settings and the Portfolio access to the client."""
	drop_stale_generated_sidebar()
	if frappe.session.user != "Guest":
		bootinfo.auri_pms_risk_thresholds = risk_thresholds()
		# managers, and members who manage at least one project (their Project Role can manage members)
		bootinfo.auri_pms_portfolio = bool(portfolio_projects())
