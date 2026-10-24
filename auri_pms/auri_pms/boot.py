"""Boot data: the risk score thresholds and whether the Portfolio is open to the user, without a server round trip."""

from __future__ import annotations

import frappe

from auri_pms.auri_pms.risk import risk_thresholds
from auri_pms.auri_pms.utils import portfolio_projects


def boot_session(bootinfo) -> None:
	"""Expose the risk thresholds of PMS Settings and the Portfolio access to the client."""
	if frappe.session.user != "Guest":
		bootinfo.auri_pms_risk_thresholds = risk_thresholds()
		# managers, and members who manage at least one project (their Project Role can manage members)
		bootinfo.auri_pms_portfolio = bool(portfolio_projects())
