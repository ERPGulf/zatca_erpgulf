"""This file contains the function to call the ZATCA API for POS Invoices"""

import base64
from frappe import _  # pylint: disable=unused-import
import frappe
import requests
from zatca_erpgulf.zatca_erpgulf.event_log import log_zatca_event
from zatca_erpgulf.zatca_erpgulf.sales_invoice_with_xmlqr import (
    get_api_url,
    xml_base64_decode,
    success_log,
    error_log,
)
from zatca_erpgulf.zatca_erpgulf.sales_invoice_withoutxml import attach_qr_image
from zatca_erpgulf.zatca_erpgulf.posxml import (
    xml_tags,
    salesinvoice_data,
    add_document_level_discount_with_tax_template,
    add_document_level_discount_with_tax,
    invoice_typecode_simplified,
    doc_reference,
    additional_reference,
    company_data,
    customer_data,
    delivery_and_paymentmeans,
    tax_data,
    invoice_typecode_compliance,
)
from zatca_erpgulf.zatca_erpgulf.pos_final import (
    tax_data_with_template,
    item_data_with_template,
    item_data,
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

ITEM_TAX_TEMPLATE_WARNING = "If any one item has an Item Tax Template,"
" all items must have an Item Tax Template."
CONTENT_TYPE_JSON = "application/json"
POS_INVOICE = "POS Invoice"


def zatca_call_pos_without_xml(
    invoice_number,
    compliance_type="0",
    any_item_has_tax_template=False,
    company_abbr=None,
    source_doc=None,
):
    """Function for ZATCA call"""
    try:

        if not frappe.db.exists(POS_INVOICE, invoice_number):
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
                frappe.throw(
                    "customer should be B2C pos without xml during create xml "
                )
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

        file_content = xml_structuring(invoice,invoice_number)

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
        modified_xml_string, namespaces, signing_time = signxml_modify(company_abbr,file_content, source_doc)
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
        signed_xmlfile_name = structuring_signedxml(invoice_number, updated_xml_string)

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                attach_qr_image(qrcodeb64, pos_invoice_doc)
                reporting_api_pos_without_xml(
                    uuid1,
                    encoded_hash,
                    signed_xmlfile_name,
                    invoice_number,
                    pos_invoice_doc,
                )

            else:
                frappe.throw(
                    _(
                        "B2B is not supported for POS Invoices,customer should be B2C pos without xml "
                    )
                )
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


def reporting_api_pos_without_xml(
    uuid1, encoded_hash, signed_xmlfile_name, invoice_number, pos_invoice_doc
):
    """Function for reporting api"""
    try:
        # Retrieve the company abbreviation based on the company in the sales invoice
        company_abbr = frappe.db.get_value(
            "Company", {"name": pos_invoice_doc.company}, "abbr"
        )
        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        if not company_abbr:
            frappe.throw(
                _(f"Company with abbreviation {pos_invoice_doc.company} not found.")
            )

        # Prepare the payload without JSON formatting
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
                "file_name": "Reported xml file " + pos_invoice_doc.name + ".xml",
                "attached_to_doctype": pos_invoice_doc.doctype,
                "is_private": 1,
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
        # Directly retrieve the production CSID from the company's document field
        if not pos_invoice_doc.custom_zatca_pos_name:
            frappe.throw(
                _(
                    f"ZATCA POS name is missing for invoice pos withoutxml {invoice_number}."
                )
            )
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

        if not production_csid:
            frappe.throw(
                _(f"Production CSID is missing in ZATCA settings for {company_abbr}or in multple setting page.")
            )
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
                    invoice_doc = frappe.get_doc(POS_INVOICE, invoice_number)
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
                                f"Status code: {response.status_code}<br><br> "
                                f"{response.text}"
                            )
                        )
                    )

                if response.status_code in (401, 403, 407, 451):
                    invoice_doc = frappe.get_doc(POS_INVOICE, invoice_number)
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

                    invoice_doc = frappe.get_doc(POS_INVOICE, invoice_number)
                    invoice_doc.custom_zatca_full_response = msg
                    invoice_doc.custom_uuid = uuid1
                    invoice_doc.custom_zatca_status = "REPORTED"
                    invoice_doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    

                    success_log(response.text, uuid1, invoice_number)
                # else:

                #     error_log()

                if response.status_code not in (200, 202, 409):
                    invoice_doc = frappe.get_doc(POS_INVOICE, invoice_number)
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
                            linked_doc.custom_pih = encoded_hash
                            linked_doc.save(ignore_permissions=True)
                    else:
                        company_doc = frappe.get_doc("Company", pos_invoice_doc.company)
                        if company_doc.custom_send_einvoice_background:
                            frappe.msgprint(msg)
                        company_doc.custom_pih = encoded_hash
                        company_doc.save(ignore_permissions=True)

                    invoice_doc = frappe.get_doc(POS_INVOICE, invoice_number)
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
                
            except (ValueError, TypeError, KeyError) as e:
                frappe.throw(
                    _(("Error in reporting API-2 pos without xml " f"error: {str(e)}"))
                )

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        invoice_doc.custom_zatca_full_response = f"Error: {str(e)}"
        invoice_doc.save(ignore_permissions=True)  # or with permissions if needed
        frappe.db.commit()
        frappe.throw(_(("Error in reporting API-1 pos without xml" f"error: {str(e)}")))
