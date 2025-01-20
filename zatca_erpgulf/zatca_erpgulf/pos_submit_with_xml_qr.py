""" This module is used to submit the POS invoice to ZATCA using the API through xml and qr. """

import frappe
import requests
from lxml import etree
from zatca_erpgulf.zatca_erpgulf.sign_invoice import (
    xml_base64_decode,
    get_api_url,
    success_log,
    error_log,
)

CONTENT_TYPE_JSON = "application/json"


def extract_invoice_data_from_field(file_path):
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
        return {"error": f"Error parsing or extracting data: {e}"}


def reporting_api_machine(
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
        if not pos_invoice_doc.custom_zatca_pos_name:
            frappe.throw(f"ZATCA POS name is missing for invoice {invoice_number}.")

        zatca_settings = frappe.get_doc(
            "Zatca Multiple Setting", pos_invoice_doc.custom_zatca_pos_name
        )
        production_csid = zatca_settings.custom_final_auth_csid

        if not production_csid:
            frappe.throw(
                f"Production CSID is missing in ZATCA settings for {company_abbr}."
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
                success_log(response.text, uuid1, invoice_number)
            else:
                error_log()
        except (ValueError, TypeError, KeyError) as e:
            frappe.throw(("Error in reporting API-2 " f"error: {str(e)}"))

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.throw(("Error in reporting API-1 " f"error: {str(e)}"))


# # Path to the XML file

# custom_xml_field = "/opt/zatca-live/frappe-bench/sites/zatca-live.erpgulf.com/private/files/Cleared xml file ACC-SINV-2025-00009.xml"
# if "error" in result:
#     print(f"Error: {result['error']}")
# else:
#     print(f"UUID: {result['UUID']}")
#     print(f"DigestValue: {result['DigestValue']}")
