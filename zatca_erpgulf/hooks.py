app_name = "zatca_erpgulf"
app_title = "Zatca Erpgulf"
app_publisher = "ERPGulf"
app_description = "Implementaiton of Saudi E-Invoicing Phase-2 on Frappe ERPNext"
app_email = "support@ERPGulf.com"
app_license = "mit"
app_home = "/app/zatca-erpgulf"

from frappe import _

from . import __version__ as app_version

add_to_apps_screen = [
    {
        "name": app_name,
        "logo": "/assets/zatca_erpgulf/images/ERPGulf.png",
        "title": app_title,
        "route": "/app/zatca-erpgulf",  # <-- add leading /app/
    }
]


scheduler_events = {
    "cron": {
        "*/30 * * * *": [
            "zatca_erpgulf.zatca_erpgulf.scheduler_event.submit_invoices_to_zatca_background_process"
        ]
    }
}


doc_events = {
    "Sales Invoice": {
        # "before_insert":"zatca_erpgulf.zatca_erpgulf.sales_invoice_hooks.set_draft_series",
        "before_cancel": "zatca_erpgulf.zatca_erpgulf.validations.before_save",
        "before_submit": "zatca_erpgulf.zatca_erpgulf.tax_error.validate_sales_invoice_taxes",
        "after_insert": "zatca_erpgulf.zatca_erpgulf.validations.duplicating_invoice",
        "on_submit": [
            # "zatca_erpgulf.zatca_erpgulf.sales_invoice_hooks.rename_invoice_on_submit",
             "zatca_erpgulf.zatca_erpgulf.sign_invoice.zatca_background_on_submit"
            ]
    },
    "POS Invoice": {
        "before_cancel": "zatca_erpgulf.zatca_erpgulf.validations.before_save",
        "before_submit": "zatca_erpgulf.zatca_erpgulf.tax_error.validate_sales_invoice_taxes",
        "after_insert": "zatca_erpgulf.zatca_erpgulf.validations.duplicating_invoice",
        "on_submit": "zatca_erpgulf.zatca_erpgulf.pos_sign.zatca_background_on_submit",
    },
}




jinja = {
    "methods": [
        "zatca_erpgulf.zatca_erpgulf.utils.arabic_money_in_words",
        "zatca_erpgulf.zatca_erpgulf.utils.arabic_number"
    ]
}

doctype_js = {
    "Sales Invoice": [
        # "public/js/draft.js",
        "public/js/our_sales_invoice.js",
        "public/js/print.js",
        "public/js/badge.js"
       
    ],
    "Company": "public/js/company.js",
    "POS Invoice": ["public/js/our_pos_invoice.js", "public/js/badge_pos.js"],
}

doctype_list_js = {
    "Sales Invoice": "public/js/resubmit.js",
    "POS Invoice": "public/js/resubmitpos.js",
}


app_include_css = "/assets/zatca_erpgulf/css/tooltip.css"
app_include_js = "/assets/zatca_erpgulf/js/tooltip.js"

fixtures = [
    {
        "dt": "Desktop Icon",
        "filters": [["label", "=", "ZATCA ERPGulf"]]
    },
    {"dt": "Custom Field", "filters": [["module", "=", "Zatca Erpgulf"]]},
]