"""Make sure the ready-made status report Email Templates exist; one that is already there (possibly edited) is kept."""

from auri_pms.install import ensure_email_templates


def execute() -> None:
	ensure_email_templates()
