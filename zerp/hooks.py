app_name = "zerp"
app_title = "Zerp"
app_publisher = "vt"
app_description = "saas"
app_email = "islammoustafa86@outlook.com"
app_license = "mit"

# Website Settings
website_route_rules = [
    {"from_route": "/cshome", "to_route": "cshome"},  # Set as home page
    {"from_route": "/subscription", "to_route": "subscription"},
    {"from_route": "/subscription/register", "to_route": "subscription/register"},
    {"from_route": "/subscription/plans", "to_route": "subscription/plans"},
    {"from_route": "/subscribe", "to_route": "subscribe"},  # New route for subscription signup
    {"from_route": "/my_subscriptions", "to_route": "my_subscriptions"}  # Subscription list page
]

# Export Web Forms
fixtures = [
    {
        "dt": "Web Form",
        "filters": [
            ["module", "=", "Zerp"]
        ]
    },
    {
        "dt": "Web Page",
        "filters": [
            ["module", "=", "Zerp"]
        ]
    },
    {
        "dt": "Website Settings",
        "filters": [
            ["name", "=", "Website Settings"]
        ]
    },
    {
        "dt": "Website Theme",
        "filters": [
            ["name", "=", "Standard"]
        ]
    },
    {
        "dt": "Website Script",
        "filters": [
            ["name", "=", "Website Script"]
        ]
    },
    {
        "dt": "Website Sidebar",
        "filters": [
            ["module", "=", "Zerp"]
        ]
    },
    {
        "dt": "Workspace",
        "filters": [
            ["module", "=", "Zerp"]
        ]
    },
    {
        "dt": "Portal Settings",
        "filters": [
            ["name", "=", "Portal Settings"]
        ]
    }
]

# Web Forms Export
webform_export = [
    "Subscription Registration",
    "Subscription Plan Selection"
]

# Web Pages Export
webpage_export = [
    "subscription",
    "subscription/register",
    "subscription/plans",
    "subscription/success",
    "subscription/error",
    "subscribe"  # New route for subscription signup
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "zerp",
# 		"logo": "/assets/zerp/logo.png",
# 		"title": "Zerp",
# 		"route": "/zerp",
# 		"has_permission": "zerp.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/zerp/css/zerp.css"
# app_include_js = "/assets/zerp/js/zerp.js"

# include js, css files in header of web template
# web_include_css = "/assets/zerp/css/zerp.css"
# web_include_js = "/assets/zerp/js/zerp.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "zerp/public/scss/website"

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
# app_include_icons = "zerp/public/icons.svg"

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
# 	"methods": "zerp.utils.jinja_methods",
# 	"filters": "zerp.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "zerp.custom_fields.setup_custom_fields"
after_install = "zerp.custom_fields.setup_custom_fields"

# Uninstallation
# ------------

# before_uninstall = "zerp.uninstall.before_uninstall"
# after_uninstall = "zerp.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "zerp.utils.before_app_install"
# after_app_install = "zerp.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "zerp.utils.before_app_uninstall"
# after_app_uninstall = "zerp.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "zerp.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
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
# 		"zerp.tasks.all"
# 	],
# 	"daily": [
# 		"zerp.tasks.daily"
# 	],
# 	"hourly": [
# 		"zerp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"zerp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"zerp.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "zerp.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "zerp.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "zerp.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["zerp.utils.before_request"]
# after_request = ["zerp.utils.after_request"]

# Job Events
# ----------
# before_job = ["zerp.utils.before_job"]
# after_job = ["zerp.utils.after_job"]

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
# 	"zerp.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

