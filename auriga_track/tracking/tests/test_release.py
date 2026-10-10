"""Releases (T-080 .. T-085)."""

import frappe

from auriga_track.tracking.tests.utils import DEV, MGR, TM, TrackerTestCase


class TestRelease(TrackerTestCase):
	def release(self, name, user=MGR, **kw):
		with self.as_user(user):
			return frappe.get_doc(
				{"doctype": "Release", "release_name": name, "project": self.ALP, **kw}
			).insert()

	def values(self, release, *fields):
		return frappe.db.get_value("Release", release, list(fields), as_dict=True)

	def test_t080_dev_cannot_create_release(self):
		"""T-080: dev (no can_manage_releases) cannot create a release."""
		self.assertThrows(
			"You are not allowed to manage releases in Project", lambda: self.release("x1", DEV)
		)

	def test_t081_counts_and_percent(self):
		"""T-081: 4 items, 1 closed -> total 4, closed 1, 25%."""
		v1 = self.world.releases["v1"]
		items = [self.new_item(MGR, tracker="Task", release=v1) for _ in range(4)]
		self.save_as(MGR, items[0], status="Closed")
		self.assertEqual(
			self.values(v1, "total_items", "closed_items", "percent_complete"),
			{"total_items": 4, "closed_items": 1, "percent_complete": 25},
		)

	def test_t082_move_item_between_releases(self):
		"""T-082: moving an item recalculates both releases."""
		v1, other = self.world.releases["v1"], self.release("v3").name
		item = self.new_item(MGR, tracker="Task", release=v1)
		self.new_item(MGR, tracker="Task", release=v1)
		self.save_as(MGR, item, release=other)
		self.assertEqual(self.values(v1, "total_items").total_items, 1)
		self.assertEqual(self.values(other, "total_items").total_items, 1)

	def test_t083_roadmap_flag(self):
		"""T-083: a tracker with show_in_roadmap = 0 does not count towards % complete."""
		frappe.db.set_value("Tracker", "Support", "show_in_roadmap", 0)
		v1 = self.world.releases["v1"]
		self.new_item(MGR, tracker="Bug", release=v1)
		support = self.new_item(MGR, tracker="Support", release=v1)
		self.save_as(MGR, support, status="Closed")
		self.assertEqual(
			self.values(v1, "total_items", "percent_complete"), {"total_items": 2, "percent_complete": 0}
		)

	def test_t084_close_release(self):
		"""T-084: closing with open items is rejected; after moving them it saves and members are notified."""
		v1 = self.world.releases["v1"]
		item = self.new_item(MGR, tracker="Task", release=v1)
		release = frappe.get_doc("Release", v1)
		self.assertThrows(
			"Move or close 1 open items before closing this release",
			lambda: self.save_as(MGR, release, status="Closed"),
		)
		item.reload()
		self.save_as(MGR, item, release=None)
		release.reload()
		self.save_as(MGR, release, status="Closed")
		self.assertTrue(
			frappe.db.exists(
				"Notification Log", {"document_type": "Release", "document_name": v1, "for_user": MGR}
			)
		)

	def test_t085_delete_release_with_items(self):
		"""T-085: a release with items cannot be deleted."""
		v1 = self.world.releases["v1"]
		self.new_item(MGR, tracker="Task", release=v1)
		with self.as_user(TM):
			self.assertRaises(frappe.LinkExistsError, frappe.delete_doc, "Release", v1)
