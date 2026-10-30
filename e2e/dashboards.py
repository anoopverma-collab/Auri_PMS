"""Browser checks of the Auri PMS dashboards (Playwright, read-only).

Run from the bench folder; the bench must be running:

    SESSIONS=$(cd sites && ../env/bin/python ../apps/auri_pms/e2e/sessions.py standard-v16.local Administrator) \\
    SITE=standard-v16.local URL=http://localhost:8002 \\
    ADMIN=Administrator MANAGER=<a user with a manager role> DENIED=<a user with no managed project> \\
    python3 apps/auri_pms/e2e/dashboards.py

It logs in with a session id made by ``sessions.py``, passed in SESSIONS as its JSON output (no password is used) and only reads and clicks: no record is created or
changed. Screenshots go to ``e2e/screenshots``. Exit code 1 when a check fails.
"""

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[2]
SITE = os.environ.get("SITE", "standard-v16.local")
URL = os.environ.get("URL", "http://localhost:8002")
ADMIN = os.environ.get("ADMIN", "Administrator")
MANAGER = os.environ.get("MANAGER", "")
DENIED = os.environ.get("DENIED", "")
SHOTS = HERE / "screenshots"
SHOTS.mkdir(exist_ok=True)

results = []


def check(case, ok, detail=""):
	results.append((case, bool(ok), detail))
	print(f"{'PASS' if ok else 'FAIL'}  {case}{'  - ' + str(detail) if detail and not ok else ''}")


def sessions(users):
	"""The session ids printed by sessions.py, passed in SESSIONS as JSON (see the header)."""
	raw = os.environ.get("SESSIONS", "")
	if not raw.startswith("{"):
		sys.exit("Set SESSIONS to the output of sessions.py (see the header of this file)")
	sids = json.loads(raw)
	missing = [u for u in users if u not in sids]
	if missing:
		sys.exit(f"SESSIONS has no session for {', '.join(missing)}")
	return sids


def api(page, method, **args):
	return page.evaluate(
		"""async ([m, a]) => { const r = await fetch('/api/method/' + m, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': frappe.csrf_token}, body: JSON.stringify(a)}); return (await r.json()); }""",
		[method, args],
	)


class Session:
	def __init__(self, browser, sid, width=1400, height=900, dark=False):
		self.context = browser.new_context(
			viewport={"width": width, "height": height}, color_scheme="dark" if dark else "light"
		)
		self.context.add_cookies([{"name": "sid", "value": sid, "url": URL}])
		self.page = self.context.new_page()
		self.errors = []
		self.page.on("pageerror", lambda e: self.errors.append(str(e)))
		self.page.on(
			"console",
			lambda m: self.errors.append(m.text) if m.type == "error" and "favicon" not in m.text else None,
		)

	def open(self, route, ready=".hub-tile, .hub-panel"):
		self.page.goto(f"{URL}/desk/{route}")
		self.page.wait_for_selector(ready, timeout=30000)
		self.page.wait_for_timeout(600)

	def sidebar(self):
		return self.page.eval_on_selector_all(
			".sidebar-item-container .sidebar-item-label",
			"els => els.map(e => e.innerText.trim()).filter(Boolean)",
		)

	def close(self):
		self.context.close()


OPTIONS = '.page-form [data-fieldname="{f}"] ul[role=listbox] [role=option] p[title]'


def dropdown(session, fieldname):
	"""Open a Link field's dropdown and return the options it lists, as ``title | detail`` (the helper rows are left out)."""
	box = session.page.locator(f'.page-form [data-fieldname="{fieldname}"] input').first
	box.click()
	box.fill("")
	session.page.wait_for_timeout(1200)
	rows = session.page.eval_on_selector_all(
		OPTIONS.format(f=fieldname),
		"els => els.map(e => e.getAttribute('title') + ' | ' + (e.querySelector('span') ? e.querySelector('span').innerText : ''))",
	)
	return [r for r in rows if not r.startswith(("filter_description", "Create a new", "Advanced Search"))]


def pick(session, fieldname, text_contains):
	box = session.page.locator(f'.page-form [data-fieldname="{fieldname}"] input').first
	box.click()
	box.fill("")
	session.page.wait_for_timeout(1200)
	session.page.locator(OPTIONS.format(f=fieldname), has_text=text_contains).first.click()
	session.page.wait_for_timeout(1800)


def run():
	users = [u for u in (ADMIN, MANAGER, DENIED) if u]
	sids = sessions(users)
	with sync_playwright() as p:
		browser = p.chromium.launch()

		# ---------------------------------------------------------------- admin
		s = Session(browser, sids[ADMIN])
		page = s.page
		s.open("management-dashboard", ".hub-tile")
		check(
			"NAV-08 sidebar starts with Auri Insights, Delivery & Health, Client Status Report and lists no Project Hub or Quality Dashboard",
			s.sidebar()[:3] == ["Auri Insights", "Delivery & Health", "Client Status Report"]
			and "Project Hub" not in s.sidebar()
			and "Quality Dashboard" not in s.sidebar(),
			s.sidebar()[:5],
		)
		check("NAV-02 sidebar has no Portfolio entry", "Portfolio" not in s.sidebar(), s.sidebar())
		check("MD-00 dashboard opens without script errors", not s.errors, s.errors[:3])
		kpis = api(page, "auri_pms.auri_pms.api.get_management_dashboard")["message"]["kpis"]
		tiles = page.eval_on_selector_all(
			".hub-tile",
			"els => els.map(e => [e.querySelector('b').innerText, e.querySelector('span').innerText])",
		)
		tile = {label: value for value, label in tiles}
		check(
			"MD-01 tiles match the numbers from the server",
			tile.get("Total tasks") == str(kpis["tasks_total"])
			and tile.get("Total projects") == str(kpis["projects"])
			and tile.get("Overdue") == str(kpis["tasks_overdue"]),
			(tile, kpis),
		)
		check(
			"MD-10 every section is drawn",
			all(
				page.locator("text=" + t).count()
				for t in (
					"Project overview",
					"Release-wise tracking",
					"Sprint overview",
					"User-wise workload",
					"Delivery health",
				)
			),
		)
		page.screenshot(path=str(SHOTS / "management-delivery.png"), full_page=True)

		# hours: estimated vs actual vs billable, one row per project, equal to the server's numbers
		hours = api(page, "auri_pms.auri_pms.api.get_management_dashboard")["message"]["hours"]
		check(
			"MD-13 the hours section lists a row per project and a chart when there are hours",
			page.locator("text=Hours by project").count() == 1
			and page.locator(".hub-table", has_text="Billable of actual").locator("tbody tr").count()
			>= len(hours["projects"])
			and (
				(hours["total"]["estimated"] or hours["total"]["actual"]) == 0
				or page.locator("#md-hours svg").count() == 1
			),
		)
		first = hours["projects"][0]
		check(
			"MD-14 a project's hours equal the server's numbers",
			page.locator(".hub-table", has_text="Billable of actual")
			.locator("tbody tr")
			.first.inner_text()
			.replace("\n", " ")
			.count(f"{first['actual']:g}")
			>= 1,
			first,
		)

		# tile click opens the matching list
		page.locator(".hub-tile", has_text="Open tasks").click()
		page.wait_for_timeout(2500)
		check("MD-08 a tile opens the Work Item list", "/work-item" in page.url, page.url)
		s.open("management-dashboard", ".hub-tile")

		# every tile is a link, and the delivery-health tiles open a list with exactly their count
		dead = page.eval_on_selector_all(
			".hub-tile",
			"els => els.filter(e => !e.hasAttribute('data-go') && !e.hasAttribute('data-route')).map(e => e.innerText.replace(/\\n/g, ' / '))",
		)
		check("MD-11 every tile is clickable", not dead, dead)
		for label in ("Delayed projects", "Delayed releases", "Overdue sprints", "Pending activities"):
			s.open("management-dashboard", ".hub-tile")
			tile = page.locator(".hub-tile", has_text=label).first
			shown = int(tile.locator("b").inner_text())
			tile.click()
			page.wait_for_timeout(3500)
			count = page.evaluate("(document.querySelector('.list-count') || {}).innerText || ''")
			digits = [int(x) for x in "".join(c if c.isdigit() else " " for c in count).split()]
			rows = page.locator(".list-row-container, .result .list-row").count()
			check(
				f"MD-12 the {label} tile opens a list of {shown}",
				(digits and digits[-1] == shown) or rows == shown or (shown == 0 and rows <= 1),
				(count, rows, shown),
			)
		s.open("management-dashboard", ".hub-tile")

		# tabs
		page.locator(".md-tabs span", has_text="Health and cost").click()
		page.wait_for_selector(".pf", timeout=30000)
		page.wait_for_timeout(800)
		check(
			"MD-09 Health and cost tab shows the Portfolio view",
			page.locator(".pf .hub-tiles").count() > 0
			and page.locator(".md-tabs span.active", has_text="Health and cost").count() == 1,
		)
		check(
			"HC-06 health cards and the project table draw",
			page.locator(".pf-card").count() >= 1 and page.locator(".pf-projects").count() == 1,
		)
		page.screenshot(path=str(SHOTS / "management-health.png"), full_page=True)
		page.locator(".md-tabs span", has_text="Delivery").click()
		page.wait_for_selector(".md-sec", timeout=30000)
		check(
			"MD-09 back on the Delivery tab",
			page.locator(".md-sec").count() >= 5 and page.locator(".pf").count() == 0,
		)

		# filters: Project takes several projects; Release and Sprint follow the chosen ones
		def multi_open():
			page.keyboard.press("Escape")  # close any list that is still open
			page.mouse.click(700, 20)
			page.wait_for_timeout(300)
			page.locator('.page-form [data-fieldname="project"]').first.click()
			page.wait_for_timeout(700)

		def multi_items():
			return page.eval_on_selector_all(
				".multiselect-list .dropdown-menu li",
				"els => els.map(e => e.innerText.trim().replace(/\\n/g, ' / ')).filter(t => t && !t.startsWith('Select All'))",
			)

		def multi_toggle(text):
			page.locator(".multiselect-list .dropdown-menu li", has_text=text).first.click()
			page.wait_for_timeout(1800)

		def header():
			return page.locator(".hub-title").first.inner_text().replace("\n", " | ")

		managed = sorted(
			{
				p["name"]
				for p in api(page, "auri_pms.auri_pms.api.get_management_dashboard")["message"]["projects"]
			}
		)
		multi_open()
		offered = multi_items()
		check(
			"FLT-01 the Projects filter lists every managed Auri PMS project",
			len(offered) == len(managed) >= 1,
			(offered, managed),
		)
		all_releases = dropdown(s, "release")
		multi_open()
		multi_toggle(managed[0])
		check(
			"FLT-03 one project: the page follows it",
			"1 project" in header() and "Project: " in header(),
			header(),
		)
		multi_open()
		check(
			"FLT-04 the list still offers every project after one is chosen",
			len(multi_items()) == len(managed),
			multi_items(),
		)
		scoped_releases = dropdown(s, "release")
		check(
			"FLT-02 choosing a project narrows the Release dropdown",
			len(scoped_releases) <= len(all_releases),
			(all_releases, scoped_releases),
		)
		if len(managed) > 1:
			multi_open()
			multi_toggle(managed[1])
			check(
				"FLT-05 two projects: the page covers both",
				f"{len(managed[:2])} projects" in header() and "Projects: " in header(),
				header(),
			)
			two = api(
				page, "auri_pms.auri_pms.api.get_management_dashboard", project=json.dumps(managed[:2])
			)["message"]
			tile_total = int(
				page.locator(".hub-tile", has_text="Total tasks").first.locator("b").inner_text()
			)
			check(
				"FLT-06 the tiles add up the chosen projects",
				tile_total == two["kpis"]["tasks_total"],
				(tile_total, two["kpis"]["tasks_total"]),
			)
		page.keyboard.press("Escape")
		page.mouse.click(700, 20)
		if scoped_releases:
			pick(s, "release", scoped_releases[0].split(" | ")[0])
		page.wait_for_timeout(500)
		# a Health and cost tab opened with projects chosen focuses on them
		before = len(s.errors)
		page.locator(".md-tabs span", has_text="Health and cost").click()
		page.wait_for_selector(".pf", timeout=30000)
		page.wait_for_timeout(2500)
		check(
			"HC-10 opening Health and cost with a Release chosen raises no script errors (it used to reload twice)",
			len(s.errors) == before,
			s.errors[before : before + 2],
		)
		check(
			"HC-04 the chosen projects focus the health tab",
			page.locator(".pf-applied").count() == 1 or len(managed) <= 1,
			"no 'Showing only' bar",
		)
		page.locator("button:has-text('Clear filters')").first.click()
		page.wait_for_timeout(1800)
		release_sprint = [
			page.locator(f'.page-form [data-fieldname="{f}"] input').first.input_value()
			for f in ("release", "sprint")
		]
		chosen_left = page.locator('.page-form [data-fieldname="project"]').first.inner_text().strip()
		check(
			"FLT-13 Clear filters empties Projects, Release and Sprint",
			release_sprint == ["", ""]
			and "SJDM" not in chosen_left
			and "TST" not in chosen_left
			and "PROJ" not in chosen_left,
			(release_sprint, chosen_left),
		)
		page.screenshot(path=str(SHOTS / "management-filters.png"))

		# old route
		page.goto(f"{URL}/desk/portfolio")
		page.wait_for_selector(".md-tabs", timeout=30000)
		page.wait_for_timeout(800)
		check(
			"HC-07 /desk/portfolio opens the Health and cost tab",
			"management-dashboard" in page.url
			and page.locator(".md-tabs span.active", has_text="Health and cost").count() == 1,
			page.url,
		)

		# project hub button
		s.open("project-hub")
		page.locator("button:has-text('Delivery & Health')").first.click()
		page.wait_for_timeout(2500)
		check(
			"HC-08 the Project Hub button opens Delivery & Health",
			"management-dashboard" in page.url,
			page.url,
		)

		# Auri Insights: the dropdown offers the allocated Auri PMS projects only
		s.open("pms-insights", ".ins-hero, .hub-panel, .ins-card")
		offered = dropdown(s, "project")
		allocated = api(page, "auri_pms.auri_pms.insights.get_insight_projects")["message"]
		check(
			"INS-01 the Auri Insights dropdown lists the allocated Auri PMS projects only",
			len(offered) == len(allocated) and len(allocated) >= 1,
			(offered, allocated),
		)
		page.keyboard.press("Escape")

		# Client Status Report: the Project dropdown too
		s.open("status-report", ".hub-panel, .hub-tile")
		offered = dropdown(s, "project")
		check(
			"SR-01 the Client Status Report dropdown lists only Auri PMS projects",
			len(offered) == len(allocated) and len(allocated) >= 1,
			(offered, allocated),
		)
		page.keyboard.press("Escape")

		# quality dashboard
		s.open("quality-dashboard")
		listed = dropdown(s, "project")
		pms = {
			r["name"]
			for r in api(
				page,
				"frappe.client.get_list",
				doctype="Project",
				filters={"pms_enabled": 1},
				limit_page_length=0,
			)["message"]
		}
		all_projects = {
			r["name"]
			for r in api(page, "frappe.client.get_list", doctype="Project", limit_page_length=0)["message"]
		}
		check(
			"QD-10 the Quality Dashboard dropdown lists only Auri PMS projects",
			len(listed) == len(pms) and len(pms) <= len(all_projects),
			(listed, pms),
		)
		page.keyboard.press("Escape")
		check(
			"QD-00 Quality Dashboard shows its tiles or its empty note",
			page.locator(".hub-tile, .hub-panel").count() > 0,
		)
		page.screenshot(path=str(SHOTS / "quality.png"), full_page=True)
		check("QD-13 no script errors on Hub, Quality and Dashboard", not s.errors, s.errors[:3])
		s.close()

		# ---------------------------------------------------------------- looks: dark and phone
		d = Session(browser, sids[ADMIN], dark=True)
		d.open("management-dashboard", ".hub-tile")
		d.page.screenshot(path=str(SHOTS / "management-dark.png"))
		check("UI-01 dark mode renders the dashboard", d.page.locator(".hub-tile").count() > 0)
		d.close()
		m = Session(browser, sids[ADMIN], width=390, height=800)
		m.open("management-dashboard", ".hub-tile")
		wide = m.page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
		m.page.screenshot(path=str(SHOTS / "management-phone.png"), full_page=True)
		check("UI-02 phone width: the page does not scroll sideways", wide <= 4, f"{wide}px overflow")
		m.close()

		# ---------------------------------------------------------------- manager and denied user
		if MANAGER:
			g = Session(browser, sids[MANAGER])
			g.open("management-dashboard", ".hub-tile, .hub-panel")
			check(
				"ACC-01 a manager opens the dashboard",
				g.page.locator(".md-tabs").count() == 1
				or g.page.locator("text=for Auri PMS Admins").count() == 0,
			)
			g.close()
		if DENIED:
			x = Session(browser, sids[DENIED])
			x.open("management-dashboard", ".hub-panel")
			check(
				"ACC-02 a user with no managed project is told it is not for them",
				x.page.locator("text=is for Auri PMS Admins").count() == 1
				and x.page.locator(".hub-tile").count() == 0,
			)
			check(
				"ACC-04 the sidebar entry is hidden for that user",
				"Delivery & Health" not in x.sidebar(),
				x.sidebar()[:6],
			)
			x.page.screenshot(path=str(SHOTS / "denied.png"))
			x.close()
		browser.close()

	failed = [r for r in results if not r[1]]
	print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
	sys.exit(1 if failed else 0)


if __name__ == "__main__":
	run()
