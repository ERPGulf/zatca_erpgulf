"""this file is used to schedule the background job for submitting invoices to ZATCA"""

from datetime import datetime, timedelta, time
import frappe
from frappe.utils import now_datetime, add_to_date

from zatca_erpgulf.zatca_erpgulf.sign_invoice import zatca_background_on_submit

from zatca_erpgulf.zatca_erpgulf.schedule_pos import (
    submit_posinvoices_to_zatca_background_process,
)

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


def submit_invoices_to_zatca_background():
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
                "custom_submit_or_not",
            ],
        )

        company_summary = "\n".join(
            [
                f"{c['name']}: send_invoice={c['custom_send_invoice_to_zatca']}, submit={c['custom_submit_or_not']}"
                for c in companies
            ]
        )

        # frappe.log_error(title="ZATCA Companies Debug", message=company_summary)

        any_company_in_range = False

        for company in companies:
            start_end_times = [
                (company.custom_start_time, company.custom_end_time),
                (company.custom_start_time_session, company.custom_end_time_session),
            ]

            valid_time_found = False

            for start, end in start_end_times:
                if start is not None and end is not None:
                    start_time = convert_to_time(start)
                    end_time = convert_to_time(end)

                    if is_time_in_range(start_time, end_time, current_time):
                        valid_time_found = True

                        break

            if (
                valid_time_found
                and company.custom_send_invoice_to_zatca == "Background"
            ):
                any_company_in_range = True
                break
            else:
                pass

        if not any_company_in_range:

            return

        past_24_hours_time = add_to_date(now_datetime(), hours=-24)
        not_submitted_invoices = frappe.get_all(
            "Sales Invoice",
            filters=[
                ["creation", ">=", past_24_hours_time],
                ["docstatus", "in", [0, 1]],
                [
                    "custom_zatca_status",
                    "in",
                    ["Not Submitted", "503 Service Unavailable"],
                     ["custom_zatca_status", "!=", "REPORTED"],
                ],
            ],
            fields=["name", "docstatus", "company"],
        )

        for invoice in not_submitted_invoices:
            try:
                sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice["name"])
                company_doc = frappe.get_doc("Company", sales_invoice_doc.company)
                if sales_invoice_doc.docstatus == 1:
                    zatca_background_on_submit(
                        sales_invoice_doc, bypass_background_check=True
                    )

                elif company_doc.custom_submit_or_not == 1:
                    sales_invoice_doc.submit()
                    zatca_background_on_submit(
                        sales_invoice_doc, bypass_background_check=True
                    )

                frappe.db.commit()
            except Exception as e:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Error processing invoice {invoice['name']}",
                )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "ZATCA Background Job Error")


def submit_invoices_to_zatca_background_process():
    """Submit invoices to ZATCA only if at least one company falls within the time range."""
    try:
        past_24_hours_time = add_to_date(now_datetime(), hours=-24)
        sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters=[
                ["creation", ">=", past_24_hours_time],
                ["docstatus", "in", [0, 1]],
                [
                    "custom_zatca_status",
                    "in",
                    ["Not Submitted", "503 Service Unavailable"],
                     ["custom_zatca_status", "!=", "REPORTED"],
                ],
            ],
            fields=["name"],
        )
        # print(f"sales_invoices: {sales_invoices}")
        if sales_invoices:
            submit_invoices_to_zatca_background()  # Process Sales Invoices
        pos_invoices = frappe.get_all(
            "POS Invoice",
            filters=[
                ["creation", ">=", past_24_hours_time],
                ["docstatus", "in", [0, 1]],
                [
                    "custom_zatca_status",
                    "in",
                    ["Not Submitted", "503 Service Unavailable"],
                ], ["custom_zatca_status", "!=", "REPORTED"],
            ],
            fields=["name"],
        )

        if pos_invoices:
            submit_posinvoices_to_zatca_background_process()  # Process POS Invoices

    except Exception:
        frappe.log_error(frappe.get_traceback(), "ZATCA Background Job Error")


# submit_invoices_to_zatca_background_process()
