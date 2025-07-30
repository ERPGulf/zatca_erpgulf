"""
ZATCA E-Invoicing Integration for ERPNext
This module facilitates the generation, validation, and submission of
 ZATCA-compliant e-invoices for companies
using ERPNext. It supports compliance with the ZATCA requirements for Phase 2,
including the creation of UBL XML
invoices, signing, and submission to ZATCA servers for clearance and reporting.
"""

import os
import io
import base64
import json
from frappe import _
import frappe
import requests
from pyqrcode import create as qr_create
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from zatca_erpgulf.zatca_erpgulf.createxml import (
    xml_tags,
    salesinvoice_data,
    add_document_level_discount_with_tax_template,
    add_document_level_discount_with_tax,
    company_data,
    customer_data,
    get_address,
    invoice_typecode_compliance,
    add_nominal_discount_tax,
    doc_reference_compliance,
    doc_reference,
    additional_reference,
    delivery_and_payment_means,
    delivery_and_payment_means_for_compliance,
    invoice_typecode_simplified,
    invoice_typecode_standard,
)
from zatca_erpgulf.zatca_erpgulf.xml_tax_data import tax_data, tax_data_with_template
from zatca_erpgulf.zatca_erpgulf.create_xml_final_part import (
    tax_data_nominal,
    tax_data_with_template_nominal,
    item_data,
    item_data_advance_invoice,
    item_data_with_template_advance_invoice,
    item_data_with_template,
    xml_structuring,
)
from zatca_erpgulf.zatca_erpgulf.create_qr import create_qr_code
from zatca_erpgulf.zatca_erpgulf.sign_invoice_first import (
    removetags,
    canonicalize_xml,
    getinvoicehash,
    digital_signature,
    extract_certificate_details,
    certificate_hash,
    signxml_modify,
    generate_signed_properties_hash,
    populate_the_ubl_extensions_output,
    generate_tlv_xml,
    structuring_signedxml,
    get_tlv_for_value,
    update_qr_toxml,
    compliance_api_call,
)
from zatca_erpgulf.zatca_erpgulf.sales_invoice_with_xmlqr import (
    submit_sales_invoice_withxmlqr,
)
from zatca_erpgulf.zatca_erpgulf.sales_invoice_withoutxml import (
    zatca_call_withoutxml,
)

from zatca_erpgulf.zatca_erpgulf.submit_xml_qr_notmultiple import (
    submit_sales_invoice_simplifeid,
)
from zatca_erpgulf.zatca_erpgulf.zatca_background_sched import (
    zatca_call_scheduler_background,
)

REPORTED_XML = "%Reported xml file%"
SAUDI_ARABIA = "Saudi Arabia"


def xml_base64_decode(signed_xmlfile_name):
    """xml base64 decode"""
    try:
        with open(signed_xmlfile_name, "r", encoding="utf-8") as file:
            xml = file.read().lstrip()
            base64_encoded = base64.b64encode(xml.encode("utf-8"))
            base64_decoded = base64_encoded.decode("utf-8")
            return base64_decoded
    except (ValueError, TypeError, KeyError) as e:
        frappe.throw(_(("xml decode base64" f"error: {str(e)}")))
        return None


def get_api_url(company_abbr, base_url):
    """There are many api susing in zatca which can be defined by a feild in settings"""
    try:
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if company_doc.custom_select == "Sandbox":
            url = company_doc.custom_sandbox_url + base_url
        elif company_doc.custom_select == "Simulation":
            url = company_doc.custom_simulation_url + base_url
        else:
            url = company_doc.custom_production_url + base_url

        return url

    except (ValueError, TypeError, KeyError) as e:
        frappe.throw(_(("get api url" f"error: {str(e)}")))
        return None


def get_reporting_status(result):
    """defining the reporting status"""
    try:
        reporting_status = result.text.strip()  # Strip any leading/trailing whitespace
        print("reportingStatus: " + reporting_status)
        return reporting_status
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(_(("error in reporting statu" f"error: {str(e)}")))
        return None


def success_log(response, uuid1, invoice_number):
    """defining the success log"""
    try:
        current_time = frappe.utils.now()
        frappe.get_doc(
            {
                "doctype": "ZATCA ERPGulf Success Log",
                "title": "ZATCA invoice call done successfully",
                "message": "This message by ZATCA Compliance",
                "uuid": uuid1,
                "invoice_number": invoice_number,
                "time": current_time,
                "zatca_response": response,
            }
        ).insert(ignore_permissions=True)
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(_(("error in success log" f"error: {str(e)}")))
        return None


def error_log():
    """defining the error log"""
    try:
        frappe.log_error(
            title="ZATCA invoice call failed in clearance status",
            message=frappe.get_traceback(),
        )
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(_(("error in error log" f"error: {str(e)}")))
        return None


def attach_qr_image(qrcodeb64, sales_invoice_doc):
    """attach the qr image"""
    try:
        if not hasattr(sales_invoice_doc, "ksa_einv_qr"):
            create_custom_fields(
                {
                    sales_invoice_doc.doctype: [
                        {
                            "fieldname": "ksa_einv_qr",
                            "label": "KSA E-Invoicing QR",
                            "fieldtype": "Attach Image",
                            "read_only": 1,
                            "no_copy": 1,
                            "hidden": 0,  # Set hidden to 0 for testing
                        }
                    ]
                }
            )
            # frappe.log("Custom field 'ksa_einv_qr' created.")
        qr_code = sales_invoice_doc.get("ksa_einv_qr")
        if qr_code and frappe.db.exists({"doctype": "File", "file_url": qr_code}):
            return
        qr_image = io.BytesIO()
        qr = qr_create(qrcodeb64, error="L")
        qr.png(qr_image, scale=8, quiet_zone=1)

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"QR_Phase2_{sales_invoice_doc.name}.png".replace(
                    os.path.sep, "__"
                ),
                "attached_to_doctype": sales_invoice_doc.doctype,
                "attached_to_name": sales_invoice_doc.name,
                "is_private": 1,
                "content": qr_image.getvalue(),
                "attached_to_field": "ksa_einv_qr",
            }
        )
        file_doc.save(ignore_permissions=True)
        sales_invoice_doc.db_set("ksa_einv_qr", file_doc.file_url)
        sales_invoice_doc.notify_update()

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(_(("attach qr images" f"error: {str(e)}")))


def reporting_api(
    uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc
):
    """reporting api based on the api data and payload"""
    try:
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )

        if not company_abbr:
            frappe.throw(
                _(f"Company with abbreviation {sales_invoice_doc.company} not found.")
            )
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_xmlfile_name),
        }
        # production_csid = company_doc.custom_basic_auth_from_production
        xml_base64 = xml_base64_decode(signed_xmlfile_name)

        xml_cleared_data = base64.b64decode(xml_base64).decode("utf-8")
        file = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": "Reported xml file " + sales_invoice_doc.name + ".xml",
                "attached_to_doctype": sales_invoice_doc.doctype,
                "is_private": 1,
                "attached_to_name": sales_invoice_doc.name,
                "content": xml_cleared_data,
            }
        )
        file.save(ignore_permissions=True)
        sales_invoice_doc.db_set("custom_ksa_einvoicing_xml", file.file_url)
        if sales_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "ZATCA Multiple Setting", sales_invoice_doc.custom_zatca_pos_name
            )
            production_csid = zatca_settings.custom_final_auth_csid
        else:
            production_csid = company_doc.custom_basic_auth_from_production
        if production_csid:
            headers = {
                "accept": "application/json",
                "accept-language": "en",
                "Clearance-Status": "0",
                "Accept-Version": "V2",
                "Authorization": "Basic " + production_csid,
                "Content-Type": "application/json",
                "Cookie": "TS0106293e=0132a679c0639d13d069bcba831384623a2ca6da47fac8d91bef610c47c7119dcdd3b817f963ec301682dae864351c67ee3a402866",
            }
        else:
            frappe.throw(f"Production CSID for company {company_abbr} not found.")
            headers = None
        if company_doc.custom_send_invoice_to_zatca != "Batches":
            try:
                frappe.publish_realtime(
                    "show_gif",
                    {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"},
                    user=frappe.session.user,
                )
                response = requests.post(
                    url=get_api_url(company_abbr, base_url="invoices/reporting/single"),
                    headers=headers,
                    json=payload,
                    timeout=300,
                )
                frappe.publish_realtime("hide_gif", user=frappe.session.user)
                if response.status_code in (400, 405, 406, 409):
                    invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                    invoice_doc.db_set(
                        "custom_uuid",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    invoice_doc.db_set(
                        "custom_zatca_status",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    invoice_doc.db_set(
                        "custom_zatca_full_response",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    frappe.throw(
                        _(
                            (
                                "Error: The request you are sending to ZATCA is in incorrect format. "
                                "Please report to system administrator. "
                                f"Status code: {response.status_code}<br><br>"
                                f"{response.text}"
                            )
                        )
                    )

                if response.status_code in (401, 403, 407, 451):
                    invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                    invoice_doc.db_set(
                        "custom_uuid",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    invoice_doc.db_set(
                        "custom_zatca_status",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    invoice_doc.db_set(
                        "custom_zatca_full_response",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    frappe.throw(
                        _(
                            (
                                "Error: ZATCA Authentication failed. "
                                "Your access token may be expired or not valid. "
                                "Please contact your system administrator. "
                                f"Status code: {response.status_code}<br><br>"
                                f"{response.text}"
                            )
                        )
                    )

                if response.status_code not in (200, 202):
                    invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                    invoice_doc.db_set(
                        "custom_uuid",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    invoice_doc.db_set(
                        "custom_zatca_status",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    invoice_doc.db_set(
                        "custom_zatca_full_response",
                        "Not Submitted",
                        commit=True,
                        update_modified=True,
                    )
                    frappe.throw(
                        _(
                            (
                                "Error: ZATCA server busy or not responding."
                                " Try after sometime or contact your system administrator. "
                                f"Status code: {response.status_code}<br><br>"
                                f"{response.text}"
                            )
                        )
                    )

                if response.status_code in (200, 202):
                    msg = (
                        "SUCCESS: <br><br>"
                        if response.status_code == 200
                        else (
                            "REPORTED WITH WARNINGS: <br><br> "
                            "Please copy the below message and send it to your system administrator "
                            "to fix this warnings before next submission <br><br>"
                        )
                    )
                    msg += (
                        f"Status Code: {response.status_code}<br><br> "
                        f"ZATCA Response: {response.text}<br><br>"
                    )
                    company_name = sales_invoice_doc.company
                    # settings = frappe.get_doc("Company", company_name)
                    # company_abbr = settings.abbr
                    # if settings.custom_send_einvoice_background:
                    #     frappe.msgprint(msg)

                    # company_doc.custom_pih = encoded_hash
                    # company_doc.save(ignore_permissions=True)
                    if sales_invoice_doc.custom_zatca_pos_name:
                        if (
                            zatca_settings.custom_send_pos_invoices_to_zatca_on_background
                        ):
                            frappe.msgprint(msg)

                        # Update PIH data without JSON formatting
                        zatca_settings.custom_pih = encoded_hash
                        zatca_settings.save(ignore_permissions=True)

                    else:
                        settings = frappe.get_doc("Company", company_name)
                        company_abbr = settings.abbr
                        if settings.custom_send_einvoice_background:
                            frappe.msgprint(msg)

                        # Update PIH data without JSON formatting
                        company_doc.custom_pih = encoded_hash
                        company_doc.save(ignore_permissions=True)

                    invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                    invoice_doc.db_set(
                        "custom_zatca_full_response",
                        msg,
                        commit=True,
                        update_modified=True,
                    )
                    invoice_doc.db_set(
                        "custom_uuid", uuid1, commit=True, update_modified=True
                    )
                    invoice_doc.db_set(
                        "custom_zatca_status",
                        "REPORTED",
                        commit=True,
                        update_modified=True,
                    )

                    success_log(response.text, uuid1, invoice_number)
                else:

                    error_log()
            except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
                frappe.throw(_(f"Error in reporting API-2: {str(e)}"))

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
        invoice_doc.db_set(
            "custom_zatca_full_response",
            f"Error: {str(e)}",
            commit=True,
            update_modified=True,
        )
        frappe.throw(_(f"Error in reporting API-1: {str(e)}"))


def clearance_api(
    uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc
):
    """The clearance api with payload and headeders aand signed xml data"""
    try:
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )
        if not company_abbr:
            frappe.throw(
                _(
                    f" problem with company name in {sales_invoice_doc.company} not found."
                )
            )
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        # production_csid = company_doc.custom_basic_auth_from_production or ""
        if sales_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "ZATCA Multiple Setting", sales_invoice_doc.custom_zatca_pos_name
            )
            production_csid = zatca_settings.custom_final_auth_csid
        else:
            production_csid = company_doc.custom_basic_auth_from_production or ""
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_xmlfile_name),
        }

        if production_csid:
            headers = {
                "accept": "application/json",
                "accept-language": "en",
                "Clearance-Status": "1",
                "Accept-Version": "V2",
                "Authorization": "Basic " + production_csid,
                "Content-Type": "application/json",
                "Cookie": "TS0106293e=0132a679c03c628e6c49de86c0f6bb76390abb4416868d6368d6d7c05da619c8326266f5bc262b7c0c65a6863cd3b19081d64eee99",
            }
        else:
            frappe.throw(_(f"Production CSID for company {company_abbr} not found."))
            headers = None
        frappe.publish_realtime(
            "show_gif",
            {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"},
            user=frappe.session.user,
        )

        response = requests.post(
            url=get_api_url(company_abbr, base_url="invoices/clearance/single"),
            headers=headers,
            json=payload,
            timeout=300,
        )
        frappe.publish_realtime("hide_gif", user=frappe.session.user)

        if response.status_code in (400, 405, 406, 409):
            invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
            )
            invoice_doc.db_set(
                "custom_zatca_status",
                "Not Submitted",
                commit=True,
                update_modified=True,
            )
            invoice_doc.db_set("custom_zatca_full_response", "Not Submitted")
            frappe.throw(
                _(
                    (
                        "Error: The request you are sending to ZATCA is in incorrect format. "
                        f"Status code: {response.status_code}<br><br>"
                        f"{response.text}"
                    )
                )
            )
        if response.status_code in (401, 403, 407, 451):
            invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
            )
            invoice_doc.db_set(
                "custom_zatca_status",
                "Not Submitted",
                commit=True,
                update_modified=True,
            )
            invoice_doc.db_set("custom_zatca_full_response", "Not Submitted")
            frappe.throw(
                _(
                    (
                        "Error: ZATCA Authentication failed. "
                        f"Status code: {response.status_code}<br><br>"
                        f"{response.text}"
                    )
                )
            )
        if response.status_code not in (200, 202):
            invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
            )
            invoice_doc.db_set(
                "custom_zatca_status",
                "Not Submitted",
                commit=True,
                update_modified=True,
            )
            invoice_doc.db_set("custom_zatca_full_response", "Not Submitted")
            frappe.throw(
                _(
                    f"Error: ZATCA server busy or not responding. Status code: {response.status_code}"
                )
            )

        if response.status_code in (200, 202):
            msg = (
                "CLEARED WITH WARNINGS: <br><br>"
                if response.status_code == 202
                else "SUCCESS: <br><br>"
            )
            msg += (
                f"Status Code: {response.status_code}<br><br>"
                f"ZATCA Response: {response.text}<br><br>"
            )

            company_name = sales_invoice_doc.company
            # settings = frappe.get_doc("Company", company_name)
            # company_abbr = settings.abbr
            # if settings.custom_send_einvoice_background:
            #     frappe.msgprint(msg)
            # company_doc.custom_pih = encoded_hash
            # company_doc.save(ignore_permissions=True)
            # company_name = pos_invoice_doc.company
            if sales_invoice_doc.custom_zatca_pos_name:
                if zatca_settings.custom_send_pos_invoices_to_zatca_on_background:
                    frappe.msgprint(msg)

                    # Update PIH data without JSON formatting
                zatca_settings.custom_pih = encoded_hash
                zatca_settings.save(ignore_permissions=True)

            else:
                settings = frappe.get_doc("Company", company_name)
                company_abbr = settings.abbr
                if settings.custom_send_einvoice_background:
                    frappe.msgprint(msg)

                    # Update PIH data without JSON formatting
                company_doc.custom_pih = encoded_hash
                company_doc.save(ignore_permissions=True)

            invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_zatca_full_response", msg, commit=True, update_modified=True
            )
            invoice_doc.db_set("custom_uuid", uuid1, commit=True, update_modified=True)
            invoice_doc.db_set(
                "custom_zatca_status", "CLEARED", commit=True, update_modified=True
            )

            data = response.json()
            base64_xml = data.get("clearedInvoice")
            xml_cleared = base64.b64decode(base64_xml).decode("utf-8")
            file = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": "Cleared xml file " + sales_invoice_doc.name + ".xml",
                    "attached_to_doctype": sales_invoice_doc.doctype,
                    "is_private": 1,
                    "attached_to_name": sales_invoice_doc.name,
                    "content": xml_cleared,
                }
            )
            file.save(ignore_permissions=True)
            sales_invoice_doc.db_set("custom_ksa_einvoicing_xml", file.file_url)
            success_log(response.text, uuid1, invoice_number)
            return xml_cleared
        else:
            error_log()

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
        invoice_doc.db_set(
            "custom_zatca_full_response",
            f"Error: {str(e)}",
            commit=True,
            update_modified=True,
        )
        invoice_doc.db_set(
            "custom_zatca_status",
            "503 Service Unavailable",
            commit=True,
            update_modified=True,
        )
        frappe.throw(_(f"Error in clearance API: {str(e)}"))


def is_file_attached(file_url):
    """Check if a file is attached by verifying its existence in the database."""
    return file_url and frappe.db.exists("File", {"file_url": file_url})


def is_qr_and_xml_attached(sales_invoice_doc):
    """Check if both QR code and XML file are already"""

    # Get the QR Code field value
    qr_code = sales_invoice_doc.get("ksa_einv_qr")

    # Get the XML file if attached
    xml_file = frappe.db.get_value(
        "File",
        {
            "attached_to_doctype": sales_invoice_doc.doctype,
            "attached_to_name": sales_invoice_doc.name,
            "file_name": ["like", REPORTED_XML],
        },
        "file_url",
    )

    # Ensure both files exist before confirming attachment
    return is_file_attached(qr_code) and is_file_attached(xml_file)


@frappe.whitelist(allow_guest=False)
def zatca_call(
    invoice_number,
    compliance_type="0",
    any_item_has_tax_template=False,
    company_abbr=None,
    source_doc=None,
):
    """zatca call which includes the function calling and validation reguarding the api and
    based on this the zATCA output and message is getting"""
    try:
        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw(_("Invoice Number is NOT Valid: " + str(invoice_number)))
        invoice = xml_tags()
        invoice, uuid1, sales_invoice_doc = salesinvoice_data(invoice, invoice_number)
        # Get the company abbreviation
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )

        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                invoice = invoice_typecode_simplified(invoice, sales_invoice_doc)
            else:
                invoice = invoice_typecode_standard(invoice, sales_invoice_doc)
        else:
            invoice = invoice_typecode_compliance(invoice, compliance_type)

        invoice = doc_reference(invoice, sales_invoice_doc, invoice_number)
        invoice = additional_reference(invoice, company_abbr, sales_invoice_doc)
        invoice = company_data(invoice, sales_invoice_doc)
        invoice = customer_data(invoice, sales_invoice_doc)
        invoice = delivery_and_payment_means(
            invoice, sales_invoice_doc, sales_invoice_doc.is_return
        )

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            invoice = add_nominal_discount_tax(invoice, sales_invoice_doc)

        elif not any_item_has_tax_template:
            invoice = add_document_level_discount_with_tax(invoice, sales_invoice_doc)
        else:
            # Add document-level discount with tax template
            invoice = add_document_level_discount_with_tax_template(
                invoice, sales_invoice_doc
            )

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            if not any_item_has_tax_template:
                invoice = tax_data_nominal(invoice, sales_invoice_doc)
            else:
                invoice = tax_data_with_template_nominal(invoice, sales_invoice_doc)
        else:
            if not any_item_has_tax_template:
                invoice = tax_data(invoice, sales_invoice_doc)
            else:
                invoice = tax_data_with_template(invoice, sales_invoice_doc)
        is_claudion_installed = "claudion4saudi" in frappe.get_installed_apps()
        has_advance_copy = (
            hasattr(sales_invoice_doc, "custom_advances_copy")
            and sales_invoice_doc.custom_advances_copy
        )

        if is_claudion_installed and has_advance_copy:
            if not any_item_has_tax_template:
                invoice = item_data_advance_invoice(invoice, sales_invoice_doc)
            else:
                invoice = item_data_with_template_advance_invoice(
                    invoice, sales_invoice_doc
                )
        else:
            if not any_item_has_tax_template:
                invoice = item_data(invoice, sales_invoice_doc)
            else:
                invoice = item_data_with_template(invoice, sales_invoice_doc)

        xml_structuring(invoice)
        try:
            with open(
                frappe.local.site + "/private/files/finalzatcaxml.xml",
                "r",
                encoding="utf-8",
            ) as file:
                file_content = file.read()
        except FileNotFoundError:
            frappe.throw("XML file not found")
        tag_removed_xml = removetags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash1, encoded_hash = getinvoicehash(canonicalized_xml)
        encoded_signature = digital_signature(hash1, company_abbr, source_doc)
        issuer_name, serial_number = extract_certificate_details(
            company_abbr, source_doc
        )
        encoded_certificate_hash = certificate_hash(company_abbr, source_doc)
        namespaces, signing_time = signxml_modify(company_abbr, source_doc)
        signed_properties_base64 = generate_signed_properties_hash(
            signing_time, issuer_name, serial_number, encoded_certificate_hash
        )
        populate_the_ubl_extensions_output(
            encoded_signature,
            namespaces,
            signed_properties_base64,
            encoded_hash,
            company_abbr,
            source_doc,
        )
        tlv_data = generate_tlv_xml(company_abbr, source_doc)

        tagsbufsarray = []
        for tag_num, tag_value in tlv_data.items():
            tagsbufsarray.append(get_tlv_for_value(tag_num, tag_value))

        qrcodebuf = b"".join(tagsbufsarray)
        qrcodeb64 = base64.b64encode(qrcodebuf).decode("utf-8")
        update_qr_toxml(qrcodeb64, company_abbr)
        signed_xmlfile_name = structuring_signedxml()
        # Example usage
        # file_path = generate_invoice_pdf(
        #     invoice_number, l anguage="en", letterhead="Sample letterhead"
        # )
        # frappe.throw(f"PDF saved at: {file_path}")
        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                attach_qr_image(qrcodeb64, sales_invoice_doc)
                reporting_api(
                    uuid1,
                    encoded_hash,
                    signed_xmlfile_name,
                    invoice_number,
                    sales_invoice_doc,
                )

            else:
                clearance_api(
                    uuid1,
                    encoded_hash,
                    signed_xmlfile_name,
                    invoice_number,
                    sales_invoice_doc,
                )
                attach_qr_image(qrcodeb64, sales_invoice_doc)
        else:
            compliance_api_call(
                uuid1,
                encoded_hash,
                signed_xmlfile_name,
                company_abbr,
                source_doc,
            )
            attach_qr_image(qrcodeb64, sales_invoice_doc)

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.log_error(
            title="ZATCA invoice call failed",
            message=f"{frappe.get_traceback()}\nError: {str(e)}",
        )


@frappe.whitelist(allow_guest=False)
def zatca_call_compliance(
    invoice_number,
    company_abbr,
    source_doc,
    compliance_type="0",
    any_item_has_tax_template=False,
):
    """zatca call compliance"""

    try:
        if source_doc:
            source_doc = frappe.get_doc(json.loads(source_doc))
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")

        if not company_name:
            frappe.throw(_(f"Company with abbreviation {company_abbr} not found."))

        company_doc = frappe.get_doc("Company", company_name)

        if company_doc.custom_validation_type == "Simplified Invoice":
            compliance_type = "1"
        elif company_doc.custom_validation_type == "Standard Invoice":
            compliance_type = "2"
        elif company_doc.custom_validation_type == "Simplified Credit Note":
            compliance_type = "3"
        elif company_doc.custom_validation_type == "Standard Credit Note":
            compliance_type = "4"
        elif company_doc.custom_validation_type == "Simplified Debit Note":
            compliance_type = "5"
        elif company_doc.custom_validation_type == "Standard Debit Note":
            compliance_type = "6"
        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw(_("Invoice Number is NOT Valid: " + str(invoice_number)))
        invoice = xml_tags()
        invoice, uuid1, sales_invoice_doc = salesinvoice_data(invoice, invoice_number)
        any_item_has_tax_template = any(
            item.item_tax_template for item in sales_invoice_doc.items
        )
        if any_item_has_tax_template and not all(
            item.item_tax_template for item in sales_invoice_doc.items
        ):
            frappe.throw(
                _(
                    "If any one item has an Item Tax Template,"
                    " all items must have an Item Tax Template."
                )
            )
        invoice = invoice_typecode_compliance(invoice, compliance_type)
        invoice = doc_reference_compliance(
            invoice, sales_invoice_doc, invoice_number, compliance_type
        )
        invoice = additional_reference(invoice, company_abbr, sales_invoice_doc)
        invoice = company_data(invoice, sales_invoice_doc)
        invoice = customer_data(invoice, sales_invoice_doc)
        invoice = delivery_and_payment_means_for_compliance(
            invoice, sales_invoice_doc, compliance_type
        )

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            # Add document-level discount with tax
            invoice = add_nominal_discount_tax(invoice, sales_invoice_doc)
        elif not any_item_has_tax_template:
            invoice = add_document_level_discount_with_tax(invoice, sales_invoice_doc)
        else:
            # Add document-level discount with tax template
            invoice = add_document_level_discount_with_tax_template(
                invoice, sales_invoice_doc
            )
        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            if not any_item_has_tax_template:
                invoice = tax_data_nominal(invoice, sales_invoice_doc)
            else:
                invoice = tax_data_with_template_nominal(invoice, sales_invoice_doc)
        else:
            if not any_item_has_tax_template:
                invoice = tax_data(invoice, sales_invoice_doc)
            else:
                invoice = tax_data_with_template(invoice, sales_invoice_doc)

        if not any_item_has_tax_template:
            invoice = item_data(invoice, sales_invoice_doc)

        else:
            item_data_with_template(invoice, sales_invoice_doc)
        # Generate and process the XML data
        xml_structuring(invoice)
        with open(
            frappe.local.site + "/private/files/finalzatcaxml.xml",
            "r",
            encoding="utf-8",
        ) as file:
            file_content = file.read()

        tag_removed_xml = removetags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash1, encoded_hash = getinvoicehash(canonicalized_xml)
        encoded_signature = digital_signature(hash1, company_abbr, source_doc)
        issuer_name, serial_number = extract_certificate_details(
            company_abbr, source_doc
        )
        encoded_certificate_hash = certificate_hash(company_abbr, source_doc)
        namespaces, signing_time = signxml_modify(company_abbr, source_doc)
        signed_properties_base64 = generate_signed_properties_hash(
            signing_time, issuer_name, serial_number, encoded_certificate_hash
        )
        populate_the_ubl_extensions_output(
            encoded_signature,
            namespaces,
            signed_properties_base64,
            encoded_hash,
            company_abbr,
            source_doc,
        )
        # Generate the TLV data and QR code
        tlv_data = generate_tlv_xml(company_abbr, source_doc)
        tagsbufsarray = []
        for tag_num, tag_value in tlv_data.items():
            tagsbufsarray.append(get_tlv_for_value(tag_num, tag_value))

        qrcodebuf = b"".join(tagsbufsarray)
        qrcodeb64 = base64.b64encode(qrcodebuf).decode("utf-8")

        update_qr_toxml(qrcodeb64, company_abbr)
        signed_xmlfile_name = structuring_signedxml()
        value = compliance_api_call(
            uuid1, encoded_hash, signed_xmlfile_name, company_abbr, source_doc
        )
        return value

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.log_error(
            title="ZATCA invoice call failed", message=frappe.get_traceback()
        )
        frappe.throw(_("Error in ZATCA invoice call: " + str(e)))
        return None


@frappe.whitelist(allow_guest=False)
def zatca_background(invoice_number, source_doc, bypass_background_check=False):
    """defines the zatca bacground"""
    try:
        # frappe.throw("DEBUG: Country found in address: ")
        if source_doc:
            source_doc = frappe.get_doc(json.loads(source_doc))
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
        company_name = sales_invoice_doc.company
        settings = frappe.get_doc("Company", company_name)
        company_abbr = settings.abbr
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        # if company_doc.custom_zatca_invoice_enabled != 1 or (
        #     company_doc.custom_zatca_invoice_enabled == 1
        #     and company_doc.custom_phase_1_or_2 == "Phase-1"
        # ):
        #     # frappe.msgprint("Zatca Invoice is not enabled or Phase is not Phase-1. Submitting the document.")
        #     return

        if (
            sales_invoice_doc.taxes
            and sales_invoice_doc.taxes[0].included_in_print_rate == 1
        ):
            if any(item.item_tax_template for item in sales_invoice_doc.items):
                frappe.throw(
                    _(
                        "As per ZATCA regulation,Item Tax Template cannot be used when taxes "
                        "are included in the print rate. Please remove Item Tax Templates."
                    )
                )
        any_item_has_tax_template = any(
            item.item_tax_template for item in sales_invoice_doc.items
        )
        if any_item_has_tax_template and not all(
            item.item_tax_template for item in sales_invoice_doc.items
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulation,If any one item has an Item Tax Template,"
                    " all items must have an Item Tax Template."
                )
            )
        tax_categories = set()
        for item in sales_invoice_doc.items:
            if item.item_tax_template:
                item_tax_template = frappe.get_doc(
                    "Item Tax Template", item.item_tax_template
                )
                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                tax_categories.add(zatca_tax_category)
                for tax in item_tax_template.taxes:
                    tax_rate = float(tax.tax_rate)

                    if f"{tax_rate:.2f}" not in [
                        "5.00",
                        "15.00",
                    ] and zatca_tax_category not in [
                        "Zero Rated",
                        "Exempted",
                        "Services outside scope of tax / Not subject to VAT",
                    ]:
                        frappe.throw(
                            _(
                                (
                                    "As per ZATCA regulation,ZATCA tax category should be"
                                    " 'Zero Rated','Exempted' or 'Services outside scope of tax / Not subject to VAT' "
                                    "for items with tax rate not equal to 5.00 or 15.00."
                                )
                            )
                        )

                    if (
                        f"{tax_rate:.2f}" == "15.00"
                        and zatca_tax_category != "Standard"
                    ):
                        frappe.throw(
                            _(
                                "Check the ZATCA category code and enable it as standard."
                            )
                        )
        if not company_doc.tax_id:
            frappe.throw(_("As per ZATCA regulations, Company Tax ID is mandatory"))
        if company_doc.tax_id:
            if not (company_doc.tax_id.isdigit() and len(company_doc.tax_id) == 15):
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Company Tax ID must be a 15-digit number"
                    )
                )
            elif not (
                company_doc.tax_id.startswith("3") and company_doc.tax_id.endswith("3")
            ):
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Company Tax ID must start with 3 and end with 3"
                    )
                )
        address = get_address(sales_invoice_doc, company_doc)
        if not address.address_line1:
            frappe.throw(
                _(
                    "As per ZATCA regulations, Address Line 1 is required in the company address."
                )
            )

        if not address.address_line2:
            frappe.throw(
                _(
                    "As per ZATCA regulations, Address Line 2 is required in the company address."
                )
            )

        if (
            not address.custom_building_number
            or not address.custom_building_number.isdigit()
            or len(address.custom_building_number) != 4
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations, Building Number must be exactly 4 digitsin company address."
                )
            )

        if (
            not address.pincode
            or not address.pincode.isdigit()
            or len(address.pincode) != 5
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations, Pincode must be exactly 5 digits in company address."
                )
            )
        base_discount_amount = sales_invoice_doc.get("base_discount_amount", 0.0)
        if (
            sales_invoice_doc.custom_zatca_nominal_invoice == 1
            and sales_invoice_doc.get("base_discount_amount", 0.0) < 0
        ):
            frappe.throw(
                _(
                    (
                        "As per ZATCA regulations, Only the document level discount is possible for  "
                        "ZATCA nominal invoices.Please ensure the discount is applied correctly."
                    )
                )
            )
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
        if customer_doc.custom_b2c == 0:
            if not customer_doc.custom_buyer_id:
                frappe.throw(
                    "As per ZATCA regulations - For B2B Customers, customer CR number has to be provided"
                )
        address = None
        if customer_doc.custom_b2c != 1:
            if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
                if sales_invoice_doc.customer_address:
                    address = frappe.get_doc(
                        "Address", sales_invoice_doc.customer_address
                    )
            else:
                if customer_doc.customer_primary_address:
                    address = frappe.get_doc(
                        "Address", customer_doc.customer_primary_address
                    )
            # frappe.throw(f"DEBUG: Country found in address: '{address.country}'")
            if not address:
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Customer address is mandatory for non-B2C customers."
                    )
                )

            # ZATCA-required field validation
            if not address.address_line1:
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Address Line 1 is required in customer address."
                    )
                )
            if not address.address_line2:
                frappe.throw(
                    _(
                        "As per ZATCA regulations,Address Line 2 is required in customer address."
                    )
                )

            if address and address.country == SAUDI_ARABIA:
                if (
                    not address.custom_building_number
                    or not address.custom_building_number.isdigit()
                    or len(address.custom_building_number) != 4
                ):

                    frappe.throw(
                        _(
                            "As per ZATCA regulations,Building Number must be exactly 4 digits in customer address."
                        )
                    )
                if (
                    not address.pincode
                    or not address.pincode.isdigit()
                    or len(address.pincode) != 5
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Pincode must be exactly 5 digits in customer address."
                        )
                    )
            # if customer_doc.custom_b2c != 1:
            if address and address.country == SAUDI_ARABIA:
                if not customer_doc.tax_id:
                    frappe.throw(
                        _(
                            "As per ZATCA regulations,Tax ID is required for customers in Saudi Arabia."
                        )
                    )
                elif (
                    not customer_doc.tax_id.isdigit() or len(customer_doc.tax_id) != 15
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations,Customer Tax ID must be exactly 15 digits."
                        )
                    )
                elif not (
                    customer_doc.tax_id.startswith("3")
                    and customer_doc.tax_id.endswith("3")
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Customer Tax ID must start with 3 and end with 3."
                        )
                    )

        if "claudion4saudi" in frappe.get_installed_apps():
            if (
                hasattr(sales_invoice_doc, "custom_advances_copy")
                and sales_invoice_doc.custom_advances_copy
            ):
                if (
                    sales_invoice_doc.custom_advances_copy[0].reference_name
                    and customer_doc.custom_b2c == 1
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Advance allocation is supported for "
                            "non B2C customers. Please change the Customer type to B2B."
                        )
                    )
        if (
            sales_invoice_doc.custom_zatca_nominal_invoice == 1
            and sales_invoice_doc.get("additional_discount_percentage", 0.0) != 100
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations,Only a 100% discount is allowed for ZATCA"
                    " nominal invoices.Please ensure the additional discount percentage is set to 100."
                )
            )

        if (
            sales_invoice_doc.custom_zatca_nominal_invoice == 1
            and sales_invoice_doc.get("custom_submit_line_item_discount_to_zatca")
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations, For nominal invoices, please disable line item"
                    "discounts by unchecking 'Submit Line Item Discount to ZATCA'."
                )
            )

        if len(tax_categories) > 1 and base_discount_amount > 0:
            frappe.throw(
                _(
                    "As per ZATCA regulations, ZATCA does not respond for multiple items with multiple tax categories"
                    " with doc-level discount. Please ensure all items have the same tax category."
                )
            )
        if (
            base_discount_amount > 0
            and sales_invoice_doc.apply_discount_on != "Net Total"
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations,You cannot put discount on Grand total as the tax is already calculated."
                    " Please make sure your discount is in Net total field."
                )
            )

        if base_discount_amount < 0 and sales_invoice_doc.is_return == 0:
            frappe.throw(
                _(
                    "As per ZATCA regulations,Additional discount cannot be negative. Please enter a positive value."
                )
            )

        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw(
                _(
                    "Please save and submit the invoice before sending to ZATCA: "
                    + str(invoice_number)
                )
            )

        if sales_invoice_doc.docstatus in [0, 2]:
            frappe.throw(
                _(
                    "Please submit the invoice before sending to ZATCA: "
                    + str(invoice_number)
                )
            )

        if sales_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw(_("Already submitted to Zakat and Tax Authority"))

        if settings.custom_zatca_invoice_enabled != 1:
            frappe.throw(
                _(
                    "ZATCA Invoice is not enabled in Company Settings,"
                    " Please contact your system administrator"
                )
            )
        # if settings.custom_phase_1_or_2 == "Phase-2":
        is_gpos_installed = "gpos" in frappe.get_installed_apps()

        # Check if the field exists
        field_exists = frappe.get_meta("Sales Invoice").has_field("custom_unique_id")
        if is_gpos_installed:
            if sales_invoice_doc.custom_xml and not sales_invoice_doc.custom_qr_code:
                frappe.throw(
                    _(
                        "Please provide the 'qr_code' data when 'xml' is filled for invoice: "
                        + str(invoice_number)
                    )
                )
        if settings.custom_phase_1_or_2 == "Phase-2":
            if field_exists and sales_invoice_doc.custom_unique_id:

                if is_gpos_installed and sales_invoice_doc.custom_xml:
                    # Set the custom XML field
                    custom_xml_field = sales_invoice_doc.custom_xml
                    submit_sales_invoice_withxmlqr(
                        sales_invoice_doc, custom_xml_field, invoice_number
                    )
                else:
                    zatca_call_withoutxml(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
            else:
                if is_qr_and_xml_attached(sales_invoice_doc):
                    custom_xml_field = frappe.db.get_value(
                        "File",
                        {
                            "attached_to_doctype": sales_invoice_doc.doctype,
                            "attached_to_name": sales_invoice_doc.name,
                            "file_name": ["like", REPORTED_XML],
                        },
                        "file_url",
                    )
                    submit_sales_invoice_simplifeid(
                        sales_invoice_doc, custom_xml_field, invoice_number
                    )
                elif (
                    settings.custom_send_invoice_to_zatca == "Background"
                    and not bypass_background_check
                ):
                    zatca_call_scheduler_background(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
                else:

                    zatca_call(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )

        else:
            create_qr_code(sales_invoice_doc, method=None)
        return "Success"
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(_("Error in background call: " + str(e)))


@frappe.whitelist(allow_guest=False)
def zatca_background_on_submit(doc, _method=None, bypass_background_check=False):
    """referes according to the ZATC based sytem with the submitbutton of the sales invoice"""
    try:
        source_doc = doc
        sales_invoice_doc = doc
        invoice_number = sales_invoice_doc.name
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )
        if not company_abbr:
            frappe.throw(
                _(f"Company abbreviation for {sales_invoice_doc.company} not found.")
            )
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})

        if company_doc.custom_zatca_invoice_enabled != 1:
            # frappe.msgprint("Zatca Invoice is not enabled. Submitting the document.")
            return  # Exit the function without further checks
        if (
            company_doc.custom_zatca_invoice_enabled == 1
            and company_doc.custom_phase_1_or_2 == "Phase-1"
        ):
            # frappe.msgprint(
            #     "Zatca Invoice is not enabled or Phase is not Phase-1. Submitting the document."
            # )
            create_qr_code(sales_invoice_doc, method=_method)
            return

        if (
            sales_invoice_doc.taxes
            and sales_invoice_doc.taxes[0].included_in_print_rate == 1
        ):
            if any(item.item_tax_template for item in sales_invoice_doc.items):
                frappe.throw(
                    "As per ZATCA regulations, Item Tax Template cannot be used when taxes are included"
                    " in the print rate. Please remove Item Tax Templates."
                )
        any_item_has_tax_template = False
        for item in sales_invoice_doc.items:
            if item.item_tax_template:
                any_item_has_tax_template = True
                break
        if any_item_has_tax_template:
            for item in sales_invoice_doc.items:
                if not item.item_tax_template:
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, If any one item has an Item Tax Template,"
                            " all items must have an Item Tax Template."
                        )
                    )
        tax_categories = set()
        for item in sales_invoice_doc.items:
            if item.item_tax_template:
                item_tax_template = frappe.get_doc(
                    "Item Tax Template", item.item_tax_template
                )
                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                tax_categories.add(zatca_tax_category)
                for tax in item_tax_template.taxes:
                    tax_rate = float(tax.tax_rate)

                    if f"{tax_rate:.2f}" not in [
                        "5.00",
                        "15.00",
                    ] and zatca_tax_category not in [
                        "Zero Rated",
                        "Exempted",
                        "Services outside scope of tax / Not subject to VAT",
                    ]:
                        frappe.throw(
                            _(
                                "As per ZATCA regulations, ZATCA tax category should be "
                                "'Zero Rated', 'Exempted', or 'Services outside scope of tax / Not subject to VAT' "
                                "for items with tax rate not equal to 5.00 or 15.00."
                            )
                        )

                    if (
                        f"{tax_rate:.2f}" == "15.00"
                        and zatca_tax_category != "Standard"
                    ):
                        frappe.throw(
                            _(
                                "Check the ZATCA category code and enable it as Standard."
                            )
                        )

        base_discount_amount = sales_invoice_doc.get("base_discount_amount", 0.0)
        if (
            sales_invoice_doc.custom_zatca_nominal_invoice == 1
            and sales_invoice_doc.get("base_discount_amount", 0.0) < 0
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulation, only the document level discount is possible for ZATCA nominal invoices."
                    " Please ensure the discount is applied correctly."
                )
            )
        if not company_doc.tax_id:
            frappe.throw(_("As per ZATCA regulations, Company Tax ID is mandatory"))
        if company_doc.tax_id:
            if not (company_doc.tax_id.isdigit() and len(company_doc.tax_id) == 15):
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Company Tax ID must be a 15-digit number"
                    )
                )
            elif not (
                company_doc.tax_id.startswith("3") and company_doc.tax_id.endswith("3")
            ):
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Company Tax ID must start with 3 and end with 3"
                    )
                )
        address = get_address(sales_invoice_doc, company_doc)
        if not address.address_line1:
            frappe.throw(
                _(
                    "As per ZATCA regulations, Address Line 1 is required in the company address."
                )
            )

        if not address.address_line2:
            frappe.throw(
                _(
                    "As per ZATCA regulations, Address Line 2 is required in the company address."
                )
            )

        if (
            not address.custom_building_number
            or not address.custom_building_number.isdigit()
            or len(address.custom_building_number) != 4
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations, Building Number must be exactly 4 digitsin company address."
                )
            )

        if (
            not address.pincode
            or not address.pincode.isdigit()
            or len(address.pincode) != 5
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations, Pincode must be exactly 5 digits in company address."
                )
            )

        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
        if customer_doc.custom_b2c == 0:
            if not customer_doc.custom_buyer_id:
                frappe.throw(
                    "As per ZATCA regulations- For B2B Customers, customer CR number has to be provided"
                )
        address = None
        if customer_doc.custom_b2c != 1:
            if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
                if sales_invoice_doc.customer_address:
                    address = frappe.get_doc(
                        "Address", sales_invoice_doc.customer_address
                    )
            else:
                if customer_doc.customer_primary_address:
                    address = frappe.get_doc(
                        "Address", customer_doc.customer_primary_address
                    )

            if not address:
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Customer address is mandatory for non-B2C customers."
                    )
                )

            # ZATCA-required field validation
            if not address.address_line1:
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Address Line 1 is required in customer address."
                    )
                )
            if not address.address_line2:
                frappe.throw(
                    _(
                        "As per ZATCA regulations, Address Line 2 is required in customer address."
                    )
                )
            if address and address.country == SAUDI_ARABIA:
                if (
                    not address.custom_building_number
                    or not address.custom_building_number.isdigit()
                    or len(address.custom_building_number) != 4
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Building Number must be exactly 4 digits in customer address."
                        )
                    )
                if (
                    not address.pincode
                    or not address.pincode.isdigit()
                    or len(address.pincode) != 5
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Pincode must be exactly 5 digits in customer address."
                        )
                    )
            if address and address.country == SAUDI_ARABIA:
                if not customer_doc.tax_id:
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Tax ID is required for customers in Saudi Arabia."
                        )
                    )
                elif (
                    not customer_doc.tax_id.isdigit() or len(customer_doc.tax_id) != 15
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Customer Tax ID must be exactly 15 digits."
                        )
                    )
                elif not (
                    customer_doc.tax_id.startswith("3")
                    and customer_doc.tax_id.endswith("3")
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Customer Tax ID must start with 3 and end with 3."
                        )
                    )
        if "claudion4saudi" in frappe.get_installed_apps():
            if (
                hasattr(sales_invoice_doc, "custom_advances_copy")
                and sales_invoice_doc.custom_advances_copy
            ):
                if (
                    sales_invoice_doc.custom_advances_copy[0].reference_name
                    and customer_doc.custom_b2c == 1
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulations, Advance allocation is supported for non B2C customers. Please change the Customer type to B2B."
                        )
                    )

        if (
            sales_invoice_doc.custom_zatca_nominal_invoice == 1
            and sales_invoice_doc.get("additional_discount_percentage", 0.0) != 100
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations,Only a 100% discount is allowed for ZATCA nominal invoices."
                    " Please ensure the additional discount percentage is set to 100."
                )
            )
        if (
            sales_invoice_doc.custom_zatca_nominal_invoice == 1
            and sales_invoice_doc.get("custom_submit_line_item_discount_to_zatca")
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations, For nominal invoices, please disable line item discounts"
                    " by unchecking 'Submit Line Item Discount to ZATCA'."
                )
            )
        if len(tax_categories) > 1 and base_discount_amount > 0:
            frappe.throw(
                _(
                    "As per ZATCA regulations, ZATCA does not respond for multiple items with multiple tax categories "
                    "and a document-level discount. Please ensure all items have the same tax category."
                )
            )
        if (
            base_discount_amount > 0
            and sales_invoice_doc.apply_discount_on != "Net Total"
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulations,You cannot apply a discount on the Grand Total as the tax is already calculated. "
                    "Please apply your discount on the Net Total."
                )
            )
        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw(
                _(
                    f"Please save and submit the invoice before sending to ZATCA: {invoice_number}"
                )
            )
        if base_discount_amount < 0 and not sales_invoice_doc.is_return:
            frappe.throw(
                _(
                    "Additional discount cannot be negative. Please enter a positive value."
                )
            )
        if sales_invoice_doc.docstatus in [0, 2]:
            frappe.throw(
                _(
                    f"Please submit the invoice before sending to ZATCA: {invoice_number}"
                )
            )
        if sales_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw(
                _("This invoice has already been submitted to Zakat and Tax Authority.")
            )
        company_name = sales_invoice_doc.company
        settings = frappe.get_doc("Company", company_name)
        # if settings.custom_phase_1_or_2 == "Phase-2":
        is_gpos_installed = "gpos" in frappe.get_installed_apps()
        field_exists = frappe.get_meta("Sales Invoice").has_field("custom_unique_id")
        if is_gpos_installed:
            if sales_invoice_doc.custom_xml and not sales_invoice_doc.custom_qr_code:
                frappe.throw(
                    _(
                        "Please provide the 'qr_code' field data when have'xml' for invoice: "
                        + str(invoice_number)
                    )
                )
        if settings.custom_phase_1_or_2 == "Phase-2":

            if field_exists and sales_invoice_doc.custom_unique_id:
                if is_gpos_installed and sales_invoice_doc.custom_xml:
                    # Set the custom XML field
                    custom_xml_field = sales_invoice_doc.custom_xml
                    submit_sales_invoice_withxmlqr(
                        sales_invoice_doc, custom_xml_field, invoice_number
                    )
                else:
                    zatca_call_withoutxml(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
            else:
                if is_qr_and_xml_attached(sales_invoice_doc):
                    custom_xml_field = frappe.db.get_value(
                        "File",
                        {
                            "attached_to_doctype": sales_invoice_doc.doctype,
                            "attached_to_name": sales_invoice_doc.name,
                            "file_name": ["like", REPORTED_XML],
                        },
                        "file_url",
                    )
                    submit_sales_invoice_simplifeid(
                        sales_invoice_doc, custom_xml_field, invoice_number
                    )
                elif (
                    settings.custom_send_invoice_to_zatca == "Background"
                    and not bypass_background_check
                ):
                    zatca_call_scheduler_background(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
                else:

                    zatca_call(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )

        else:
            create_qr_code(sales_invoice_doc, method=None)
        doc.reload()
    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(_(f"Error in background call: {str(e)}"))


@frappe.whitelist()
def resubmit_invoices(invoice_numbers, bypass_background_check=False):
    """
    Resubmit invoices where custom_zatca_full_response contains 'RemoteDisconnected'.
    If the invoice is already submitted, call `zatca_background_on_submit`.
    Otherwise, submit the invoice.
    """
    if isinstance(invoice_numbers, str):
        invoice_numbers = frappe.parse_json(invoice_numbers)

    results = {}
    for invoice_number in invoice_numbers:
        try:
            # Fetch the Sales Invoice document
            sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
            company_doc = frappe.get_doc("Company", sales_invoice_doc.company)
            if (
                sales_invoice_doc.docstatus == 1
            ):  # Check if the invoice is already submitted
                # Call the zatca_background_on_submit function
                zatca_background_on_submit(
                    sales_invoice_doc, bypass_background_check=True
                )

            elif company_doc.custom_submit_or_not == 1:
                # Submit the invoice
                sales_invoice_doc.submit()
                zatca_background_on_submit(
                    sales_invoice_doc, bypass_background_check=True
                )

        except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
            frappe.throw(_(f"Error in background call: {str(e)}"))
            # Log errors and add to the results

    return results
