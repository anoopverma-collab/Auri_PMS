"""Risk Register calculations shared by the dashboards, the health status and the client report."""

from __future__ import annotations

import re
from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

OPEN_STATUSES = ("Identified", "Mitigating", "Monitoring")
LEVELS = ("Critical", "High", "Medium", "Low")
LIST_FIELDS = [
	"name",
	"title",
	"project",
	"status",
	"category",
	"risk_level",
	"risk_score",
	"probability",
	"impact",
	"risk_owner",
	"mitigation_due",
]


def scale_value(label: str | None) -> int:
	"""The number in front of a scale label such as ``4 - Likely``."""
	match = re.match(r"\s*(\d)", label or "")
	return cint(match.group(1)) if match else 0


def risk_level(score: int) -> str:
	"""Low 1-4, Medium 5-9, High 10-14, Critical 15-25."""
	if score >= 15:
		return "Critical"
	if score >= 10:
		return "High"
	if score >= 5:
		return "Medium"
	return "Low" if score else ""


def is_overdue(risk, today_=None) -> bool:
	"""An open risk whose mitigation date has passed."""
	return bool(
		risk.status in OPEN_STATUSES
		and risk.mitigation_due
		and getdate(risk.mitigation_due) < getdate(today_ or today())
	)


def _plural(count: int, one: str, many: str) -> str:
	return one if count == 1 else many


def risk_summary(project: str, limit: int = 8) -> frappe._dict:
	"""Counts, the probability x impact matrix and the top open risks of one project (permission aware)."""
	rows = frappe.get_list(
		"Risk Register", filters={"project": project}, fields=LIST_FIELDS, limit_page_length=0
	)
	open_rows = [r for r in rows if r.status in OPEN_STATUSES]
	by_level = Counter(r.risk_level for r in open_rows)
	matrix = [[0] * 5 for _row in range(5)]  # rows: probability 5..1, columns: impact 1..5
	for r in open_rows:
		p, i = scale_value(r.probability), scale_value(r.impact)
		if 1 <= p <= 5 and 1 <= i <= 5:
			matrix[5 - p][i - 1] += 1
	top = sorted(
		open_rows, key=lambda r: (-cint(r.risk_score), str(r.mitigation_due or "9999-12-31"), r.name)
	)[:limit]
	names = {
		u.name: u.full_name
		for u in frappe.get_all(
			"User",
			fields=["name", "full_name"],
			filters={"name": ["in", [r.risk_owner for r in top if r.risk_owner]]},
		)
	}
	return frappe._dict(
		total=len(rows),
		open=len(open_rows),
		by_level={level: by_level.get(level, 0) for level in LEVELS},
		overdue=sum(1 for r in open_rows if is_overdue(r)),
		occurred=sum(1 for r in rows if r.status == "Occurred"),
		closed=sum(1 for r in rows if r.status == "Closed"),
		matrix=matrix,
		top=[
			{
				"name": r.name,
				"title": r.title,
				"status": r.status,
				"risk_level": r.risk_level,
				"risk_score": cint(r.risk_score),
				"category": r.category,
				"owner": names.get(r.risk_owner) or r.risk_owner or "",
				"mitigation_due": str(r.mitigation_due) if r.mitigation_due else None,
				"overdue": is_overdue(r),
			}
			for r in top
		],
	)


def portfolio_risk_counts(projects: list[str]) -> dict[str, dict]:
	"""Open, critical, high and overdue risk counts for each project in ``projects`` (permission aware)."""
	counts = {p: {"open": 0, "critical": 0, "high": 0, "overdue": 0} for p in projects}
	if not projects:
		return counts
	for r in frappe.get_list(
		"Risk Register",
		filters={"project": ["in", projects], "status": ["in", list(OPEN_STATUSES)]},
		fields=["project", "risk_level", "status", "mitigation_due"],
		limit_page_length=0,
	):
		c = counts[r.project]
		c["open"] += 1
		c["critical"] += r.risk_level == "Critical"
		c["high"] += r.risk_level == "High"
		c["overdue"] += is_overdue(r)
	return counts


def my_risks(user: str, limit: int = 10) -> list[dict]:
	"""Open risks owned by ``user``, the highest score first (permission aware)."""
	rows = frappe.get_list(
		"Risk Register",
		filters={"risk_owner": user, "status": ["in", list(OPEN_STATUSES)]},
		fields=LIST_FIELDS,
		order_by="risk_score desc, mitigation_due asc",
		limit_page_length=limit,
	)
	project_names = {
		p.name: p.project_name
		for p in frappe.get_all(
			"Project",
			fields=["name", "project_name"],
			filters={"name": ["in", list({r.project for r in rows})]},
		)
	}
	return [
		{
			"name": r.name,
			"title": r.title,
			"project": r.project,
			"project_label": project_names.get(r.project) or r.project,
			"status": r.status,
			"risk_level": r.risk_level,
			"risk_score": cint(r.risk_score),
			"mitigation_due": str(r.mitigation_due) if r.mitigation_due else None,
			"overdue": is_overdue(r),
		}
		for r in rows
	]


def client_risks(project: str) -> list[dict]:
	"""Open risks the project manager chose to show to the client, with their mitigation plan."""
	rows = frappe.get_all(
		"Risk Register",
		filters={
			"project": project,
			"show_in_client_report": 1,
			"status": ["in", [*OPEN_STATUSES, "Occurred"]],
		},
		fields=[*LIST_FIELDS, "mitigation_plan"],
		order_by="risk_score desc, mitigation_due asc",
	)
	return [
		{
			"name": r.name,
			"title": r.title,
			"status": r.status,
			"risk_level": r.risk_level,
			"risk_score": cint(r.risk_score),
			"mitigation": frappe.utils.strip_html_tags(r.mitigation_plan or "").strip(),
			"mitigation_due": str(r.mitigation_due) if r.mitigation_due else None,
		}
		for r in rows
	]


def risk_reasons(project: str) -> list[dict]:
	"""Reasons for the project health status: critical or high open risks and overdue mitigations."""
	rows = frappe.get_all(
		"Risk Register",
		filters={"project": project, "status": ["in", list(OPEN_STATUSES)]},
		fields=["risk_level", "status", "mitigation_due"],
	)
	critical = sum(r.risk_level == "Critical" for r in rows)
	high = sum(r.risk_level == "High" for r in rows)
	overdue = sum(is_overdue(r) for r in rows)
	reasons: list[dict] = []
	if critical:
		reasons.append(
			{
				"level": "red",
				"text": _("{0} {1} open in the risk register").format(
					critical, _plural(critical, _("critical risk is"), _("critical risks are"))
				),
			}
		)
	elif high:
		reasons.append(
			{
				"level": "amber",
				"text": _("{0} {1} open in the risk register").format(
					high, _plural(high, _("high risk is"), _("high risks are"))
				),
			}
		)
	if overdue:
		reasons.append(
			{
				"level": "amber",
				"text": _("{0} {1} past the mitigation date").format(
					overdue, _plural(overdue, _("risk is"), _("risks are"))
				),
			}
		)
	return reasons
