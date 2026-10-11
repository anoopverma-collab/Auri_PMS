"""Project Status Report - a log of every client status report that was emailed."""

from frappe.model.document import Document


class ProjectStatusReport(Document):
	"""A sent (or scheduled) client status report with the exact HTML that went out."""
