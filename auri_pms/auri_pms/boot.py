"""Boot data: the risk score thresholds the desk shows without a server round trip."""

from __future__ import annotations

import frappe

from auri_pms.auri_pms.risk import risk_thresholds


def boot_session(bootinfo) -> None:
	"""Expose the risk thresholds of PMS Settings to the client."""
	if frappe.session.user != "Guest":
		bootinfo.auri_pms_risk_thresholds = risk_thresholds()
