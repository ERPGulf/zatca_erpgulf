"""this file is used to schedule the background job for submitting invoices to ZATCA"""

from datetime import datetime, timedelta, time
from frappe.utils import now_datetime, add_to_date
import frappe
from zatca_erpgulf.zatca_erpgulf.sign_invoice import zatca_background_on_submit


# frappe.init(site="zatca.erpgulf.com")
# frappe.connect()


def convert_to_time(time_value):
    """Convert timedelta or string to datetime.time object."""
    if isinstance(time_value, str):  # If it's a string, convert it
        return datetime.strptime(time_value, "%H:%M:%S").time()
    elif isinstance(time_value, timedelta):  # Convert timedelta to time
        return (datetime.min + time_value).time()
    elif isinstance(time_value, time):  # Already a time object
        return time_value
    else:
        raise ValueError(f"Unsupported time format: {time_value} ({type(time_value)})")


def submit_invoices_to_zatca_background_process():
    """submit_invoices_to_zatca_background_process."""
    try:
        current_time = now_datetime()
        past_24_hours_time = add_to_date(current_time, hours=-24)

        not_submitted_invoices = frappe.get_all(
            "Sales Invoice",
            filters=[
                ["creation", ">=", past_24_hours_time],
                ["docstatus", "in", [0, 1]],
                ["custom_zatca_status", "=", "Not Submitted"],
            ],
            fields=["name", "docstatus", "custom_zatca_status", "company"],
        )

        # print("🔹 Invoices found:", not_submitted_invoices)
        if not not_submitted_invoices:
            frappe.log_error(
                "No pending invoices found for ZATCA submission in the last 48 hours.",
                "ZATCA Background Job",
            )
            return

        for invoice in not_submitted_invoices:
            sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice["name"])
            company_doc = frappe.get_doc("Company", sales_invoice_doc.company)
            start_time = convert_to_time(company_doc.custom_start_time)
            end_time = convert_to_time(company_doc.custom_end_time)
            formatted_time = current_time.time()
            if start_time <= end_time:  # Normal case
                in_range = start_time <= formatted_time <= end_time
            else:  # Midnight case (e.g., 23:00 - 05:00)
                in_range = start_time <= formatted_time or formatted_time <= end_time

            if not in_range:
                frappe.log_error(
                    f"Skipping {sales_invoice_doc.name}: Current time {formatted_time} "
                    f"is outside the allowed range ({start_time} - {end_time}).",
                    "ZATCA Background Job",
                )
                continue  # Skip this invoice

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
