"""this file is used to schedule the background job for submitting invoices to ZATCA"""

from datetime import datetime, timedelta, time
from frappe.utils import now_datetime, add_to_date
import frappe
from zatca_erpgulf.zatca_erpgulf.sign_invoice import zatca_background_on_submit


# frappe.init(site="zatca.erpgulf.com")
# frappe.connect()


def convert_to_time(time_value):
    """Convert timedelta or string to datetime.time object."""
    if isinstance(time_value, str):
        return datetime.strptime(time_value, "%H:%M:%S").time()
    elif isinstance(time_value, timedelta):
        return (datetime.min + time_value).time()
    elif isinstance(time_value, time):
        return time_value
    else:
        raise ValueError(f"Unsupported time format: {time_value} ({type(time_value)})")


def is_time_in_range(start_time, end_time, current_time):
    """Check if the current time is within the allowed range."""
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return start_time <= current_time or current_time <= end_time


def submit_invoices_to_zatca_background_process():
    """Submit invoices to ZATCA only if at least one company falls within the time range."""
    try:
        current_time = now_datetime().time()
        companies = frappe.get_all(
            "Company",
            fields=[
                "name",
                "custom_start_time",
                "custom_end_time",
                "custom_send_invoice_to_zatca",
            ],
        )

        any_company_in_range = False
        for company in companies:
            if not company.custom_start_time or not company.custom_end_time:
                continue

            start_time = convert_to_time(company.custom_start_time)
            end_time = convert_to_time(company.custom_end_time)

            if (
                is_time_in_range(start_time, end_time, current_time)
                and company.custom_send_invoice_to_zatca == "Background"
            ):
                any_company_in_range = True
                break

        if not any_company_in_range:
            # frappe.log_error(
            #     "No companies found with valid submission time.", "ZATCA Background Job"
            # )
            pass
            return

        past_24_hours_time = add_to_date(now_datetime(), hours=-24)

        not_submitted_invoices = frappe.get_all(
            "Sales Invoice",
            filters=[
                ["creation", ">=", past_24_hours_time],
                ["docstatus", "in", [0, 1]],
                ["custom_zatca_status", "=", "Not Submitted"],
            ],
            fields=["name", "docstatus", "company"],
        )

        if not not_submitted_invoices:
            frappe.log_error(
                "No pending invoices found for ZATCA submission.",
                "ZATCA Background Job",
            )
            return

        for invoice in not_submitted_invoices:
            sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice["name"])
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
