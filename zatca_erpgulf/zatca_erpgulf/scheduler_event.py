"""this file is used to schedule the background job for submitting invoices to ZATCA"""

import frappe
from frappe.utils import now_datetime, add_to_date
from zatca_erpgulf.zatca_erpgulf.sign_invoice import zatca_background_on_submit

# frappe.init(site="zatca.erpgulf.com")
# frappe.connect()


def submit_invoices_to_zatca_background_process():
    """
    in every 10 minutes if 'custom_send_invoice_to_zatca'set to 'background' in setting.
    Fetches all Sales Invoices from the past 48 hours that are either:
    - Draft (`docstatus=0`) or Submitted (`docstatus=1`)
    - OR `custom_zatca_status="Not Submitted"`
    - Sends them to ZATCA
    """
    try:
        current_time = now_datetime()
        past_48_hours_time = add_to_date(current_time, hours=-48)
        # print("past_48_hours_time", past_48_hours_time)
        not_submitted_invoices = frappe.get_all(
            "Sales Invoice",
            filters=[
                ["creation", ">=", past_48_hours_time],  # Created in last 48 hours
                ["docstatus", "in", [0, 1]],  # Draft or Submitted
                [
                    "custom_zatca_status",
                    "=",
                    "Not Submitted",
                ],  # OR Not Submitted to ZATCA
            ],
            fields=["name", "docstatus", "custom_zatca_status", "company"],
        )
        print("🔹 Invoices found:", not_submitted_invoices)

        #
        if not not_submitted_invoices:
            # print("No invoices match the filter conditions.")
            frappe.log_error(
                "No pending invoices found for ZATCA submission in the last 48 hours.",
                "ZATCA Background Job",
            )
            return

        for invoice in not_submitted_invoices:
            sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice["name"])
            company_doc = frappe.get_doc("Company", sales_invoice_doc.company)
            if company_doc.custom_send_invoice_to_zatca != "Background":
                frappe.log_error(
                    f"Skipping {sales_invoice_doc.name}: Company '{company_doc.name}' "
                    "does not have 'background' mode enabled.",
                    "ZATCA Background Job",
                )
                continue  # Skip this invoice

            if sales_invoice_doc.docstatus == 1:
                zatca_background_on_submit(sales_invoice_doc)
                frappe.log_error(
                    f"Processed {sales_invoice_doc.name}: Sent to ZATCA.",
                    "ZATCA Background Job",
                )
            else:
                sales_invoice_doc.submit()
                frappe.log_error(
                    f"Submitted {sales_invoice_doc.name} before sending to ZATCA.",
                    "ZATCA Background Job",
                )

        frappe.log_error(
            f"Processed {len(not_submitted_invoices)} invoices for ZATCA submission.",
            "ZATCA Background Job",
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "ZATCA Background Job Error")
