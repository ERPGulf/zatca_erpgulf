"""ZATCA E-Invoicing Integration for ERPNext
This module facilitates the generation, validation, and submission of
 ZATCA-compliant e-invoices for companies 
using ERPNext. It supports compliance with the ZATCA requirements for Phase 2, 
including the creation of UBL XML 
invoices, signing, and submission to ZATCA servers for clearance and reporting."""

import base64
import json
import requests
import frappe
from zatca_erpgulf.zatca_erpgulf.posxml import (
    xml_tags,
    salesinvoice_data,
    add_document_level_discount_with_tax_template,
    add_document_level_discount_with_tax,
    invoice_typecode_simplified,
    invoice_typecode_standard,
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
                f"Company with abbreviation {pos_invoice_doc.company} not found."
            )

        # Retrieve the company document using the abbreviation
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})

        # Prepare the payload without JSON formatting
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_xmlfile_name),
        }

        # Directly retrieve the production CSID from the company's document field
        if pos_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "Zatca Multiple Setting", pos_invoice_doc.custom_zatca_pos_name
            )
            production_csid = zatca_settings.custom_final_auth_csid
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
            frappe.throw(f"Production CSID for company {company_abbr} not found.")

        try:
            frappe.publish_realtime(
                "show_gif", {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"}
            )
            response = requests.post(
                url=get_api_url(company_abbr, base_url="invoices/reporting/single"),
                headers=headers,
                json=payload,
                timeout=30,
            )
            frappe.publish_realtime("hide_gif")
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
                    (
                        "Error: The request you are sending to Zatca is in incorrect format. "
                        "Please report to system administrator. "
                        f"Status code: {response.status_code}<br><br> "
                        f"{response.text}"
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
                    (
                        "Error: Zatca Authentication failed."
                        "Your access token may be expired or not valid. "
                        "Please contact your system administrator. "
                        f"Status code: {response.status_code}<br><br> "
                        f"{response.text}"
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
                    (
                        "Error: Zatca server busy or not responding."
                        " Try after sometime or contact your system administrator. "
                        f"Status code: {response.status_code}<br><br> "
                        f"{response.text}"
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
                    f"Zatca Response: {response.text}<br><br>"
                )

                company_name = pos_invoice_doc.company
                if pos_invoice_doc.custom_zatca_pos_name:
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

                invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
                invoice_doc.db_set(
                    "custom_zatca_full_response", msg, commit=True, update_modified=True
                )
                invoice_doc.db_set(
                    "custom_uuid", uuid1, commit=True, update_modified=True
                )
                invoice_doc.db_set(
                    "custom_zatca_status", "REPORTED", commit=True, update_modified=True
                )

                xml_base64 = xml_base64_decode(signed_xmlfile_name)

                xml_cleared_data = base64.b64decode(xml_base64).decode("utf-8")
                file = frappe.get_doc(
                    {
                        "doctype": "File",
                        "file_name": "Reported xml file "
                        + pos_invoice_doc.name
                        + ".xml",
                        "attached_to_doctype": pos_invoice_doc.doctype,
                        "attached_to_name": pos_invoice_doc.name,
                        "content": xml_cleared_data,
                    }
                )

                file.save(ignore_permissions=True)
                success_log(response.text, uuid1, invoice_number)
            else:
                error_log()
        except (ValueError, TypeError, KeyError) as e:
            frappe.throw(("Error in reporting API-2 " f"error: {str(e)}"))

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(("Error in reporting API-1 " f"error: {str(e)}"))


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
                (
                    "There is a problem with company name in invoice "
                    f"{pos_invoice_doc.company} not found."
                )
            )

        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if pos_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "Zatca Multiple Setting", pos_invoice_doc.custom_zatca_pos_name
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
            frappe.throw(f"Production CSID for company {company_abbr} not found.")

        frappe.publish_realtime(
            "show_gif", {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"}
        )
        response = requests.post(
            url=get_api_url(company_abbr, base_url="invoices/clearance/single"),
            headers=headers,
            json=payload,
            timeout=30,
        )
        frappe.publish_realtime("hide_gif")
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
                (
                    "Error: The request you are sending to Zatca is in incorrect format. "
                    f"Status code: {response.status_code}<br><br>"
                    f"{response.text}"
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
                (
                    "Error: Zatca Authentication failed. "
                    f"Status code: {response.status_code}<br><br>"
                    f"{response.text}"
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
                f"Error: Zatca server busy or not responding. Status code: {response.status_code}"
            )

        if response.status_code in (200, 202):
            msg = (
                "CLEARED WITH WARNINGS: <br><br>"
                if response.status_code == 202
                else "SUCCESS: <br><br>"
            )
            msg += (
                f"Status Code: {response.status_code}<br><br>"
                f"Zatca Response: {response.text}<br><br>"
            )

            # frappe.msgprint(msg)
            company_name = pos_invoice_doc.company
            if pos_invoice_doc.custom_zatca_pos_name:
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
                    "attached_to_doctype": pos_invoice_doc.doctype,
                    "attached_to_name": pos_invoice_doc.name,
                    "content": xml_cleared,
                }
            )
            file.save(ignore_permissions=True)

            success_log(response.text, uuid1, invoice_number)
            return xml_cleared
        else:
            error_log()
            return None

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(("Error in clearance API " f"error: {str(e)}"))
        return None


@frappe.whitelist(allow_guest=False)
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
            frappe.throw("Invoice Number is NOT Valid: " + str(invoice_number))

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

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                reporting_api(
                    uuid1,
                    encoded_hash,
                    signed_xmlfile_name,
                    invoice_number,
                    pos_invoice_doc,
                )
                attach_qr_image(qrcodeb64, pos_invoice_doc)
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
            compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name, company_abbr)
            attach_qr_image(qrcodeb64, pos_invoice_doc)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.log_error(
            title="Zatca invoice call failed",
            message=f"{frappe.get_traceback()} \n Error: {str(e)}",
        )


@frappe.whitelist(allow_guest=False)
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
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

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
            frappe.throw("Invoice Number is NOT Valid: " + str(invoice_number))

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
            frappe.throw(ITEM_TAX_TEMPLATE_WARNING)

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

        # Make the compliance API call
        compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name, company_abbr)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.log_error(
            title="Zatca invoice call failed",
            message=f"{frappe.get_traceback()} \n Error: {str(e)}",
        )
        frappe.throw("Error in Zatca invoice call: " + str(e))


@frappe.whitelist(allow_guest=False)
def zatca_background_(invoice_number, source_doc):
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
            frappe.throw(ITEM_TAX_TEMPLATE_WARNING)

        pos_profile = pos_invoice_doc.pos_profile
        if not pos_profile:
            frappe.throw("POS Profile is not set in the POS Invoice.")
        pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
        taxes_and_charges = pos_profile_doc.taxes_and_charges
        taxes_template_doc = frappe.get_doc(
            "Sales Taxes and Charges Template", taxes_and_charges
        )

        tax_rate = taxes_template_doc.taxes[0]
        if tax_rate and tax_rate.included_in_print_rate == 1:
            if any(item.item_tax_template for item in pos_invoice_doc.items):
                frappe.throw(
                    "Item Tax Template cannot be used when taxes are included in "
                    "the print rate. Please remove Item Tax Templates."
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
                            "Zatca tax category should be 'Zero Rated', 'Exempted' or "
                            "'Services outside scope of tax / Not subject to VAT' for items with "
                            "tax rate not equal to 5.00 or 15.00."
                        )

                    if (
                        f"{tax_rate:.2f}" == "15.00"
                        and zatca_tax_category != "Standard"
                    ):
                        frappe.throw(
                            "Check the Zatca category code and enable it as standard."
                        )
        base_discount_amount = pos_invoice_doc.get("base_discount_amount", 0.0)
        if len(tax_categories) > 1 and base_discount_amount > 0:
            frappe.throw(
                "ZATCA does not respond for multiple items with multiple tax categories"
                " with doc-level discount. Please ensure all items have the same tax category."
            )
        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw(
                "Please save and submit the invoice before sending to Zatca: "
                + str(invoice_number)
            )
        if base_discount_amount < 0:
            frappe.throw(
                "Additional discount cannot be negative. Please enter a positive value."
            )

        if pos_invoice_doc.docstatus in [0, 2]:
            frappe.throw(
                "Please submit the invoice before sending to Zatca: "
                + str(invoice_number)
            )

        if pos_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw("Already submitted to Zakat and Tax Authority")

        if settings.custom_zatca_invoice_enabled != 1:
            frappe.throw(
                "Zatca Invoice is not enabled in Company Settings, "
                "Please contact your system administrator"
            )

        if settings.custom_phase_1_or_2 == "Phase-2":
            zatca_call(
                invoice_number, "0", any_item_has_tax_template, company_abbr, source_doc
            )
        else:
            create_qr_code(pos_invoice_doc, method=None)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in background call: " + str(e))


@frappe.whitelist(allow_guest=False)
def zatca_background_on_submit(doc, _method=None):
    """Function for zatca background on submit"""

    try:
        source_doc = doc
        pos_invoice_doc = doc
        invoice_number = pos_invoice_doc.name
        pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        company_abbr = frappe.db.get_value(
            "Company", {"name": pos_invoice_doc.company}, "abbr"
        )
        if not company_abbr:
            frappe.throw(
                f"Company abbreviation for {pos_invoice_doc.company} not found."
            )

        any_item_has_tax_template = False

        for item in pos_invoice_doc.items:
            if item.item_tax_template:
                any_item_has_tax_template = True
                break

        if any_item_has_tax_template:
            for item in pos_invoice_doc.items:
                if not item.item_tax_template:
                    frappe.throw(ITEM_TAX_TEMPLATE_WARNING)

        pos_profile = pos_invoice_doc.pos_profile
        if not pos_profile:
            frappe.throw("POS Profile is not set in the POS Invoice.")
        pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
        taxes_and_charges = pos_profile_doc.taxes_and_charges
        taxes_template_doc = frappe.get_doc(
            "Sales Taxes and Charges Template", taxes_and_charges
        )

        tax_rate = taxes_template_doc.taxes[0]
        if tax_rate and tax_rate.included_in_print_rate == 1:
            if any(item.item_tax_template for item in pos_invoice_doc.items):
                frappe.throw(
                    "Item Tax Template cannot be used when taxes are included in "
                    "the print rate. Please remove Item Tax Templates."
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
                            "Zatca tax category should be 'Zero Rated', 'Exempted' or "
                            "'Services outside scope of tax / Not subject to VAT' for items with "
                            "tax rate not equal to 5.00 or 15.00."
                        )

                    if (
                        f"{tax_rate:.2f}" == "15.00"
                        and zatca_tax_category != "Standard"
                    ):
                        frappe.throw(
                            "Check the Zatca category code and enable it as standard."
                        )
        base_discount_amount = pos_invoice_doc.get("base_discount_amount", 0.0)
        if len(tax_categories) > 1 and base_discount_amount > 0:
            frappe.throw(
                "ZATCA does not respond for multiple items with multiple tax categories "
                "with doc-level discount. Please ensure all items have the same tax category."
            )
        # Check if Zatca Invoice is enabled in the Company document
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if company_doc.custom_zatca_invoice_enabled != 1:
            frappe.throw(
                "Zatca Invoice is not enabled in the Company settings,"
                " Please contact your system administrator"
            )

        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw(
                "Please save and submit the invoice before sending to Zatca:  "
                + str(invoice_number)
            )
        if base_discount_amount < 0:
            frappe.throw(
                "Additional discount cannot be negative. Please enter a positive value."
            )

        if pos_invoice_doc.docstatus in [0, 2]:
            frappe.throw(
                "Please submit the invoice before sending to Zatca:  "
                + str(invoice_number)
            )

        if pos_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw("Already submitted to Zakat and Tax Authority")
        company_name = pos_invoice_doc.company

        # Retrieve the company document to access settings
        settings = frappe.get_doc("Company", company_name)
        if settings.custom_phase_1_or_2 == "Phase-2":
            zatca_call(
                invoice_number, "0", any_item_has_tax_template, company_abbr, source_doc
            )
        else:
            create_qr_code(pos_invoice_doc, method=None)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in background call submit: " + str(e))
