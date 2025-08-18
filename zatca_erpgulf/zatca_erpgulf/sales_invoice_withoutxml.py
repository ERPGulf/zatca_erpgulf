"""This file is used to generate the zATCA without XML file and the QR code for the sales invoice"""

import base64
import os
import io
from frappe import _
import frappe
import requests

from pyqrcode import create as qr_create
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from zatca_erpgulf.zatca_erpgulf.sales_invoice_with_xmlqr import (
    get_api_url,
    xml_base64_decode,
    success_log,
    error_log,
)
from zatca_erpgulf.zatca_erpgulf.createxml import (
    xml_tags,
    salesinvoice_data,
    add_document_level_discount_with_tax_template,
    add_document_level_discount_with_tax,
    company_data,
    customer_data,
    invoice_typecode_compliance,
    add_nominal_discount_tax,
    doc_reference,
    additional_reference,
    delivery_and_payment_means,
    invoice_typecode_simplified,
)
from zatca_erpgulf.zatca_erpgulf.xml_tax_data import tax_data, tax_data_with_template
from zatca_erpgulf.zatca_erpgulf.create_xml_final_part import (
    tax_data_nominal,
    tax_data_with_template_nominal,
    item_data,
    item_data_with_template,
    xml_structuring,
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

SALES_INVOICE = "Sales Invoice"


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


def zatca_call_withoutxml(
    invoice_number,
    compliance_type="0",
    any_item_has_tax_template=False,
    company_abbr=None,
    source_doc=None,
):
    """zatca call which includes the function calling and validation reguarding the api and
    based on this the zATCA output and message is getting"""
    try:
        if not frappe.db.exists(SALES_INVOICE, invoice_number):
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
                frappe.throw(
                    _("customer should be B2C sales invoice with xml during create xml")
                )
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

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                attach_qr_image(qrcodeb64, sales_invoice_doc)
                reporting_api_sales_withoutxml(
                    uuid1,
                    encoded_hash,
                    signed_xmlfile_name,
                    invoice_number,
                    sales_invoice_doc,
                )
            else:
                frappe.throw(
                    _("customer should be B2C type required for simplified invoice")
                )
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


def reporting_api_sales_withoutxml(
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
        if not sales_invoice_doc.custom_zatca_pos_name:
            frappe.throw(
                _(
                    f"ZATCA POS name is missing for invoice without xml {invoice_number}."
                )
            )

        zatca_settings = frappe.get_doc(
            "ZATCA Multiple Setting", sales_invoice_doc.custom_zatca_pos_name
        )
        production_csid = zatca_settings.custom_final_auth_csid

        if not production_csid:
            frappe.throw(
                _(f"Production CSID is missing in ZATCA settings for {company_abbr}.")
            )
        headers = {
            "accept": "application/json",
            "accept-language": "en",
            "Clearance-Status": "0",
            "Accept-Version": "V2",
            "Authorization": "Basic " + production_csid,
            "Content-Type": "application/json",
            "Cookie": "TS0106293e=0132a679c0639d13d069bcba831384623a2ca6da47fac8d91bef610c47c7119dcdd3b817f963ec301682dae864351c67ee3a402866",
        }
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
                if response.status_code in (400, 405, 406):
                    invoice_doc = frappe.get_doc(SALES_INVOICE, invoice_number)
                    # invoice_doc.db_set(
                    #     "custom_uuid",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    # invoice_doc.db_set(
                    #     "custom_zatca_status",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    # invoice_doc.db_set(
                    #     "custom_zatca_full_response",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    invoice_doc.custom_uuid = "Not Submitted"
                    invoice_doc.custom_zatca_status = "Not Submitted"
                    invoice_doc.custom_zatca_full_response = "Not Submitted"
                    invoice_doc.save(ignore_permissions=True)  # or with permissions if needed
                    frappe.db.commit()

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
                    invoice_doc = frappe.get_doc(SALES_INVOICE, invoice_number)
                    invoice_doc.custom_uuid = "Not Submitted"
                    invoice_doc.custom_zatca_status = "Not Submitted"
                    invoice_doc.custom_zatca_full_response = "Not Submitted"
                    invoice_doc.save(ignore_permissions=True)  # or with permissions if needed
                    frappe.db.commit()
                    # invoice_doc.db_set(
                    #     "custom_uuid",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    # invoice_doc.db_set(
                    #     "custom_zatca_status",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    # invoice_doc.db_set(
                    #     "custom_zatca_full_response",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
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
                    invoice_doc = frappe.get_doc(SALES_INVOICE, invoice_number)
                    # invoice_doc.db_set(
                    #     "custom_uuid",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    # invoice_doc.db_set(
                    #     "custom_zatca_status",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    # invoice_doc.db_set(
                    #     "custom_zatca_full_response",
                    #     "Not Submitted",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    invoice_doc.custom_uuid = "Not Submitted"
                    invoice_doc.custom_zatca_status = "Not Submitted"
                    invoice_doc.custom_zatca_full_response = "Not Submitted"
                    invoice_doc.save(ignore_permissions=True)  # or with permissions if needed
                    frappe.db.commit()
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

                    if sales_invoice_doc.custom_zatca_pos_name:
                        if (
                            zatca_settings.custom_send_pos_invoices_to_zatca_on_background
                        ):
                            frappe.msgprint(msg)

                        # Update PIH data without JSON formatting
                        zatca_settings.custom_pih = encoded_hash
                        zatca_settings.save(ignore_permissions=True)

                    invoice_doc = frappe.get_doc(SALES_INVOICE, invoice_number)
                    # invoice_doc.db_set(
                    #     "custom_zatca_full_response",
                    #     msg,
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    # invoice_doc.db_set(
                    #     "custom_uuid", uuid1, commit=True, update_modified=True
                    # )
                    # invoice_doc.db_set(
                    #     "custom_zatca_status",
                    #     "REPORTED",
                    #     commit=True,
                    #     update_modified=True,
                    # )
                    invoice_doc.custom_zatca_full_response = msg
                    invoice_doc.custom_uuid = uuid1
                    invoice_doc.custom_zatca_status = "REPORTED"
                    invoice_doc.save(ignore_permissions=True)
                    frappe.db.commit()

                    success_log(response.text, uuid1, invoice_number)
                else:

                    error_log()
                if response.status_code == 409:
                    msg = "SUCCESS: <br><br>"
                    msg += (
                        f"Status Code: {response.status_code}<br><br> "
                        f"ZATCA Response: {response.text}<br><br>"
                    )

                    # Update PIH
                    if sales_invoice_doc.custom_zatca_pos_name:
                        zatca_settings = frappe.get_doc(
                            "ZATCA Multiple Setting", sales_invoice_doc.custom_zatca_pos_name
                        )
                        if zatca_settings.custom_send_pos_invoices_to_zatca_on_background:
                            frappe.msgprint(msg)
                        zatca_settings.custom_pih = encoded_hash
                        zatca_settings.save(ignore_permissions=True)
                    else:
                        company_doc = frappe.get_doc("Company", sales_invoice_doc.company)
                        if company_doc.custom_send_einvoice_background:
                            frappe.msgprint(msg)
                        company_doc.custom_pih = encoded_hash
                        company_doc.save(ignore_permissions=True)

                    invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                    invoice_doc.custom_zatca_full_response = msg
                    invoice_doc.custom_uuid = uuid1
                    invoice_doc.custom_zatca_status = "REPORTED"
                    invoice_doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    

                    success_log(response.text, uuid1, invoice_number)
                else:

                    error_log()
                
            except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
                frappe.throw(
                    _(f"Error in reporting API-2 sales invoice with xml: {str(e)}")
                )

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc(SALES_INVOICE, invoice_number)
        # invoice_doc.db_set(
        #     "custom_zatca_full_response",
        #     f"Error: {str(e)}",
        #     commit=True,
        #     update_modified=True,
        # )
        invoice_doc.custom_zatca_full_response = f"Error: {str(e)}"
        invoice_doc.save(ignore_permissions=True)  # or with permissions if needed
        frappe.db.commit()
        frappe.throw(_(f"Error in reporting API-1 sales invoice with xml: {str(e)}"))
