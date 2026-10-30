"""Print a logged-in session id for each user given on the command line (run with the bench env python, from the sites folder).

    ../env/bin/python e2e/sessions.py standard-v16.local Administrator user@example.com

Creates an ordinary Sessions row per user, as a login would; no password is read or changed.
"""

import json
import sys

import frappe
import frappe.auth

site, users = sys.argv[1], sys.argv[2:]
from frappe.app import Request
from werkzeug.test import EnvironBuilder

frappe.init(site=site)
frappe.connect()
frappe.local.request = Request(EnvironBuilder(path="/").get_environ())
frappe.local.request_ip = "127.0.0.1"
frappe.local.cookie_manager = frappe.auth.CookieManager()
frappe.local.response = frappe._dict()
out = {}
for user in users:
	frappe.set_user("Administrator")
	frappe.local.login_manager = frappe.auth.LoginManager()
	frappe.local.login_manager.login_as(user)
	out[user] = frappe.session.sid
# a separate script run, not a request; the session rows must be saved for the browser to use them
frappe.db.commit()  # nosemgrep
print(json.dumps(out))
