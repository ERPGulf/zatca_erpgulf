import frappe
import json
import base64
from frappe import _
import traceback
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
SALES_INVOICE = "Sales Invoice"
REPORTED_XML = "%Reported xml file%"

SUPPORTED_INVOICES = ["Sales Invoice", "POS Invoice"]

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
def debug_call(
    invoice_number,
    compliance_type="0",
    any_item_has_tax_template=False,
    company_abbr=None,
    source_doc=None,
    bypass_background_check=False
):
    """
    Generate ZATCA-compliant debug XML for a Sales Invoice and attach as a private file.
    Handles Phase-2, B2C simplified, GPOS, TLV, QR, signing, and fallback logic.
    """
    try:
    # Load Sales Invoice
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
        source_doc = sales_invoice_doc
        # if source_doc:
        #         source_doc = frappe.get_doc(json.loads(source_doc))
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
        company_name = sales_invoice_doc.company
        settings = frappe.get_doc("Company", company_name)
        company_abbr = settings.abbr
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if company_doc.custom_zatca_invoice_enabled != 1:
            frappe.msgprint("Zatca Invoice is not enabled. Submitting the document.")
            return
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
        if company_doc.tax_id and customer_doc.tax_id:
            if company_doc.tax_id.strip() == customer_doc.tax_id.strip():
                sales_invoice_doc.custom_zatca_status = "Intra-company transfer"
                sales_invoice_doc.custom_zatca_full_response = "Intra-company transfer"
                sales_invoice_doc.save(ignore_permissions=True)
                frappe.db.commit()
                return
        # Check if GPOS installed & custom fields exist
        is_gpos_installed = "gpos" in frappe.get_installed_apps()
        field_exists = frappe.get_meta(SALES_INVOICE).has_field("custom_unique_id")

        # Validate QR if XML already exists
        if is_gpos_installed and getattr(sales_invoice_doc, "custom_xml", None) and not getattr(sales_invoice_doc, "custom_qr_code", None):
            frappe.throw(_("Please provide the 'qr_code' field data when XML exists for invoice: ") + str(invoice_number))
        
        # --- Helper function: generate & attach XML ---
        def generate_and_attach_xml(invoice_doc, handle_b2c_simplified=True):
            # Step 1: XML creation
            invoice = xml_tags()
            invoice, uuid1, invoice_doc = salesinvoice_data(invoice, invoice_doc.name)
            customer_doc = frappe.get_doc("Customer", invoice_doc.customer)

            # Step 2: Invoice type logic
            if handle_b2c_simplified:
                invoice = invoice_typecode_simplified(invoice, invoice_doc)
            else:
                if compliance_type == "0":

                    if getattr(customer_doc, "custom_b2c", 0) == 1:

                        invoice = invoice_typecode_simplified(invoice, invoice_doc)
                    else:
                        invoice = invoice_typecode_standard(invoice, invoice_doc)
                else:
                    invoice = invoice_typecode_compliance(invoice, compliance_type)


            # Step 3: Populate XML
            invoice = doc_reference(invoice, invoice_doc, invoice_doc.name)
            invoice = additional_reference(invoice, company_abbr, invoice_doc)
            invoice = company_data(invoice, invoice_doc)
            invoice = customer_data(invoice, invoice_doc)
            invoice = delivery_and_payment_means(invoice, invoice_doc, invoice_doc.is_return)

            # Step 4: Discounts & Taxes
            if getattr(invoice_doc, "custom_zatca_nominal_invoice", 0) == 1:
                invoice = add_nominal_discount_tax(invoice, invoice_doc)
                if not any_item_has_tax_template:
                    invoice = tax_data_nominal(invoice, invoice_doc)
                else:
                    invoice = tax_data_with_template_nominal(invoice, invoice_doc)
            else:
                if not any_item_has_tax_template:
                    invoice = add_document_level_discount_with_tax(invoice, invoice_doc)
                    invoice = tax_data(invoice, invoice_doc)
                else:
                    invoice = add_document_level_discount_with_tax_template(invoice, invoice_doc)
                    invoice = tax_data_with_template(invoice, invoice_doc)

            # Step 5: Item data
            is_claudion_installed = "claudion4saudi" in frappe.get_installed_apps()
            has_advance_copy = getattr(invoice_doc, "custom_advances_copy", False)

            if is_claudion_installed and has_advance_copy:
                if not any_item_has_tax_template:
                    invoice = item_data_advance_invoice(invoice, invoice_doc)
                else:
                    invoice = item_data_with_template_advance_invoice(invoice, invoice_doc)
            else:
                if not any_item_has_tax_template:
                    invoice = item_data(invoice, invoice_doc)
                else:
                    invoice = item_data_with_template(invoice, invoice_doc)

            # Step 6: XML Structuring & reading
            xml_structuring(invoice,invoice_number)
            xml_file_path = f"{frappe.local.site}/private/files/finalzatcaxml_{invoice_number}.xml"
            try:
                with open(xml_file_path, "r", encoding="utf-8") as file:
                    xml_content = file.read()
            except FileNotFoundError:
                frappe.throw(_("XML file not found"))

            # Step 7: Signing & QR
            tag_removed_xml = removetags(xml_content)
            canonicalized_xml = canonicalize_xml(tag_removed_xml)
            hash1, encoded_hash = getinvoicehash(canonicalized_xml)
            encoded_signature = digital_signature(hash1, company_abbr, source_doc)
            issuer_name, serial_number = extract_certificate_details(company_abbr, source_doc)
            encoded_certificate_hash = certificate_hash(company_abbr, source_doc)
            namespaces, signing_time = signxml_modify(company_abbr,invoice_number, source_doc)
            signed_properties_base64 = generate_signed_properties_hash(signing_time, issuer_name, serial_number, encoded_certificate_hash)      
            
            populate_the_ubl_extensions_output(
                encoded_signature,
                namespaces,
                signed_properties_base64,
                encoded_hash,
                company_abbr,
                invoice_number,
                source_doc,
            )
            tlv_data = generate_tlv_xml(company_abbr,invoice_number, source_doc)

            tagsbufsarray = []
            for tag_num, tag_value in tlv_data.items():
                tagsbufsarray.append(get_tlv_for_value(tag_num, tag_value))

            qrcodebuf = b"".join(tagsbufsarray)
            qrcodeb64 = base64.b64encode(qrcodebuf).decode("utf-8")
            update_qr_toxml(qrcodeb64,invoice_number, company_abbr)
            signed_xmlfile_name = structuring_signedxml(invoice_number)
            # Step 8: Save & attach final XML
            
            signed_xmlfile_name = f"{frappe.local.site}/private/files/final_xml_after_indent_{invoice_number}.xml"
            debug_filename = f"DEBUG_INVOICE_{invoice_doc.name}.xml"
            with open(signed_xmlfile_name, "r", encoding="utf-8") as f:
                xml_data = f.read()
            existing_files = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": SALES_INVOICE,
                    "attached_to_name": invoice_doc.name,
                    "file_name": ["like", "DEBUG_INVOICE_%"],
                },
                order_by="creation desc",
                fields=["name", "file_name"]
            )

            # Delete older debug files if any
            for file in existing_files:
                frappe.delete_doc("File", file.name, ignore_permissions=True)
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": debug_filename,
                "attached_to_doctype": SALES_INVOICE,
                "attached_to_name": invoice_doc.name,
                "content": xml_data,
                "is_private": 1,
            })
            file_doc.save(ignore_permissions=True)
            frappe.msgprint(f"✅ Debug XML attached as {debug_filename}")

            return {"status": "success", "message": f"XML attached: {debug_filename}"}

        # --- Determine handle_b2c_simplified flag ---
        handle_b2c_simplified = False  # default

        if settings.custom_phase_1_or_2 == "Phase-2":
            if field_exists and getattr(sales_invoice_doc, "custom_unique_id", None):
                if is_gpos_installed and getattr(sales_invoice_doc, "custom_xml", None):
                    
                    # Already processed, do nothing
                    frappe.msgprint("Already the xml attached")
                    pass
                else:
                    # Phase-2 + custom_unique_id + no XML yet => B2C simplified
                    handle_b2c_simplified = True
            else:
                if is_qr_and_xml_attached(sales_invoice_doc):
                    # Already has QR & XML => do 
                    frappe.msgprint("✅ XML/QR already attached")
                    pass
                elif settings.custom_send_invoice_to_zatca == "Background" and not bypass_background_check:
                    # Background sending => B2C simplified
                    handle_b2c_simplified = True
                else:
                    # Default / fallback => not simplified
                    handle_b2c_simplified = False

        # --- Generate and attach XML ---
        return generate_and_attach_xml(sales_invoice_doc, handle_b2c_simplified=handle_b2c_simplified)
    except Exception as e:
            # Log full traceback in Frappe
            frappe.log_error(traceback.format_exc(), f"Debug XML Error for invoice {invoice_number}")
            # Return a proper JSON response to JS
            return {"status": "error", "message": f"Error generating debug XML: {str(e)}"}