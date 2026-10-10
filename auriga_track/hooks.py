app_name = "auriga_track"
app_title = "Auri PMS"
app_publisher = "Anoop Verma"
app_description = "Auri PMS (Project Management System). Plan. Track. Deliver. A centralized platform for project planning, task management, timelines, effort tracking, team collaboration, and delivery monitoring. Suitable for projects, tasks, milestones, timesheets, estimates versus actuals, and management dashboards."
app_email = "anoop.verma@aurigait.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "auriga_track",
# 		"logo": "/assets/auriga_track/logo.png",
# 		"title": "Auri PMS",
# 		"route": "/auriga_track",
# 		"has_permission": "auriga_track.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/auriga_track/css/auriga_track.css"
# app_include_js = "/assets/auriga_track/js/auriga_track.js"

# include js, css files in header of web template
# web_include_css = "/assets/auriga_track/css/auriga_track.css"
# web_include_js = "/assets/auriga_track/js/auriga_track.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "auriga_track/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "auriga_track/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "auriga_track.utils.jinja_methods",
# 	"filters": "auriga_track.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "auriga_track.install.before_install"
# after_install = "auriga_track.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "auriga_track.uninstall.before_uninstall"
# after_uninstall = "auriga_track.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "auriga_track.utils.before_app_install"
# after_app_install = "auriga_track.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "auriga_track.utils.before_app_uninstall"
# after_app_uninstall = "auriga_track.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "auriga_track.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "auriga_track.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"auriga_track.tasks.all"
# 	],
# 	"daily": [
# 		"auriga_track.tasks.daily"
# 	],
# 	"hourly": [
# 		"auriga_track.tasks.hourly"
# 	],
# 	"weekly": [
# 		"auriga_track.tasks.weekly"
# 	],
# 	"monthly": [
# 		"auriga_track.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "auriga_track.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "auriga_track.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "auriga_track.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "auriga_track.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["auriga_track.utils.before_request"]
# after_request = ["auriga_track.utils.after_request"]

# Job Events
# ----------
# before_job = ["auriga_track.utils.before_job"]
# after_job = ["auriga_track.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"auriga_track.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# ---------------------------------------------------------------------------
# Auri PMS configuration
# ---------------------------------------------------------------------------
after_install = "auriga_track.install.after_install"
after_migrate = ["auriga_track.install.after_migrate"]
before_uninstall = "auriga_track.install.before_uninstall"

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Tracking"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Tracking"]]},
	{"dt": "Role", "filters": [["name", "in", ["Tracker Manager", "Tracker User"]]]},
	{"dt": "Notification", "filters": [["module", "=", "Tracking"]]},
]

doc_events = {
	"Project": {
		"validate": "auriga_track.tracking.project_hooks.validate",
		"on_update": "auriga_track.tracking.project_hooks.on_update",
		"on_trash": "auriga_track.tracking.project_hooks.on_trash",
	},
	"User": {"on_update": "auriga_track.tracking.utils.clear_cache"},
	"ToDo": {"validate": "auriga_track.tracking.doctype.work_item.work_item.validate_todo"},
	"Communication": {"after_insert": "auriga_track.tracking.email_intake.on_communication"},
}

permission_query_conditions = {
	"Project": "auriga_track.permissions.project_query",
	"Work Item": "auriga_track.permissions.work_item_query",
	"Release": "auriga_track.permissions.release_query",
	"Sprint": "auriga_track.permissions.sprint_query",
	"Project Status Report": "auriga_track.permissions.status_report_query",
	"Time Entry": "auriga_track.permissions.time_entry_query",
	"Work Item Category": "auriga_track.permissions.category_query",
}

has_permission = {
	"Project": "auriga_track.permissions.project_has_permission",
	"Work Item": "auriga_track.permissions.work_item_has_permission",
	"Release": "auriga_track.permissions.release_has_permission",
	"Sprint": "auriga_track.permissions.sprint_has_permission",
	"Project Status Report": "auriga_track.permissions.status_report_has_permission",
	"Time Entry": "auriga_track.permissions.time_entry_has_permission",
	"Work Item Category": "auriga_track.permissions.category_has_permission",
}

override_doctype_dashboards = {"Project": ["auriga_track.tracking.project_hooks.get_dashboard_data"]}

scheduler_events = {
	"daily": [
		"auriga_track.tracking.tasks.send_due_digests",
		"auriga_track.tracking.status_report.send_scheduled_reports",
	]
}

global_search_doctypes = {"Default": [{"doctype": "Work Item", "index": 30}]}

app_include_js = "auriga_track.bundle.js"

doctype_js = {"Project": "public/js/project.js"}
