"""Work item relations (T-060 .. T-067)."""

import frappe

from auri_pms.auri_pms.tests.utils import DEV, MGR, REP, TrackerTestCase, ensure_company


class TestRelations(TrackerTestCase):
	def relate(self, user, item, relation_type, target):
		item.append("relations", {"relation_type": relation_type, "related_work_item": target.name})
		return self.save_as(user, item)

	def rows(self, item):
		return {
			(r.relation_type, r.related_work_item) for r in frappe.get_doc("Work Item", item.name).relations
		}

	def test_t060_blocks_creates_blocked_by(self):
		"""T-060: A Blocks B gives B a Blocked by A row."""
		a, b = self.new_item(MGR), self.new_item(MGR)
		self.relate(MGR, a, "Blocks", b)
		self.assertIn(("Blocked by", a.name), self.rows(b))

	def test_t061_reverse_pairs(self):
		"""T-061: Relates, Duplicates and Precedes create the right reverse rows."""
		expected = {"Relates to": "Relates to", "Duplicates": "Duplicated by", "Precedes": "Follows"}
		for forward, reverse in expected.items():
			a, b = self.new_item(MGR), self.new_item(MGR)
			self.relate(MGR, a, forward, b)
			self.assertIn((reverse, a.name), self.rows(b), forward)

	def test_t062_removing_row_removes_reverse(self):
		"""T-062: removing A Blocks B removes the reverse row from B."""
		a, b = self.new_item(MGR), self.new_item(MGR)
		self.relate(MGR, a, "Blocks", b)
		a.reload()
		a.relations = []
		self.save_as(MGR, a)
		self.assertFalse(self.rows(b))

	def test_t063_reporter_relates_to_item_it_cannot_edit(self):
		"""T-063: rep relates own item to dev's item; the reverse row is written despite R-15."""
		own, theirs = self.new_item(REP), self.new_item(DEV)
		self.relate(REP, own, "Relates to", theirs)
		self.assertIn(("Relates to", own.name), self.rows(theirs))

	def test_t064_invalid_relations(self):
		"""T-064: self relation, duplicate row and block+blocked-by are rejected."""
		a, b = self.new_item(MGR), self.new_item(MGR)
		self.assertThrows("Cannot relate a work item to itself", lambda: self.relate(MGR, a, "Relates to", a))
		a.reload()
		a.relations = []
		a.append("relations", {"relation_type": "Blocks", "related_work_item": b.name})
		a.append("relations", {"relation_type": "Blocks", "related_work_item": b.name})
		self.assertThrows("This relation already exists", lambda: self.save_as(MGR, a))
		a.reload()
		a.relations = []
		a.append("relations", {"relation_type": "Blocks", "related_work_item": b.name})
		a.append("relations", {"relation_type": "Blocked by", "related_work_item": b.name})
		self.assertThrows("cannot both block and be blocked by", lambda: self.save_as(MGR, a))

	def test_t065_no_access_to_related_item(self):
		"""T-065: dev cannot relate to an item in a private project dev cannot read."""
		private = frappe.get_doc(
			{
				"doctype": "Project",
				"company": ensure_company(),
				"project_name": "Private",
				"pms_enabled": 1,
				"tracker_identifier": "PRV",
				"tracker_members": [{"user": MGR, "project_role": "Manager"}],
			}
		).insert()
		hidden = self.new_item(MGR, private.name)
		mine = self.new_item(DEV)
		self.assertThrows(
			f"You do not have access to {hidden.name}", lambda: self.relate(DEV, mine, "Relates to", hidden)
		)

	def test_t066_cross_project_relation(self):
		"""T-066: an ALP item can relate to a BET item."""
		alp_item, bet_item = self.new_item(MGR), self.new_item(MGR, self.BET)
		self.relate(MGR, alp_item, "Relates to", bet_item)
		self.assertIn(("Relates to", alp_item.name), self.rows(bet_item))

	def test_t067_delete_removes_reverse_rows(self):
		"""T-067: deleting A removes it from B's relations."""
		a, b = self.new_item(MGR), self.new_item(MGR)
		self.relate(MGR, a, "Blocks", b)
		with self.as_user(MGR):
			frappe.delete_doc("Work Item", a.name)
		self.assertFalse(self.rows(b))
