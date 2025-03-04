"""this file is used to schedule the background job for submitting invoices to ZATCA"""

from datetime import datetime, timedelta, time
import frappe
from frappe.utils import now_datetime, add_to_date

from zatca_erpgulf.zatca_erpgulf.pos_sign import zatca_background_on_submit


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


def submit_posinvoices_to_zatca_background_process():
    """Submit invoices to ZATCA only if at least one company falls within the time range."""
    try:
        current_time = now_datetime().time()
        companies = frappe.get_all(
            "Company",
            fields=[
                "name",
                "custom_start_time",
                "custom_end_time",
                "custom_start_time_session",
                "custom_end_time_session",
                "custom_send_invoice_to_zatca",
            ],
        )
        # print(f"companies: {companies}", "ZATCA Background Job")
        for company in companies:
            start_time = None
            end_time = None

            if company.custom_start_time and company.custom_end_time:
                start_time = convert_to_time(company.custom_start_time)
                end_time = convert_to_time(company.custom_end_time)
            elif company.custom_start_time_session and company.end_time_session:
                start_time = convert_to_time(company.custom_start_time_session)
                end_time = convert_to_time(company.custom_end_time_session)

            if not (start_time and end_time):
                continue
            if (
                start_time
                and end_time
                and is_time_in_range(start_time, end_time, current_time)
                and company.custom_send_invoice_to_zatca == "Background"
            ):
                any_company_in_range = True
                break
        if not any_company_in_range:
            pass
            return

        past_24_hours_time = add_to_date(now_datetime(), hours=-24)

        not_submitted_invoices = frappe.get_all(
            "POS Invoice",
            filters=[
                ["creation", ">=", past_24_hours_time],
                ["docstatus", "in", [0, 1]],
                ["custom_zatca_status", "=", "Not Submitted"],
            ],
            fields=["name", "docstatus", "company"],
        )

        if not not_submitted_invoices:
            # frappe.log_error(
            #     "No pending invoices found for ZATCA submission.",
            #     "ZATCA Background Job",
            # )
            pass
            return

        for invoice in not_submitted_invoices:
            pos_invoice_doc = frappe.get_doc("POS Invoice", invoice["name"])
            company_doc = frappe.get_doc("Company", pos_invoice_doc.company)
            # print(f"Processing {pos_invoice_doc.name}", "ZATCA Background Job")
            if pos_invoice_doc.docstatus == 1:
                zatca_background_on_submit(
                    pos_invoice_doc, bypass_background_check=True
                )
                frappe.log_error(
                    f"Processed {pos_invoice_doc.name}: Sent to ZATCA.",
                    "ZATCA Background Job",
                )
            elif company_doc.custom_submit_or_not == 1:
                pos_invoice_doc.submit()
                zatca_background_on_submit(
                    pos_invoice_doc, bypass_background_check=True
                )
                frappe.log_error(
                    f"Submitted {pos_invoice_doc.name} before sending to ZATCA.",
                    "ZATCA Background Job",
                )

        # frappe.log_error(
        #     f"Processed {len(not_submitted_invoices)} invoices for ZATCA submission.",
        #     "ZATCA Background Job",
        # )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ZATCA Background Job Error")


# submit_posinvoices_to_zatca_background_process()
