"""PMS Report Section - one row of the order in which the client status report lists its sections."""

from frappe.model.document import Document


class PMSReportSection(Document):
	"""A section of the status report; the row position is the position in the report."""
