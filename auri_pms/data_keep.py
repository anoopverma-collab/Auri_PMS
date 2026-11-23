"""Keep the Auri PMS data across an uninstall and a new install.

``bench uninstall-app`` drops the table of every Auri PMS DocType and the Auri PMS Custom Fields on Project.
Before that happens ``before_uninstall`` copies the records into one plain table (``__auri_pms_kept``). It is not a
DocType, so the uninstall leaves it alone. ``after_install`` puts the records back.

Records come back with ``db_insert``: names, owners and dates stay as they were, and no hook runs (no ToDo,
no roll-up, no mail). A record that already exists is never changed.
"""

from __future__ import annotations

import json
from itertools import batched, chain

import frappe
from frappe.model import no_value_fields
from frappe.utils import cint, now
from pypika import Table

TABLE = "__auri_pms_kept"
MODULE = "Auri PMS"
PAGE = 500
TABLE_FIELDS = ("Table", "Table MultiSelect")


def keep_data_enabled() -> bool:
	"""False when the site config key ``auri_pms_drop_data_on_uninstall`` is 1: a clean uninstall."""
	return not cint(frappe.conf.get("auri_pms_drop_data_on_uninstall"))


class KeptData:
	"""Save the Auri PMS records to the backup table and restore them from it."""

	def __init__(self) -> None:
		self.table = Table(TABLE)
		self.names: set[str] = set()  # record names seen while saving, to pick the naming counters

	# ------------------------------------------------------------------ save
	def save(self) -> int:
		"""Replace the table content with the current records and return the row count.

		An empty site never replaces an older copy, so a second uninstall cannot erase the first."""
		rows = chain(self.document_rows(), self.project_rows())
		first = next(rows, None)
		if first is None:
			return 0
		self.ensure_table()
		frappe.qb.from_(self.table).delete().run()
		count = self.write(chain([first], rows)) + self.write(self.series_rows())
		frappe.logger("auri_pms").info(f"Kept {count} Auri PMS rows in {TABLE}")
		return count

	@staticmethod
	def table_present() -> bool:
		"""``frappe.db.table_exists`` only knows ``tab`` tables, so look at the real table list."""
		return TABLE in frappe.db.get_tables(cached=False)

	def ensure_table(self) -> None:
		if self.table_present():
			return
		frappe.db.sql_ddl(
			f"""create table `{TABLE}` (
				`kind` varchar(20) not null,
				`doctype` varchar(140) not null,
				`name` varchar(255) not null,
				`data` longtext,
				`kept_on` datetime,
				primary key (`kind`, `doctype`, `name`)
			) engine=InnoDB row_format=dynamic character set=utf8mb4 collate=utf8mb4_unicode_ci"""
		)

	def write(self, rows) -> int:
		count = 0
		for batch in batched(rows, 200, strict=False):
			query = frappe.qb.into(self.table).columns("kind", "doctype", "name", "data", "kept_on")
			for kind, doctype, name, data in batch:
				query = query.insert(kind, doctype, name, json.dumps(data, default=str), now())
			query.run()
			count += len(batch)
		return count

	def document_rows(self):
		"""One row per record of every DocType of the module; child rows travel inside their parent."""
		for doctype in frappe.get_all(
			"DocType", filters={"module": MODULE, "istable": 0}, pluck="name", order_by="name"
		):
			meta = frappe.get_meta(doctype)
			if meta.issingle:
				yield from self.single_row(meta)
			elif frappe.db.table_exists(doctype):
				yield from self.records(meta)

	def single_row(self, meta):
		values = frappe.db.get_singles_dict(
			meta.name
		)  # only the stored values: a never saved Check stays unsaved
		children = self.children_of(meta.name, self.table_fields(meta), [meta.name]).get(meta.name, {})
		if values or children:
			yield "single", meta.name, meta.name, {"values": values, "children": children}

	def records(self, meta):
		tables = self.table_fields(meta)
		start = 0
		while page := frappe.get_all(
			meta.name,
			fields=["*"],
			order_by="creation asc, name asc",
			limit_start=start,
			limit_page_length=PAGE,
		):
			children = self.children_of(meta.name, tables, [row.name for row in page])
			for row in page:
				self.names.add(row.name)
				yield "doc", meta.name, row.name, {"values": row, "children": children.get(row.name, {})}
			start += PAGE

	def project_rows(self):
		"""The Auri PMS fields of every Project: members, enabled statuses, modules, ticket types and the rest."""
		fields = frappe.get_all(
			"Custom Field",
			filters={"dt": "Project", "module": MODULE},
			fields=["fieldname", "fieldtype", "options"],
		)
		tables = {f.fieldname: f.options for f in fields if f.fieldtype in TABLE_FIELDS}
		scalars = [
			f.fieldname
			for f in fields
			if f.fieldtype not in no_value_fields + TABLE_FIELDS
			and frappe.db.has_column("Project", f.fieldname)
		]
		projects = frappe.get_all("Project", fields=["name", *scalars], limit_page_length=0)
		children = self.children_of("Project", tables, [p.name for p in projects])
		for project in projects:
			values = {k: v for k, v in project.items() if k != "name" and v not in (None, "")}
			if values or children.get(project.name):
				yield (
					"project",
					"Project",
					project.name,
					{"values": values, "children": children.get(project.name, {})},
				)

	def series_rows(self):
		"""The naming counters of the saved records (ALP-, TE-2026- ...), so new records do not repeat a name."""
		series = Table("tabSeries")  # Series is a plain table, not a DocType
		for name, current in frappe.qb.from_(series).select(series.name, series.current).run():
			if name and any(record.startswith(name) for record in self.names):
				yield "series", "Series", name, {"current": current}

	@staticmethod
	def table_fields(meta) -> dict[str, str]:
		return {df.fieldname: df.options for df in meta.get_table_fields()}

	@staticmethod
	def children_of(doctype: str, tables: dict[str, str], parents: list[str]) -> dict[str, dict[str, list]]:
		"""{parent: {fieldname: [child rows]}} read straight from the child tables."""
		found: dict[str, dict[str, list]] = {}
		for fieldname, child in tables.items():
			if not parents or not frappe.db.table_exists(child):
				continue
			rows = frappe.get_all(
				child,
				filters={"parent": ["in", parents], "parenttype": doctype, "parentfield": fieldname},
				fields=["*"],
				order_by="idx asc",
				limit_page_length=0,
			)
			for row in rows:
				found.setdefault(row.parent, {}).setdefault(fieldname, []).append(row)
		return found

	# ------------------------------------------------------------------ restore
	def has_data(self) -> bool:
		return bool(self.table_present() and frappe.qb.from_(self.table).select("kind").limit(1).run())

	def restore_documents(self) -> int:
		"""Recreate the saved records that are missing, then lift the naming counters. Return the number created."""
		if not self.has_data():
			return 0
		created = 0
		for kind, doctype, rows in self.read(("doc", "single")):
			if kind == "single":
				created += sum(self.restore_single(doctype, data) for _, data in rows)
			else:
				created += self.restore_records(doctype, rows)
		self.restore_series()
		frappe.logger("auri_pms").info(f"Restored {created} Auri PMS records from {TABLE}")
		return created

	def restore_projects(self, sync: bool = True) -> int:
		"""Put the Auri PMS fields back on the Projects. Their Custom Fields come from the fixtures, so import those first."""
		if not self.has_data():
			return 0
		rows = [r for _, _, page in self.read(("project",)) for r in page]
		if not rows:
			return 0
		if sync:
			from frappe.utils.fixtures import sync_fixtures

			sync_fixtures("auri_pms")  # install runs it after after_install; it is safe to run twice
		return sum(self.restore_project(name, data) for name, data in rows)

	def read(self, kinds: tuple[str, ...]):
		"""Yield (kind, doctype, [(name, data)]) pages of the saved rows."""
		start = 0
		while page := (
			frappe.qb.from_(self.table)
			.select("kind", "doctype", "name", "data")
			.where(self.table.kind.isin(kinds))
			.orderby(self.table.kind)
			.orderby(self.table.doctype)
			.orderby(self.table.name)
			.limit(PAGE)
			.offset(start)
			.run()
		):
			by_group: dict[tuple, list] = {}
			for kind, doctype, name, data in page:
				by_group.setdefault((kind, doctype), []).append((name, json.loads(data)))
			for (kind, doctype), rows in by_group.items():
				yield kind, doctype, rows
			start += PAGE

	def restore_records(self, doctype: str, rows: list) -> int:
		if not frappe.db.table_exists(doctype):  # the DocType no longer exists in this version
			return 0
		existing = set(frappe.get_all(doctype, filters={"name": ["in", [n for n, _ in rows]]}, pluck="name"))
		created = 0
		for name, data in rows:
			if name not in existing:
				self.insert(doctype, data["values"], data["children"])
				created += 1
		return created

	def restore_single(self, doctype: str, data: dict) -> int:
		stored = frappe.db.get_singles_dict(doctype)
		restored = 0
		for field, value in data["values"].items():
			if field not in stored:
				frappe.db.set_single_value(doctype, field, value, update_modified=False)
				restored += 1
		for fieldname, rows in data["children"].items():
			child = self.child_doctype(doctype, fieldname)
			if child and not frappe.db.exists(
				child, {"parent": doctype, "parenttype": doctype, "parentfield": fieldname}
			):
				self.insert_children(doctype, {fieldname: rows})
				restored += len(rows)
		return restored

	def restore_project(self, name: str, data: dict) -> int:
		if not frappe.db.exists("Project", name):
			return 0
		values = {k: v for k, v in data["values"].items() if frappe.db.has_column("Project", k)}
		if values:
			frappe.db.set_value("Project", name, values, update_modified=False)
		for fieldname, rows in data["children"].items():
			child = self.project_child_doctype(fieldname)
			if child and not frappe.db.exists(
				child, {"parent": name, "parenttype": "Project", "parentfield": fieldname}
			):
				self.insert_children("Project", {fieldname: rows}, child_doctype=child)
		return 1

	def insert(self, doctype: str, values: dict, children: dict) -> None:
		frappe.get_doc({**values, "doctype": doctype}).db_insert()
		self.insert_children(doctype, children)

	def insert_children(self, doctype: str, children: dict, child_doctype: str | None = None) -> None:
		for fieldname, rows in children.items():
			child = child_doctype or self.child_doctype(doctype, fieldname)
			if not child or not frappe.db.table_exists(child):
				continue
			for row in rows:
				frappe.get_doc({**row, "doctype": child}).db_insert()

	@staticmethod
	def child_doctype(doctype: str, fieldname: str) -> str | None:
		df = frappe.get_meta(doctype).get_field(fieldname)
		return df.options if df else None

	@staticmethod
	def project_child_doctype(fieldname: str) -> str | None:
		return frappe.db.get_value("Custom Field", {"dt": "Project", "fieldname": fieldname}, "options")

	def restore_series(self) -> None:
		series = Table("tabSeries")
		for _, _, rows in self.read(("series",)):
			for name, data in rows:
				current = frappe.qb.from_(series).select(series.current).where(series.name == name).run()
				if not current:
					frappe.qb.into(series).columns("name", "current").insert(name, data["current"]).run()
				elif cint(current[0][0]) < cint(data["current"]):
					frappe.qb.update(series).set(series.current, data["current"]).where(
						series.name == name
					).run()
