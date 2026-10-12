"""Replace the first versions of the two ready-made status report Email Templates with the redesigned ones."""

from auri_pms.install import ensure_email_templates


def execute() -> None:
	ensure_email_templates(overwrite=True)
