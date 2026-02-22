
"""ZATCA E-Invoicing Integration for ERPNext debug xml for pos inv"""

import base64
import json
import requests
from frappe import _
import frappe
import traceback
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



def is_file_attached(file_url):
    """Check if a file is attached by verifying its existence in the database."""
    return file_url and frappe.db.exists("File", {"file_url": file_url})


def is_qr_and_xml_attached(pos_invoice_doc):
    """Check if both QR code and XML file are already"""

    # Get the QR Code field value
    qr_code = pos_invoice_doc.get("ksa_einv_qr")

    # Get the XML file if attached
    xml_file = frappe.db.get_value(
        "File",
        {
            "attached_to_doctype": pos_invoice_doc.doctype,
            "attached_to_name": pos_invoice_doc.name,
            "file_name": ["like", "%Reported xml file%"],
        },
        "file_url",
    )

    # Ensure both files exist before confirming attachment
    return is_file_attached(qr_code) and is_file_attached(xml_file)

@frappe.whitelist(allow_guest=False)
def debug_call(
    invoice_number,
    compliance_type="0",
    any_item_has_tax_template=False,
    company_abbr=None,
    source_doc=None,
):

    """Function for ZATCA debug XML generation and attachment"""
    try:
        # --- Fetch POS Invoice ---
        pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        source_doc = pos_invoice_doc

        company_name = pos_invoice_doc.company
        settings = frappe.get_doc("Company", company_name)
        company_abbr = settings.abbr
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})

        if company_doc.custom_zatca_invoice_enabled != 1:
            frappe.msgprint(_("ZATCA Invoice is not enabled. Submitting the document."))
            return

        # --- Fetch Customer ---
        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)

        # Intra-company transfer
        if company_doc.tax_id and customer_doc.tax_id:
            if company_doc.tax_id.strip() == customer_doc.tax_id.strip():
                pos_invoice_doc.custom_zatca_status = "Intra-company transfer"
                pos_invoice_doc.custom_zatca_full_response = "Intra-company transfer"
                pos_invoice_doc.save(ignore_permissions=True)
                frappe.db.commit()
                return

        if not customer_doc.custom_buyer_id_type and customer_doc.custom_buyer_id:
            frappe.throw(_("Buyer ID must be blank if Buyer ID Type is not set."))

        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw(_("Invoice Number is NOT valid:" + str(invoice_number)))

        # --- Check GPOS and fields ---
        is_gpos_installed = "gpos" in frappe.get_installed_apps()
        field_exists = frappe.get_meta("POS Invoice").has_field("custom_unique_id")

        if is_gpos_installed and pos_invoice_doc.custom_xml and not pos_invoice_doc.custom_qr_code:
            frappe.throw(
                _(
                    "Please provide the 'qr_code' field data when 'custom_xml' is filled for invoice: "
                    + str(invoice_number)
                )
            )

        # --- Function to generate and attach XML ---
        def generate_and_attach_xml(invoice_doc, handle_b2c_simplified=True):
            invoice = xml_tags()
            invoice, uuid1, invoice_doc = salesinvoice_data(invoice, invoice_number)

            company_abbr = frappe.db.get_value("Company", {"name": invoice_doc.company}, "abbr")
            customer_doc_inner = frappe.get_doc("Customer", invoice_doc.customer)

            if compliance_type == "0":
                if customer_doc_inner.custom_b2c == 1:
                    invoice = invoice_typecode_simplified(invoice, invoice_doc)
                else:
                    frappe.throw(_("Customer should be B2C POS without XML during create XML."))
            else:
                invoice = invoice_typecode_compliance(invoice, compliance_type)

            invoice = doc_reference(invoice, invoice_doc, invoice_number)
            invoice = additional_reference(invoice, company_abbr, invoice_doc)
            invoice = company_data(invoice, invoice_doc)
            invoice = customer_data(invoice, invoice_doc)
            invoice = delivery_and_paymentmeans(invoice, invoice_doc, invoice_doc.is_return)

            if not any_item_has_tax_template:
                invoice = add_document_level_discount_with_tax(invoice, invoice_doc)
                invoice = tax_data(invoice, invoice_doc)
                invoice = item_data(invoice, invoice_doc)
            else:
                invoice = add_document_level_discount_with_tax_template(invoice, invoice_doc)
                invoice = tax_data_with_template(invoice, invoice_doc)
                invoice = item_data_with_template(invoice, invoice_doc)

            file_content = xml_structuring(invoice)

            # --- Read XML file ---
            # try:
            #     with open(f"{frappe.local.site}/private/files/finalzatcaxml_{invoice_number}.xml", "r", encoding="utf-8") as file:
            #         file_content = file.read()
            # except FileNotFoundError:
            #     frappe.throw("XML file not found")

            tag_removed_xml = removetags(file_content)
            canonicalized_xml = canonicalize_xml(tag_removed_xml)
            hash1, encoded_hash = getinvoicehash(canonicalized_xml)
            encoded_signature = digital_signature(hash1, company_abbr, source_doc)
            issuer_name, serial_number = extract_certificate_details(company_abbr, source_doc)
            encoded_certificate_hash = certificate_hash(company_abbr, source_doc)
            modified_xml_string, namespaces, signing_time = signxml_modify(company_abbr,file_content, source_doc)
            signed_properties_base64 = generate_signed_properties_hash(signing_time, issuer_name, serial_number, encoded_certificate_hash)
            final_xml_string = populate_the_ubl_extensions_output(modified_xml_string,encoded_signature, namespaces, signed_properties_base64, encoded_hash, company_abbr, source_doc)

            tlv_data = generate_tlv_xml(final_xml_string, company_abbr, source_doc)
            tagsbufsarray = [get_tlv_for_value(tag_num, tag_value) for tag_num, tag_value in tlv_data.items()]
            qrcodebuf = b"".join(tagsbufsarray)
            qrcodeb64 = base64.b64encode(qrcodebuf).decode("utf-8")
            updated_xml_string = update_qr_toxml(final_xml_string, qrcodeb64, company_abbr)

            signed_xmlfile_name = structuring_signedxml(invoice_number ,updated_xml_string)
            safe_invoice_number = invoice_number.replace("/", "-")
            signed_xmlfile_name = f"{frappe.local.site}/private/files/final_xml_after_indent_{safe_invoice_number}.xml"
            debug_filename = f"DEBUG_INVOICE_{invoice_doc.name}.xml"
            # nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
            with open(signed_xmlfile_name, "r", encoding="utf-8") as f:
                xml_data = f.read()

            # Delete older debug files
            existing_files = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": "POS Invoice",
                    "attached_to_name": invoice_doc.name,
                    "file_name": ["like", "DEBUG_INVOICE_%"],
                },
                order_by="creation desc",
                fields=["name", "file_name"]
            )

            for file in existing_files:
                frappe.delete_doc("File", file.name, ignore_permissions=True)

            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": debug_filename,
                "attached_to_doctype": "POS Invoice",
                "attached_to_name": invoice_doc.name,
                "content": xml_data,
                "is_private": 1,
            })
            file_doc.save(ignore_permissions=True)
            frappe.msgprint(f"✅ Debug XML attached as {debug_filename}")

            return {"status": "success", "message": f"XML attached: {debug_filename}"}

        # --- Determine handle_b2c_simplified flag ---
        handle_b2c_simplified = False

        if settings.custom_phase_1_or_2 == "Phase-2":
            if field_exists and getattr(pos_invoice_doc, "custom_unique_id", None):
                if not getattr(pos_invoice_doc, "custom_zatca_pos_name", None):
                    frappe.throw(_("POS name is required"))

                if is_gpos_installed and getattr(pos_invoice_doc, "custom_xml", None):
                    frappe.msgprint(_("✅ XML already attached for this POS invoice"))
                else:
                    handle_b2c_simplified = True
            else:
                if is_qr_and_xml_attached(pos_invoice_doc):
                    frappe.msgprint(_("✅ XML/QR already attached"))
                elif settings.custom_send_invoice_to_zatca == "Background" and not bypass_background_check:
                    handle_b2c_simplified = True
                else:
                    handle_b2c_simplified = False

        return generate_and_attach_xml(pos_invoice_doc, handle_b2c_simplified=handle_b2c_simplified)

    except Exception as e:
        frappe.log_error(traceback.format_exc(), f"Debug XML Error for invoice {invoice_number}")
        return {"status": "error", "message": f"Error generating debug XML: {str(e)}"}