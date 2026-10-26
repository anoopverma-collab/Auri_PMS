app_name = "auri_pms"
app_title = "Auri PMS"
app_publisher = "Anoop Verma"
app_description = "Auri PMS (Project Management System). A centralized platform for project planning, task management, timelines, effort tracking, team collaboration, and delivery monitoring. Suitable for projects, tasks, milestones, timesheets, estimates versus actuals, and management dashboards, with risk tracking, project health status and client status reports (configurable layouts, sections and email defaults, PDF and delivery tracking)."
app_email = "anoop.verma@aurigait.com"
app_license = "mit"
app_logo_url = "/assets/auri_pms/images/auri-pms-icon-256.png"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "auri_pms",
# 		"logo": "/assets/auri_pms/logo.png",
# 		"title": "Auri PMS",
# 		"route": "/auri_pms",
# 		"has_permission": "auri_pms.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "auri_pms.bundle.css"
# app_include_js = "/assets/auri_pms/js/auri_pms.js"

# include js, css files in header of web template
# web_include_css = "auri_pms.bundle.css"
# web_include_js = "/assets/auri_pms/js/auri_pms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "auri_pms/public/scss/website"

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
# app_include_icons = "auri_pms/public/icons.svg"

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
# 	"methods": "auri_pms.utils.jinja_methods",
# 	"filters": "auri_pms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "auri_pms.install.before_install"
# after_install = "auri_pms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "auri_pms.uninstall.before_uninstall"
# after_uninstall = "auri_pms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "auri_pms.utils.before_app_install"
# after_app_install = "auri_pms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "auri_pms.utils.before_app_uninstall"
# after_app_uninstall = "auri_pms.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "auri_pms.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "auri_pms.notifications.get_notification_config"

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
# 		"auri_pms.tasks.all"
# 	],
# 	"daily": [
# 		"auri_pms.tasks.daily"
# 	],
# 	"hourly": [
# 		"auri_pms.tasks.hourly"
# 	],
# 	"weekly": [
# 		"auri_pms.tasks.weekly"
# 	],
# 	"monthly": [
# 		"auri_pms.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "auri_pms.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "auri_pms.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "auri_pms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "auri_pms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["auri_pms.utils.before_request"]
# after_request = ["auri_pms.utils.after_request"]

# Job Events
# ----------
# before_job = ["auri_pms.utils.before_job"]
# after_job = ["auri_pms.utils.after_job"]

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
# 	"auri_pms.auth.validate"
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
after_install = "auri_pms.install.after_install"
after_migrate = ["auri_pms.install.after_migrate"]
before_uninstall = "auri_pms.install.before_uninstall"

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Auri PMS"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Auri PMS"]]},
	{"dt": "Role", "filters": [["name", "in", ["Auri PMS Admin", "Auri PMS Manager", "Auri PMS User"]]]},
	{"dt": "Notification", "filters": [["module", "=", "Auri PMS"]]},
]

doc_events = {
	"Project": {
		"validate": "auri_pms.auri_pms.project_hooks.validate",
		"on_update": "auri_pms.auri_pms.project_hooks.on_update",
		"on_trash": "auri_pms.auri_pms.project_hooks.on_trash",
	},
	"User": {"on_update": "auri_pms.auri_pms.utils.clear_cache"},
	"ToDo": {"validate": "auri_pms.auri_pms.doctype.work_item.work_item.validate_todo"},
	"Communication": {"after_insert": "auri_pms.auri_pms.email_intake.on_communication"},
}

permission_query_conditions = {
	"Project": "auri_pms.permissions.project_query",
	"Work Item": "auri_pms.permissions.work_item_query",
	"Release": "auri_pms.permissions.release_query",
	"Risk Register": "auri_pms.permissions.risk_register_query",
	"Sprint": "auri_pms.permissions.sprint_query",
	"Project Status Report": "auri_pms.permissions.status_report_query",
	"Time Entry": "auri_pms.permissions.time_entry_query",
	"Work Item Category": "auri_pms.permissions.category_query",
	"Project Module": "auri_pms.permissions.project_module_query",
}

has_permission = {
	"Project": "auri_pms.permissions.project_has_permission",
	"Work Item": "auri_pms.permissions.work_item_has_permission",
	"Release": "auri_pms.permissions.release_has_permission",
	"Risk Register": "auri_pms.permissions.risk_register_has_permission",
	"Sprint": "auri_pms.permissions.sprint_has_permission",
	"Project Status Report": "auri_pms.permissions.status_report_has_permission",
	"Time Entry": "auri_pms.permissions.time_entry_has_permission",
	"Work Item Category": "auri_pms.permissions.category_has_permission",
	"Project Module": "auri_pms.permissions.project_module_has_permission",
}

override_doctype_dashboards = {
	"Project": ["auri_pms.auri_pms.project_hooks.get_dashboard_data"],
	"Work Item": ["auri_pms.auri_pms.doctype.work_item.work_item.get_dashboard_data"],
}

scheduler_events = {
	"hourly": [
		"auri_pms.auri_pms.doctype.project_status_report.project_status_report.refresh_pending_statuses"
	],
	"daily": [
		"auri_pms.auri_pms.tasks.send_due_digests",
		"auri_pms.auri_pms.status_report.send_scheduled_reports",
		"auri_pms.auri_pms.snapshots.weekly",
		"auri_pms.auri_pms.snapshots.monthly",
	],
}

global_search_doctypes = {"Default": [{"doctype": "Work Item", "index": 30}]}

app_include_js = "auri_pms.bundle.js"

boot_session = "auri_pms.auri_pms.boot.boot_session"

doctype_js = {"Project": "public/js/project.js"}
