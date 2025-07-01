app_name = "zatca_erpgulf"
app_title = "Zatca Erpgulf"
app_publisher = "ERPGulf"
app_description = "Implementaiton of Saudi E-Invoicing Phase-2 on Frappe ERPNext"
app_email = "support@ERPGulf.com"
app_license = "mit"

from frappe import _

from . import __version__ as app_version


# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/zatca_erpgulf/css/zatca_erpgulf.css"
# app_include_js = "/assets/zatca_erpgulf/js/zatca_erpgulf.js"

# include js, css files in header of web template
# web_include_css = "/assets/zatca_erpgulf/css/zatca_erpgulf.css"
# web_include_js = "/assets/zatca_erpgulf/js/zatca_erpgulf.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "zatca_erpgulf/public/scss/website"

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

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "zatca_erpgulf.utils.jinja_methods",
# 	"filters": "zatca_erpgulf.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "zatca_erpgulf.install.before_install"
# after_install = "zatca_erpgulf.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "zatca_erpgulf.uninstall.before_uninstall"
# after_uninstall = "zatca_erpgulf.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "zatca_erpgulf.utils.before_app_install"
# after_app_install = "zatca_erpgulf.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "zatca_erpgulf.utils.before_app_uninstall"
# after_app_uninstall = "zatca_erpgulf.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "zatca_erpgulf.notifications.get_notification_config"

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
# 		"zatca_erpgulf.tasks.all"
# 	],
# 	"daily": [
# 		"zatca_erpgulf.tasks.daily"
# 	],
# 	"hourly": [
# 		"zatca_erpgulf.tasks.hourly"
# 	],
# 	"weekly": [
# 		"zatca_erpgulf.tasks.weekly"
# 	],
# 	"monthly": [
# 		"zatca_erpgulf.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "zatca_erpgulf.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "zatca_erpgulf.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "zatca_erpgulf.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["zatca_erpgulf.utils.before_request"]
# after_request = ["zatca_erpgulf.utils.after_request"]

# Job Events
# ----------
# before_job = ["zatca_erpgulf.utils.before_job"]
# after_job = ["zatca_erpgulf.utils.after_job"]

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
# 	"zatca_erpgulf.auth.validate"
# ]

# schedule for every 10 minutes every day 24 hours
scheduler_events = {
    "cron": {
        "*/10 * * * *": [
            "zatca_erpgulf.zatca_erpgulf.scheduler_event.submit_invoices_to_zatca_background_process"
        ]
    }
}


# # schdule for every 10 minutes from 1 am to 7 am
# scheduler_events = {
#     "cron": {
#         "*/10 1-7 * * * ": [
#             "zatca_erpgulf.zatca_erpgulf.scheduler_event.submit_invoices_to_zatca_background_process"
#         ]
#     }
# }

doc_events = {
    "Sales Invoice": {
        "before_cancel": "zatca_erpgulf.zatca_erpgulf.validations.before_save",
        "before_submit": "zatca_erpgulf.zatca_erpgulf.tax_error.validate_sales_invoice_taxes",
        "after_insert": "zatca_erpgulf.zatca_erpgulf.validations.duplicating_invoice",
        "on_submit": "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_background_on_submit",
    },
    "POS Invoice": {
        "before_cancel": "zatca_erpgulf.zatca_erpgulf.validations.before_save",
        "before_submit": "zatca_erpgulf.zatca_erpgulf.tax_error.validate_sales_invoice_taxes",
        "after_insert": "zatca_erpgulf.zatca_erpgulf.validations.duplicating_invoice",
        "on_submit": "zatca_erpgulf.zatca_erpgulf.pos_sign.zatca_background_on_submit",
    },
}
doctype_js = {
    "Sales Invoice": [
        "public/js/our_sales_invoice.js",
        "public/js/print.js",
        "public/js/badge.js",
    ],
    "Company": "public/js/company.js",
    "POS Invoice": ["public/js/our_pos_invoice.js", "public/js/badge_pos.js"],
}

doctype_list_js = {
    "Sales Invoice": "public/js/resubmit.js",
    "POS Invoice": "public/js/resubmitpos.js",
}


# fixtures = [ {"dt": "Custom Field","filters": [["module", "=", "Zatca Erpgulf"]] }]
fixtures = [
    {
        "dt": "Number Card",
        "filters": [
            [
                "name",
                "in",
                [
                    "Cleared This Month",
                    "Not Submitted This Month",
                    "Reported This Month",
                    "503 Service Unavailable This Month",
                ],
            ]
        ],
    },
    {
        "dt": "Dashboard Chart",
        "filters": [["name", "=", "Monthly Invoices Reported to ZATCA"]],
    },
    {"dt": "Dashboard", "filters": [["name", "=", "ZATCA Dashboard"]]},
    {
        "dt": "Workspace",
        "filters": [["name", "=", "ZATCA ERPGulf"]],  # Use actual Workspace name here
    },
    {"dt": "Workspace", "filters": {"module": "Zatca Erpgulf"}},
    {"dt": "Custom Field", "filters": [["module", "=", "Zatca Erpgulf"]]},
    {"dt": "Report", "filters": {"module": "Zatca Erpgulf"}},
    {
        "dt": "Report",
        "filters": [
            [
                "name",
                "in",
                [
                    "Item-wise Sales Register",
                    "Item-wise Purchase Register",
                    "Zatca Status Report",
                ],
            ]
        ],
    },
    # {"dt": "Page", "filters": [["name", "in", ["setup-zatca-phase-2"]]]},
    {"dt": "Page", "filters": {"module": "Zatca Erpgulf"}},
]

app_include_css = "/assets/zatca_erpgulf/css/tooltip.css"
app_include_js = "/assets/zatca_erpgulf/js/tooltip.js"
