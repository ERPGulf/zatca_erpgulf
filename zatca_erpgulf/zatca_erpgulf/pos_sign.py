"""ZATCA E-Invoicing Integration for ERPNext
This module facilitates the generation, validation, and submission of
 ZATCA-compliant e-invoices for companies
using ERPNext. It supports compliance with the ZATCA requirements for Phase 2,
including the creation of UBL XML
invoices, signing, and submission to ZATCA servers for clearance and reporting."""

import base64
import json
import requests
from frappe import _
import frappe
from zatca_erpgulf.zatca_erpgulf.event_log import log_zatca_event
from zatca_erpgulf.zatca_erpgulf.posxml import (
    xml_tags,
    salesinvoice_data,
    add_document_level_discount_with_tax_template,
    add_document_level_discount_with_tax,
    invoice_typecode_simplified,
    invoice_typecode_standard,
    get_address,
    doc_reference,
    additional_reference,
    company_data,
    customer_data,
    delivery_and_paymentmeans,
    tax_data,
    invoice_typecode_compliance,
    delivery_and_paymentmeans_for_compliance,
    doc_reference_compliance,
)
from zatca_erpgulf.zatca_erpgulf.pos_final import (
    tax_data_with_template,
    item_data_with_template,
    item_data,
    xml_structuring,
)
from zatca_erpgulf.zatca_erpgulf.create_qr import create_qr_code

from zatca_erpgulf.zatca_erpgulf.sign_invoice import (
    xml_base64_decode,
    get_api_url,
    attach_qr_image,
    success_log,
    error_log,
)

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
from zatca_erpgulf.zatca_erpgulf.pos_submit_with_xml_qr import submit_pos_withxmlqr
from zatca_erpgulf.zatca_erpgulf.pos_submit__without_xml import (
    zatca_call_pos_without_xml,
)

from zatca_erpgulf.zatca_erpgulf.submit_poswithqr_notmultiple import (
    submit_pos_invoice_simplifeid,
)

from zatca_erpgulf.zatca_erpgulf.pos_schedule_background import (
    zatca_call_pos_without_xml_background,
)

ITEM_TAX_TEMPLATE_WARNING = "If any one item has an Item Tax Template,"
" all items must have an Item Tax Template."
CONTENT_TYPE_JSON = "application/json"


def reporting_api(
    uuid1, encoded_hash, signed_xmlfile_name, invoice_number, pos_invoice_doc
):
    """Function for reporting api"""
    try:
        # Retrieve the company abbreviation based on the company in the sales invoice
        company_abbr = frappe.db.get_value(
            "Company", {"name": pos_invoice_doc.company}, "abbr"
        )

        if not company_abbr:
            frappe.throw(
                _(f"Company with abbreviation {pos_invoice_doc.company} not found.")
            )

        # Retrieve the company document using the abbreviation
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})

        # Prepare the payload without JSON formatting
        xml_base64 = xml_base64_decode(signed_xmlfile_name)

        xml_cleared_data = base64.b64decode(xml_base64).decode("utf-8")
        file = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": "Reported xml file " + pos_invoice_doc.name + ".xml",
                "is_private": 1,
                "attached_to_doctype": pos_invoice_doc.doctype,
                "attached_to_name": pos_invoice_doc.name,
                "content": xml_cleared_data,
            }
        )
        file.is_private = 1
        file.save(ignore_permissions=True)
        pos_invoice_doc.db_set("custom_ksa_einvoicing_xml", file.file_url)
        if file.is_private == 0:
            frappe.db.set_value("File", file.name, "is_private", 1)
            frappe.db.commit()
        # file.reload()
        # frappe.throw(file.is_private)
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_xmlfile_name),
        }

        # Directly retrieve the production CSID from the company's document field
        if pos_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "ZATCA Multiple Setting", pos_invoice_doc.custom_zatca_pos_name
            )
            if zatca_settings.custom__use_company_certificate__keys != 1:
                production_csid = zatca_settings.custom_final_auth_csid
            else:
                linked_doc = frappe.get_doc("Company", zatca_settings.custom_linked_doctype)
                production_csid = linked_doc.custom_basic_auth_from_production
        else:
                production_csid = company_doc.custom_basic_auth_from_production
        if production_csid:
            headers = {
                "accept": CONTENT_TYPE_JSON,
                "accept-language": "en",
                "Clearance-Status": "0",
                "Accept-Version": "V2",
                "Authorization": "Basic " + production_csid,
                "Content-Type": CONTENT_TYPE_JSON,
                "Cookie": (
                    "TS0106293e=0132a679c0639d13d069bcba831384623a2ca6da47fac8d91bef610c47c7119d"
                    "cdd3b817f963ec301682dae864351c67ee3a402866"
                ),
            }
        else:
            headers = None
            frappe.throw(_(f"Production CSID for company {company_abbr} not found or mutiple setting page have no pcsid."))
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
                if response.status_code in (200, 202, 409):
                    if response.status_code == 200:
                            status_label = "Success"
                            title = f"ZATCA Success - {invoice_number}"
                    elif response.status_code == 202:
                        status_label = "Warning"
                        title = f"ZATCA Invoice with Warnings - {invoice_number}"
                    elif response.status_code == 409:
                        status_label = "Success (Duplicate Invoice)"
                        title = f"ZATCA Duplicate Success - {invoice_number}"

                    msg = (
                        f"Status Code: {response.status_code}<br>"
                        f"ZATCA Response: {response.text}"
                    )

                    log_zatca_event(
                        invoice_number=invoice_number,
                        response_text=msg,
                        status=status_label,
                        uuid=uuid1,
                        title=title
                    )

                else:
                    
                    status_label = f"Failed (HTTP {response.status_code})"
                    title = f"ZATCA API Failed - {invoice_number}"
                    msg = (
                        f"Status Code: {response.status_code}<br>"
                        f"ZATCA Response: {response.text}"
                    )
                    log_zatca_event(
                        invoice_number=invoice_number,
                        response_text=msg,
                        status=status_label,
                        uuid=uuid1,
                        title=title
                    )
                if response.status_code in (400, 405, 406):
                    invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
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
                                f"Status code: {response.status_code}<br><br> "
                                f"{response.text}"
                            )
                        )
                    )

                if response.status_code in (401, 403, 407, 451):
                    invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
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
                                "Error: ZATCA Authentication failed."
                                "Your access token may be expired or not valid. "
                                "Please contact your system administrator. "
                                f"Status code: {response.status_code}<br><br> "
                                f"{response.text}"
                            )
                        )
                    )
                if response.status_code == 409:
                    msg = "SUCCESS: <br><br>"
                    msg += (
                        f"Status Code: {response.status_code}<br><br> "
                        f"ZATCA Response: {response.text}<br><br>"
                    )

                    # Update PIH
                    if pos_invoice_doc.custom_zatca_pos_name:
                        zatca_settings = frappe.get_doc(
                            "ZATCA Multiple Setting", pos_invoice_doc.custom_zatca_pos_name
                        )
                        if zatca_settings.custom__use_company_certificate__keys != 1:
                            if zatca_settings.custom_send_pos_invoices_to_zatca_on_background:
                                frappe.msgprint(msg)
                            zatca_settings.custom_pih = encoded_hash
                            zatca_settings.save(ignore_permissions=True)
                        else:
                            linked_doc = frappe.get_doc("Company", zatca_settings.custom_linked_doctype)
                            if linked_doc.custom_send_einvoice_background:
                                frappe.msgprint(msg)
                            linked_doc.custom_pih = encoded_hash
                            linked_doc.save(ignore_permissions=True)
                    else:
                        company_doc = frappe.get_doc("Company", pos_invoice_doc.company)
                        if company_doc.custom_send_einvoice_background:
                            frappe.msgprint(msg)
                        company_doc.custom_pih = encoded_hash
                        company_doc.save(ignore_permissions=True)

                    invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
                    invoice_doc.custom_zatca_full_response = msg
                    invoice_doc.custom_uuid = uuid1
                    invoice_doc.custom_zatca_status = "REPORTED"
                    invoice_doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    

                    success_log(response.text, uuid1, invoice_number)
                
                if response.status_code not in (200, 202, 409):
                    invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
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
                                f"Status code: {response.status_code}<br><br> "
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
                        f"Status Code: {response.status_code}<br><br>"
                        f"ZATCA Response: {response.text}<br><br>"
                    )

                    company_name = pos_invoice_doc.company
                    if pos_invoice_doc.custom_zatca_pos_name:
                        if zatca_settings.custom__use_company_certificate__keys != 1:
                            if (
                                zatca_settings.custom_send_pos_invoices_to_zatca_on_background
                            ):
                                frappe.msgprint(msg)

                            # Update PIH data without JSON formatting
                            zatca_settings.custom_pih = encoded_hash
                            zatca_settings.save(ignore_permissions=True)
                        else: 
                            linked_doc = frappe.get_doc("Company", zatca_settings.custom_linked_doctype)
                            if linked_doc.custom_send_einvoice_background:
                                frappe.msgprint(msg)

                            # Update PIH data without JSON formatting
                            linked_doc.custom_pih = encoded_hash
                            linked_doc.save(ignore_permissions=True)

                    else:
                        settings = frappe.get_doc("Company", company_name)
                        company_abbr = settings.abbr
                        if settings.custom_send_einvoice_background:
                            frappe.msgprint(msg)

                        # Update PIH data without JSON formatting
                        company_doc.custom_pih = encoded_hash
                        company_doc.save(ignore_permissions=True)

                    invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
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
            except (ValueError, TypeError, KeyError) as e:
                frappe.throw(_(("Error in reporting API-2 Normal POS invoice" f"error: {str(e)}")))

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        invoice_doc.db_set(
            "custom_zatca_full_response",
            f"Error: {str(e)}",
            commit=True,
            update_modified=True,
        )
        frappe.throw(_(("Error in reporting API-1 " f"error: {str(e)}")))


def clearance_api(
    uuid1, encoded_hash, signed_xmlfile_name, invoice_number, pos_invoice_doc
):
    """Function for clearence api"""
    try:
        # Retrieve the company name based on the abbreviation in the POS Invoice
        company_abbr = frappe.db.get_value(
            "Company", {"name": pos_invoice_doc.company}, "abbr"
        )
        if not company_abbr:
            frappe.throw(
                _(
                    (
                        "There is a problem with company name in invoice "
                        f"{pos_invoice_doc.company} not found."
                    )
                )
            )

        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if pos_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "ZATCA Multiple Setting", pos_invoice_doc.custom_zatca_pos_name
            )
            if zatca_settings.custom__use_company_certificate__keys != 1:
                production_csid = zatca_settings.custom_final_auth_csid
            else:
                linked_doc = frappe.get_doc("Company", zatca_settings.custom_linked_doctype)
                production_csid = linked_doc.custom_basic_auth_from_production or ""
        else:
            production_csid = company_doc.custom_basic_auth_from_production or ""
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_xmlfile_name),
        }

        if production_csid:
            headers = {
                "accept": CONTENT_TYPE_JSON,
                "accept-language": "en",
                "Clearance-Status": "1",
                "Accept-Version": "V2",
                "Authorization": "Basic " + production_csid,
                "Content-Type": CONTENT_TYPE_JSON,
                "Cookie": (
                    "TS0106293e=0132a679c03c628e6c49de86c0f6bb76390abb4416868d6368d6d7c05da619c8"
                    "326266f5bc262b7c0c65a6863cd3b19081d64eee99"
                ),
            }
        else:
            headers = None
            frappe.throw(_(f"Production CSID for company {company_abbr} not found."))

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
        if response.status_code in (200, 202, 409):
            if response.status_code == 200:
                    status_label = "Success"
                    title = f"ZATCA Success - {invoice_number}"
            elif response.status_code == 202:
                status_label = "Warning"
                title = f"ZATCA Invoice with Warnings - {invoice_number}"
            elif response.status_code == 409:
                status_label = "Success (Duplicate Invoice)"
                title = f"ZATCA Duplicate Success - {invoice_number}"

            msg = (
                f"Status Code: {response.status_code}<br>"
                f"ZATCA Response: {response.text}"
            )

            log_zatca_event(
                invoice_number=invoice_number,
                response_text=msg,
                status=status_label,
                uuid=uuid1,
                title=title
            )

        else:
            
            status_label = f"Failed (HTTP {response.status_code})"
            title = f"ZATCA API Failed - {invoice_number}"
            msg = (
                f"Status Code: {response.status_code}<br>"
                f"ZATCA Response: {response.text}"
            )
            log_zatca_event(
                invoice_number=invoice_number,
                response_text=msg,
                status=status_label,
                uuid=uuid1,
                title=title
            )
        if response.status_code in (400, 405, 406, 409):
            invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
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
                        f"Status code: {response.status_code}<br><br>"
                        f"{response.text}"
                    )
                )
            )

        if response.status_code in (401, 403, 407, 451):
            invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
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
                        f"Status code: {response.status_code}<br><br>"
                        f"{response.text}"
                    )
                )
            )

        if response.status_code not in (200, 202):
            invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
            invoice_doc.db_set(
                "custom_uuid", "Not Submitted", commit=True, update_modified=True
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

            # frappe.msgprint(msg)
            company_name = pos_invoice_doc.company
            if pos_invoice_doc.custom_zatca_pos_name:
                if zatca_settings.custom__use_company_certificate__keys != 1:
                    if zatca_settings.custom_send_pos_invoices_to_zatca_on_background:
                        frappe.msgprint(msg)

                        # Update PIH data without JSON formatting
                    zatca_settings.custom_pih = encoded_hash
                    zatca_settings.save(ignore_permissions=True)
                else:
                    linked_doc = frappe.get_doc("Company", zatca_settings.custom_linked_doctype)
                    if linked_doc.custom_send_einvoice_background:
                        frappe.msgprint(msg)

                        # Update PIH data without JSON formatting
                    linked_doc.custom_pih = encoded_hash
                    linked_doc.save(ignore_permissions=True)

            else:
                settings = frappe.get_doc("Company", company_name)
                company_abbr = settings.abbr
                if settings.custom_send_einvoice_background:
                    frappe.msgprint(msg)

                    # Update PIH data without JSON formatting
                company_doc.custom_pih = encoded_hash
                company_doc.save(ignore_permissions=True)

            invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
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
                    "file_name": "Cleared xml file " + pos_invoice_doc.name + ".xml",
                    "is_private": 1,  # Ensure this is explicitly set
                    "attached_to_doctype": pos_invoice_doc.doctype,
                    "attached_to_name": pos_invoice_doc.name,
                    "content": xml_cleared,
                }
            )

            file.is_private = 1  # Force private before saving
            file.save(ignore_permissions=True)
            if file.is_private == 0:
                frappe.db.set_value("File", file.name, "is_private", 1)
                frappe.db.commit()

            success_log(response.text, uuid1, invoice_number)
            return xml_cleared
        else:
            error_log()
            return None

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
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
        frappe.throw(_(("Error in clearance API " f"error: {str(e)}")))
        return None


# @frappe.whitelist(allow_guest=False)
def zatca_call(
    invoice_number,
    compliance_type="0",
    any_item_has_tax_template=False,
    company_abbr=None,
    source_doc=None,
):
    """Function for zatca call"""
    try:

        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw(_("Invoice Number is NOT Valid:" + str(invoice_number)))

        invoice = xml_tags()
        invoice, uuid1, pos_invoice_doc = salesinvoice_data(invoice, invoice_number)

        # Get the company abbreviation
        company_abbr = frappe.db.get_value(
            "Company", {"name": pos_invoice_doc.company}, "abbr"
        )

        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                invoice = invoice_typecode_simplified(invoice, pos_invoice_doc)
            else:
                invoice = invoice_typecode_standard(invoice, pos_invoice_doc)
        else:
            invoice = invoice_typecode_compliance(invoice, compliance_type)

        invoice = doc_reference(invoice, pos_invoice_doc, invoice_number)
        invoice = additional_reference(invoice, company_abbr, pos_invoice_doc)
        invoice = company_data(invoice, pos_invoice_doc)
        invoice = customer_data(invoice, pos_invoice_doc)
        invoice = delivery_and_paymentmeans(
            invoice, pos_invoice_doc, pos_invoice_doc.is_return
        )
        if not any_item_has_tax_template:
            invoice = add_document_level_discount_with_tax(invoice, pos_invoice_doc)
        else:
            invoice = add_document_level_discount_with_tax_template(
                invoice, pos_invoice_doc
            )

        if not any_item_has_tax_template:
            invoice = tax_data(invoice, pos_invoice_doc)
        else:
            invoice = tax_data_with_template(invoice, pos_invoice_doc)

        if not any_item_has_tax_template:
            invoice = item_data(invoice, pos_invoice_doc)
        else:
            invoice = item_data_with_template(invoice, pos_invoice_doc)

        file_content = xml_structuring(invoice)

        # try:
        #     with open(
        #         f"{frappe.local.site}/private/files/finalzatcaxml_{invoice_number}.xml",
        #         "r",
        #         encoding="utf-8",
        #     ) as file:
        #         file_content = file.read()
        # except FileNotFoundError:
        #     frappe.throw("XML file not found")

        tag_removed_xml = removetags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash1, encoded_hash = getinvoicehash(canonicalized_xml)
        encoded_signature = digital_signature(hash1, company_abbr, source_doc)
        issuer_name, serial_number = extract_certificate_details(
            company_abbr, source_doc
        )
        encoded_certificate_hash = certificate_hash(company_abbr, source_doc)
        modified_xml_string,namespaces, signing_time = signxml_modify(company_abbr,file_content, source_doc)
        signed_properties_base64 = generate_signed_properties_hash(
            signing_time, issuer_name, serial_number, encoded_certificate_hash
        )
        final_xml_string = populate_the_ubl_extensions_output(
            modified_xml_string,
            encoded_signature,
            namespaces,
            signed_properties_base64,
            encoded_hash,
            company_abbr,
            source_doc,
        )
        tlv_data = generate_tlv_xml(final_xml_string, company_abbr, source_doc)

        tagsbufsarray = []
        for tag_num, tag_value in tlv_data.items():
            tagsbufsarray.append(get_tlv_for_value(tag_num, tag_value))

        qrcodebuf = b"".join(tagsbufsarray)
        qrcodeb64 = base64.b64encode(qrcodebuf).decode("utf-8")
        updated_xml_string = update_qr_toxml(final_xml_string, qrcodeb64, company_abbr)
        signed_xmlfile_name = structuring_signedxml(invoice_number,updated_xml_string)

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                attach_qr_image(qrcodeb64, pos_invoice_doc)
                reporting_api(
                    uuid1,
                    encoded_hash,
                    signed_xmlfile_name,
                    invoice_number,
                    pos_invoice_doc,
                )

            else:
                clearance_api(
                    uuid1,
                    encoded_hash,
                    signed_xmlfile_name,
                    invoice_number,
                    pos_invoice_doc,
                )
                attach_qr_image(qrcodeb64, pos_invoice_doc)
        else:
            compliance_api_call(
                uuid1, encoded_hash, signed_xmlfile_name, company_abbr, source_doc
            )
            attach_qr_image(qrcodeb64, pos_invoice_doc)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.log_error(
            title="ZATCA invoice call failed",
            message=f"{frappe.get_traceback()} \n Error: {str(e)}",
        )


# @frappe.whitelist(allow_guest=False)
def zatca_call_compliance(
    invoice_number,
    company_abbr,
    compliance_type="0",
    any_item_has_tax_template=False,
    source_doc=None,
):
    """Function for zatca call compliance"""

    try:

        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")

        if not company_name:
            frappe.throw(_(f"Company with abbreviation {company_abbr} not found."))

        company_doc = frappe.get_doc("Company", company_name)

        # Determine compliance type based on company settings
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
        # Validate the invoice number
        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw(_("Invoice Number is NOT Valid1:" + str(invoice_number)))

        # Fetch and process the sales invoice data
        invoice = xml_tags()
        invoice, uuid1, pos_invoice_doc = salesinvoice_data(invoice, invoice_number)
        # Check if any item has a tax template and validate it
        any_item_has_tax_template = any(
            item.item_tax_template for item in pos_invoice_doc.items
        )
        if any_item_has_tax_template and not all(
            item.item_tax_template for item in pos_invoice_doc.items
        ):
            frappe.throw(_(ITEM_TAX_TEMPLATE_WARNING))

        invoice = invoice_typecode_compliance(invoice, compliance_type)
        invoice = doc_reference_compliance(
            invoice, pos_invoice_doc, invoice_number, compliance_type
        )
        invoice = additional_reference(invoice, company_abbr, pos_invoice_doc)
        invoice = company_data(invoice, pos_invoice_doc)
        invoice = customer_data(invoice, pos_invoice_doc)
        invoice = delivery_and_paymentmeans_for_compliance(
            invoice, pos_invoice_doc, compliance_type
        )
        if not any_item_has_tax_template:
            invoice = add_document_level_discount_with_tax(invoice, pos_invoice_doc)
        else:
            invoice = add_document_level_discount_with_tax_template(
                invoice, pos_invoice_doc
            )

        # Add tax and item data
        if not any_item_has_tax_template:
            invoice = tax_data(invoice, pos_invoice_doc)
        else:
            invoice = tax_data_with_template(invoice, pos_invoice_doc)

        if not any_item_has_tax_template:
            invoice = item_data(invoice, pos_invoice_doc)
        else:
            item_data_with_template(invoice, pos_invoice_doc)

        # Generate and process the XML data
        file_content = xml_structuring(invoice)
        # with open(
        #     f"{frappe.local.site}/private/files/finalzatcaxml_{invoice_number}.xml",
        #     "r",
        #     encoding="utf-8",
        # ) as file:
        #     file_content = file.read()

        tag_removed_xml = removetags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash1, encoded_hash = getinvoicehash(canonicalized_xml)
        encoded_signature = digital_signature(hash1, company_abbr, source_doc)
        issuer_name, serial_number = extract_certificate_details(
            company_abbr, source_doc
        )
        encoded_certificate_hash = certificate_hash(company_abbr, source_doc)
        modified_xml_string, namespaces, signing_time = signxml_modify(company_abbr,file_content, source_doc)
        signed_properties_base64 = generate_signed_properties_hash(
            signing_time, issuer_name, serial_number, encoded_certificate_hash
        )
        final_xml_string= populate_the_ubl_extensions_output(
            modified_xml_string,
            encoded_signature,
            namespaces,
            signed_properties_base64,
            encoded_hash,
            company_abbr,
            source_doc,
        )

        # Generate the TLV data and QR code
        tlv_data = generate_tlv_xml(final_xml_string, company_abbr, source_doc)

        tagsbufsarray = []
        for tag_num, tag_value in tlv_data.items():
            tagsbufsarray.append(get_tlv_for_value(tag_num, tag_value))

        qrcodebuf = b"".join(tagsbufsarray)
        qrcodeb64 = base64.b64encode(qrcodebuf).decode("utf-8")

        updated_xml_string = update_qr_toxml(final_xml_string, qrcodeb64, company_abbr)
        signed_xmlfile_name = structuring_signedxml(invoice_number,updated_xml_string)

        # Make the compliance API call
        compliance_api_call(
            uuid1, encoded_hash, signed_xmlfile_name, company_abbr, source_doc
        )

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.log_error(
            title="ZATCA invoice call failed",
            message=f"{frappe.get_traceback()} \n Error: {str(e)}",
        )
        frappe.throw(_("Error in ZATCA invoice call: " + str(e)))


@frappe.whitelist(allow_guest=False)
def zatca_background_(invoice_number:str, source_doc:str=None, bypass_background_check:bool=False):
    """Function for zatca background"""
    try:
        if source_doc:
            source_doc = frappe.get_doc(
                json.loads(source_doc)
            )  # Deserialize if sent as JSON

        pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        company_name = pos_invoice_doc.company

        settings = frappe.get_doc("Company", company_name)
        company_abbr = settings.abbr

        any_item_has_tax_template = any(
            item.item_tax_template for item in pos_invoice_doc.items
        )
        if any_item_has_tax_template and not all(
            item.item_tax_template for item in pos_invoice_doc.items
        ):
            frappe.throw(_(ITEM_TAX_TEMPLATE_WARNING))

        pos_profile = pos_invoice_doc.pos_profile
        if not pos_profile:
            frappe.throw(_("POS Profile is not set in the POS Invoice."))
        pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
        taxes_and_charges = pos_profile_doc.taxes_and_charges
        taxes_template_doc = frappe.get_doc(
            "Sales Taxes and Charges Template", taxes_and_charges
        )

        tax_rate = taxes_template_doc.taxes[0]
        if tax_rate and tax_rate.included_in_print_rate == 1:
            if any(item.item_tax_template for item in pos_invoice_doc.items):
                frappe.throw(
                    _(
                        "As per ZATCA regulation,Item Tax Template cannot be used when taxes are included in "
                        "the print rate. Please remove Item Tax Templates."
                    )
                )
        tax_categories = set()
        for item in pos_invoice_doc.items:
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
                                "As per ZATCA regulation, ZATCA tax category should be 'Zero Rated', 'Exempted' or "
                                "'Services outside scope of tax / Not subject to VAT' for items with "
                                "tax rate not equal to 5.00 or 15.00."
                            )
                        )

                    if (
                        f"{tax_rate:.2f}" == "15.00"
                        and zatca_tax_category != "Standard"
                    ):
                        frappe.throw(
                            _(
                                "As per ZATCA regulation, Check the ZATCA category code and enable it as standard."
                            )
                        )
        address = None
        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)
        if customer_doc.custom_b2c == 0:
            if not customer_doc.custom_buyer_id:
                frappe.throw(_(
                    "As per ZATCA regulation- For B2B Customers, customer CR number has to be provided"
                ))
        if customer_doc.custom_b2c != 1:
            if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
                if pos_invoice_doc.customer_address:
                    address = frappe.get_doc(
                        "Address", pos_invoice_doc.customer_address
                    )
            else:
                if customer_doc.customer_primary_address:
                    address = frappe.get_doc(
                        "Address", customer_doc.customer_primary_address
                    )

            if not address:
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Customer address is mandatory for non-B2C customers."
                    )
                )

            # ZATCA-required field validation
            if not address.address_line1:
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Address Line 1 is required in customer address."
                    )
                )
            if not address.address_line2:
                frappe.throw(
                    _(
                        "As per ZATCA regulation,Address Line 2 is required in customer address."
                    )
                )
            if (
                not address.custom_building_number
                or not address.custom_building_number.isdigit()
                or len(address.custom_building_number) != 4
            ):
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Building Number must be exactly 4 digits in customer address."
                    )
                )
            if (
                not address.pincode
                or not address.pincode.isdigit()
                or len(address.pincode) != 5
            ):
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Pincode must be exactly 5 digits in customer address."
                    )
                )
            if address and address.country == "Saudi Arabia":
                if not customer_doc.tax_id:
                    frappe.throw(
                        _(
                            "As per ZATCA regulation, Tax ID is required for customers in Saudi Arabia."
                        )
                    )
                elif (
                    not customer_doc.tax_id.isdigit() or len(customer_doc.tax_id) != 15
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulation, Customer Tax ID must be exactly 15 digits."
                        )
                    )

        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if not company_doc.tax_id:
            frappe.throw(_("As per ZATCA regulation, Company Tax ID is mandatory"))
        if company_doc.tax_id and not (
            company_doc.tax_id.isdigit() and len(company_doc.tax_id) == 15
        ):
            frappe.throw(
                _("As per ZATCA regulation, Company Tax ID must be a 15-digit number")
            )
        address = get_address(pos_invoice_doc, company_doc)
        if not address.address_line1:
            frappe.throw(
                _(
                    "As per ZATCA regulation, Address Line 1 is required in the company address."
                )
            )

        if not address.address_line2:
            frappe.throw(
                _(
                    "As per ZATCA regulation, Address Line 2 is required in the company address."
                )
            )

        if (
            not address.custom_building_number
            or not address.custom_building_number.isdigit()
            or len(address.custom_building_number) != 4
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulation, Building Number must be exactly 4 digitsin company address."
                )
            )

        if (
            not address.pincode
            or not address.pincode.isdigit()
            or len(address.pincode) != 5
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulation,Pincode must be exactly 5 digits in company address."
                )
            )
        base_discount_amount = pos_invoice_doc.get("base_discount_amount", 0.0)
        if len(tax_categories) > 1 and base_discount_amount > 0:
            frappe.throw(
                _(
                    "As per ZATCA regulation, ZATCA does not respond for multiple items with multiple tax categories"
                    " with doc-level discount. Please ensure all items have the same tax category."
                )
            )
        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw(
                _(
                    "Please save and submit the invoice before sending to ZATCA: "
                    + str(invoice_number)
                )
            )
        if base_discount_amount < 0:
            frappe.throw(
                _(
                    "Additional discount cannot be negative. Please enter a positive value."
                )
            )

        if pos_invoice_doc.docstatus in [0, 2]:
            frappe.throw(
                _(
                    "Please submit the invoice before sending to ZATCA: "
                    + str(invoice_number)
                )
            )

        if pos_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw(_("Already submitted to Zakat and Tax Authority"))

        if settings.custom_zatca_invoice_enabled != 1:
            frappe.throw(
                _(
                    "ZATCA Invoice is not enabled in Company Settings, "
                    "Please contact your system administrator"
                )
            )

        # if settings.custom_phase_1_or_2 == "Phase-2":
        is_gpos_installed = "gpos" in frappe.get_installed_apps()
        field_exists = frappe.get_meta("POS Invoice").has_field("custom_unique_id")
        if is_gpos_installed:
            if pos_invoice_doc.custom_xml and not pos_invoice_doc.custom_qr_code:
                frappe.throw(
                    _(
                        "Please provide the 'qr_code' field data when 'custom_xml' is filled for invoice: "
                        + str(invoice_number)
                    )
                )
        if settings.custom_phase_1_or_2 == "Phase-2":
            if field_exists and pos_invoice_doc.custom_unique_id:
                if not pos_invoice_doc.custom_zatca_pos_name:
                    frappe.throw(_("pos name required"))
                if is_gpos_installed and pos_invoice_doc.custom_xml:
                    # Set the custom XML field
                    custom_xml_field = pos_invoice_doc.custom_xml
                    submit_pos_withxmlqr(
                        pos_invoice_doc, custom_xml_field, invoice_number
                    )
                else:
                    zatca_call_pos_without_xml(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
            else:
                if is_qr_and_xml_attached(pos_invoice_doc):
                    custom_xml_field = frappe.db.get_value(
                        "File",
                        {
                            "attached_to_doctype": pos_invoice_doc.doctype,
                            "attached_to_name": pos_invoice_doc.name,
                            "file_name": ["like", "%Reported xml file%"],
                        },
                        "file_url",
                    )
                    submit_pos_invoice_simplifeid(
                        pos_invoice_doc, custom_xml_field, invoice_number
                    )
                elif (
                    settings.custom_send_invoice_to_zatca == "Background"
                    and not bypass_background_check and customer_doc.custom_b2c == 1
                ):
                    zatca_call_pos_without_xml_background(
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
            create_qr_code(pos_invoice_doc, method=None)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(_("Error in background call: " + str(e)))


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
            "file_name": ["like", "%Reported xml file%"],
        },
        "file_url",
    )

    # Ensure both files exist before confirming attachment
    return is_file_attached(qr_code) and is_file_attached(xml_file)


@frappe.whitelist(allow_guest=False)
def zatca_background_on_submit(doc: "dict | str", _method:  str | None = None, bypass_background_check:bool =False):
    """Function for zatca background on submit"""

    try:
        source_doc = doc
        pos_invoice_doc = doc
        invoice_number = pos_invoice_doc.name
        pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        company_abbr = frappe.db.get_value(
            "Company", {"name": pos_invoice_doc.company}, "abbr"
        )

        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if not company_abbr:
            frappe.throw(
                _(f"Company abbreviation for {pos_invoice_doc.company} not found.")
            )
        if company_doc.custom_zatca_invoice_enabled != 1:
            # frappe.msgprint("Zatca Invoice is not enabled. Submitting the document.")
            return 
        
        if company_doc.tax_id and customer_doc.tax_id:
            if company_doc.tax_id.strip() == customer_doc.tax_id.strip():
                pos_invoice_doc.custom_zatca_status = "Intra-company transfer"
                pos_invoice_doc.custom_zatca_full_response = "Intra-company transfer"
                pos_invoice_doc.save(ignore_permissions=True)
                frappe.db.commit()
                return

        if not customer_doc.custom_buyer_id_type and customer_doc.custom_buyer_id:
            frappe.throw(_("Buyer ID must be blank if Buyer ID Type is not set."))
        any_item_has_tax_template = False

        for item in pos_invoice_doc.items:
            if item.item_tax_template:
                any_item_has_tax_template = True
                break

        if any_item_has_tax_template:
            for item in pos_invoice_doc.items:
                if not item.item_tax_template:
                    frappe.throw(_(ITEM_TAX_TEMPLATE_WARNING))

        pos_profile = pos_invoice_doc.pos_profile
        if not pos_profile:
            frappe.throw(_("POS Profile is not set in the POS Invoice."))
        pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
        taxes_and_charges = pos_profile_doc.taxes_and_charges
        taxes_template_doc = frappe.get_doc(
            "Sales Taxes and Charges Template", taxes_and_charges
        )

        tax_rate = taxes_template_doc.taxes[0]
        if tax_rate and tax_rate.included_in_print_rate == 1:
            if any(item.item_tax_template for item in pos_invoice_doc.items):
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Item Tax Template cannot be used when taxes are included in "
                        "the print rate. Please remove Item Tax Templates."
                    )
                )
        tax_categories = set()
        for item in pos_invoice_doc.items:
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
                                "As per ZATCA regulation, ZATCA tax category should be 'Zero Rated', 'Exempted' or "
                                "'Services outside scope of tax / Not subject to VAT' for items with "
                                "tax rate not equal to 5.00 or 15.00."
                            )
                        )

                    if (
                        f"{tax_rate:.2f}" == "15.00"
                        and zatca_tax_category != "Standard"
                    ):
                        frappe.throw(
                            _(
                                "As per ZATCA regulation,Check the ZATCA category code and enable it as standard."
                            )
                        )

        address = None
        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)
        if customer_doc.custom_b2c == 0:
            if not customer_doc.custom_buyer_id:
                frappe.throw(_(
                    "As per ZATCA regulation- For B2B Customers, customer CR number has to be provided"
                ))
        if customer_doc.custom_b2c != 1:
            if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
                if pos_invoice_doc.customer_address:
                    address = frappe.get_doc(
                        "Address", pos_invoice_doc.customer_address
                    )
            else:
                if customer_doc.customer_primary_address:
                    address = frappe.get_doc(
                        "Address", customer_doc.customer_primary_address
                    )

            if not address:
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Customer address is mandatory for non-B2C customers."
                    )
                )

            # ZATCA-required field validation
            if not address.address_line1:
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Address Line 1 is required in customer address."
                    )
                )
            if not address.address_line2:
                frappe.throw(
                    _(
                        "As per ZATCA regulation,Address Line 2 is required in customer address."
                    )
                )
            if (
                not address.custom_building_number
                or not address.custom_building_number.isdigit()
                or len(address.custom_building_number) != 4
            ):
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Building Number must be exactly 4 digits in customer address."
                    )
                )
            if (
                not address.pincode
                or not address.pincode.isdigit()
                or len(address.pincode) != 5
            ):
                frappe.throw(
                    _(
                        "As per ZATCA regulation, Pincode must be exactly 5 digits in customer address."
                    )
                )
            if address and address.country == "Saudi Arabia":
                if not customer_doc.tax_id:
                    frappe.throw(
                        _(
                            "As per ZATCA regulation, Tax ID is required for customers in Saudi Arabia."
                        )
                    )
                elif (
                    not customer_doc.tax_id.isdigit() or len(customer_doc.tax_id) != 15
                ):
                    frappe.throw(
                        _(
                            "As per ZATCA regulation, Customer Tax ID must be exactly 15 digits."
                        )
                    )

        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if not company_doc.tax_id:
            frappe.throw(_("As per ZATCA regulation, Company Tax ID is mandatory"))
        if company_doc.tax_id and not (
            company_doc.tax_id.isdigit() and len(company_doc.tax_id) == 15
        ):
            frappe.throw(
                _("As per ZATCA regulation, Company Tax ID must be a 15-digit number")
            )
        address = get_address(pos_invoice_doc, company_doc)
        if not address.address_line1:
            frappe.throw(
                _(
                    "As per ZATCA regulation, Address Line 1 is required in the company address."
                )
            )

        if not address.address_line2:
            frappe.throw(
                _(
                    "As per ZATCA regulation, Address Line 2 is required in the company address."
                )
            )

        if (
            not address.custom_building_number
            or not address.custom_building_number.isdigit()
            or len(address.custom_building_number) != 4
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulation, Building Number must be exactly 4 digitsin company address."
                )
            )

        if (
            not address.pincode
            or not address.pincode.isdigit()
            or len(address.pincode) != 5
        ):
            frappe.throw(
                _(
                    "As per ZATCA regulation,Pincode must be exactly 5 digits in company address."
                )
            )
        base_discount_amount = pos_invoice_doc.get("base_discount_amount", 0.0)
        if len(tax_categories) > 1 and base_discount_amount > 0:
            frappe.throw(
                _(
                    "As per ZATCA regulation, ZATCA does not respond for multiple items with multiple tax categories "
                    "with doc-level discount. Please ensure all items have the same tax category."
                )
            )
        # Check if Zatca Invoice is enabled in the Company document

        if company_doc.custom_zatca_invoice_enabled != 1:
            frappe.throw(
                _(
                    "ZATCA Invoice is not enabled in the Company settings,"
                    " Please contact your system administrator"
                )
            )

        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw(
                _(
                    "Please save and submit the invoice before sending to ZATCA:  "
                    + str(invoice_number)
                )
            )
        if base_discount_amount < 0:
            frappe.throw(
                _(
                    "Additional discount cannot be negative. Please enter a positive value."
                )
            )

        if pos_invoice_doc.docstatus in [0, 2]:
            frappe.throw(
                _(
                    "Please submit the invoice before sending to ZATCA:  "
                    + str(invoice_number)
                )
            )

        if pos_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw(_("Already submitted to Zakat and Tax Authority"))
        company_name = pos_invoice_doc.company

        # Retrieve the company document to access settings
        settings = frappe.get_doc("Company", company_name)
        # if settings.custom_phase_1_or_2 == "Phase-2":
        #     zatca_call(
        #         invoice_number, "0", any_item_has_tax_template, company_abbr, source_doc
        #     )
        # else:
        #     create_qr_code(pos_invoice_doc, method=None)
        settings = frappe.get_doc("Company", company_name)

        is_gpos_installed = "gpos" in frappe.get_installed_apps()
        field_exists = frappe.get_meta("POS Invoice").has_field("custom_unique_id")
        if is_gpos_installed:
            if pos_invoice_doc.custom_xml and not pos_invoice_doc.custom_qr_code:
                frappe.throw(
                    _(
                        "Please provide the 'qr_code' field data when 'custom_xml' is filled for invoice: "
                        + str(invoice_number)
                    )
                )
        if settings.custom_phase_1_or_2 == "Phase-2":
            if field_exists and pos_invoice_doc.custom_unique_id:
                if not pos_invoice_doc.custom_zatca_pos_name:
                    frappe.throw(_("pos name required"))
                if is_gpos_installed and pos_invoice_doc.custom_xml:
                    # Set the custom XML field
                    custom_xml_field = pos_invoice_doc.custom_xml
                    submit_pos_withxmlqr(
                        pos_invoice_doc, custom_xml_field, invoice_number
                    )
                else:
                    zatca_call_pos_without_xml(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
            else:
                if is_qr_and_xml_attached(pos_invoice_doc):
                    custom_xml_field = frappe.db.get_value(
                        "File",
                        {
                            "attached_to_doctype": pos_invoice_doc.doctype,
                            "attached_to_name": pos_invoice_doc.name,
                            "file_name": ["like", "%Reported xml file%"],
                        },
                        "file_url",
                    )
                    # frappe.throw("custom_xml_field: " + str(custom_xml_field))
                    submit_pos_invoice_simplifeid(
                        pos_invoice_doc, custom_xml_field, invoice_number
                    )
                elif (
                    settings.custom_send_invoice_to_zatca == "Background"
                    and not bypass_background_check and customer_doc.custom_b2c == 1
                ):
                    zatca_call_pos_without_xml_background(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
                else:
                    # Handle the case where custom_unique_id is missing
                    zatca_call(
                        invoice_number,
                        "0",
                        any_item_has_tax_template,
                        company_abbr,
                        source_doc,
                    )
        else:
            # If not Phase-2, create a QR code
            create_qr_code(pos_invoice_doc, method=None)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(_("Error in background call submit: " + str(e)))


@frappe.whitelist()
def resubmit_invoices_pos(invoice_numbers:str, bypass_background_check:bool=False):
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
            pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
            company_doc = frappe.get_doc("Company", pos_invoice_doc.company)
            customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)


            if (
                pos_invoice_doc.docstatus == 1
            ):  # Check if the invoice is already submitted
                # Call the zatca_background_on_submit function
                zatca_background_on_submit(
                    pos_invoice_doc, bypass_background_check=True
                )

            # elif company_doc.custom_submit_or_not == 1:
            elif (
                pos_invoice_doc.docstatus == 0
                and company_doc.custom_submit_or_not == 1
                and customer_doc.custom_b2c == 1
            ):
                pos_invoice_doc.submit()
                # zatca_background_on_submit(
                #     pos_invoice_doc, bypass_background_check=True
                # )

        except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
            frappe.throw(_(f"Error in background call: {str(e)}"))
            # Log errors and add to the results

    return results
