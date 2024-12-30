"""the function for the button in  wizard"""

import json
import base64
import requests
import frappe


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

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(
            "unexpected error occurred api for company {company_abbr} " + str(e)
        )
        return None


@frappe.whitelist(allow_guest=False)
def wizard_button(company_abbr, button):
    """Compliance check for ZATCA based on file type and company abbreviation."""
    try:
        # Map buttons to their corresponding XML file paths
        button_file_mapping = {
            "simplified_invoice_button": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/simplifiedinvoice.xml.xml",
            "standard_invoice_button": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/standard invoice.xml",
            "simplified_credit_note_button": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/simplifeild credit note.xml.xml",
            "standard_credit_note_button": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/standard credit note.xml.xml",
            "simplified_debit_note_button": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/simplified debit note.xml.xml",
            "standard_debit_note_button": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/standard debit note.xml.xml",
        }

        # Determine the selected XML file based on the button clicked
        signed_xml_filename = button_file_mapping.get(button)
        if not signed_xml_filename:
            frappe.throw(f"Invalid button selected: {button}")

        # Validate and fetch company name
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)

        # Prepare payload
        encoded_hash = "<your_encoded_hash>"  # Replace with actual encoded hash
        uuid1 = "<your_uuid1>"  # Replace with actual UUID

        with open(signed_xml_filename, "rb") as file:
            xml_content = file.read()
        xml_base64_encoded = base64.b64encode(xml_content).decode("utf-8")

        payload = json.dumps(
            {
                "invoiceHash": encoded_hash,
                "uuid": uuid1,
                "invoice": xml_base64_encoded,
            }
        )

        # Check for CSID in company doc
        csid = company_doc.custom_basic_auth_from_csid
        if not csid:
            frappe.throw(f"CSID for company {company_abbr} not found.")

        # Define headers
        headers = {
            "accept": "application/json",
            "Accept-Language": "en",
            "Accept-Version": "V2",
            "Authorization": "Basic " + csid,
            "Content-Type": "application/json",
        }

        # API request
        response = requests.request(
            "POST",
            url=get_api_url(company_abbr, base_url="compliance/invoices"),
            headers=headers,
            data=payload,
            timeout=30,
        )

        # Handle response
        if response.status_code != 200:
            frappe.throw(f"Error from ZATCA API: {response.text}")

        return response.json()

    except Exception as e:
        frappe.throw(f"Error in wizard_button: {str(e)}")
