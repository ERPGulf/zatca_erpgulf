"""This module is used to submit the POS invoice to ZATCA using the API through xml and qr."""

import base64
from frappe import _
import frappe
import requests
from lxml import etree

CONTENT_TYPE_JSON = "application/json"


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


def extract_uuid_and_invoicehash(file_path):
    """
    Extracts the UUID and DigestValue from an XML file.

    Args:
        file_path (str): Path to the XML file.

    Returns:
        dict: A dictionary containing UUID and DigestValue.
    """
    try:
        # Read the file content as bytes
        with open(frappe.local.site + file_path, "rb") as file:
            custom_xml = file.read()

        # Parse the XML string as bytes
        tree = etree.fromstring(custom_xml)

        # Define the namespaces
        namespaces = {
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }

        # Extract the UUID
        uuid = tree.find("cbc:UUID", namespaces).text

        # Extract the DigestValue
        digest_value_element = tree.find(
            ".//ds:Reference[@Id='invoiceSignedData']/ds:DigestValue", namespaces
        )
        digest_value = (
            digest_value_element.text
            if digest_value_element is not None
            else "Not Found"
        )

        return uuid, digest_value

    except Exception as e:
        return {
            "error": f"Error parsing or extracting data sales invoice with xml: {e}"
        }


def reporting_api_xml_sales_invoice(
    uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc
):
    """reporting api based on the api data and payload"""
    try:
        company_abbr = frappe.db.get_value(
            "Company", {"name": sales_invoice_doc.company}, "abbr"
        )

        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_decode(signed_xmlfile_name),
        }
        # production_csid = company_doc.custom_basic_auth_from_p roduction
        if not sales_invoice_doc.custom_zatca_pos_name:
            frappe.throw(
                _(f"ZATCA POS name is missing for invoice with xml {invoice_number}.")
            )

        zatca_settings = frappe.get_doc(
            "ZATCA Multiple Setting", sales_invoice_doc.custom_zatca_pos_name
        )
        production_csid = zatca_settings.custom_final_auth_csid

        if not production_csid:
            frappe.throw(
                _(
                    f"Production CSID is missing in ZATCA settings for sales invoice with xml {company_abbr}."
                )
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
                invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                # invoice_doc.db_set(
                #     "custom_uuid", "Not Submitted", commit=True, update_modified=True
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
                invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                # invoice_doc.db_set(
                #     "custom_uuid", "Not Submitted", commit=True, update_modified=True
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
                            "Error: ZATCA Authentication failed. "
                            "Your access token may be expired or not valid. "
                            "Please contact your system administrator. "
                            f"Status code: {response.status_code}<br><br>"
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
            if response.status_code not in (200, 202):
                invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                # invoice_doc.db_set(
                #     "custom_uuid", "Not Submitted", commit=True, update_modified=True
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
                    if zatca_settings.custom_send_pos_invoices_to_zatca_on_background:
                        frappe.msgprint(msg)

                    # Update PIH data without JSON formatting
                    zatca_settings.custom_pih = encoded_hash
                    zatca_settings.save(ignore_permissions=True)

                invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
                # invoice_doc.db_set(
                #     "custom_zatca_full_response", msg, commit=True, update_modified=True
                # )
                # invoice_doc.db_set(
                #     "custom_uuid", uuid1, commit=True, update_modified=True
                # )
                # invoice_doc.db_set(
                #     "custom_zatca_status", "REPORTED", commit=True, update_modified=True
                # )
                invoice_doc.custom_zatca_full_response = msg
                invoice_doc.custom_uuid = uuid1
                invoice_doc.custom_zatca_status = "REPORTED"
                invoice_doc.save(ignore_permissions=True)
                frappe.db.commit()

                success_log(response.text, uuid1, invoice_number)
            else:

                error_log()
                
            
        except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
            frappe.throw(_(f"Error in reporting API-2 xml with sales invoice data : {str(e)}"))

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
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


def submit_sales_invoice_withxmlqr(sales_invoice_doc, file_path, invoice_number):
    """submit sales invoice with xml qr"""
    try:
        uuid1, encoded_hash = extract_uuid_and_invoicehash(file_path)

        if "error" in uuid1:
            frappe.throw(uuid1["error"])

        reporting_api_xml_sales_invoice(
            uuid1,
            encoded_hash,
            frappe.local.site + file_path,
            invoice_number,
            sales_invoice_doc,
        )

    except Exception as e:
        frappe.throw(_(f"Error in submitting sales invoice with XML and  QR: {str(e)}"))
