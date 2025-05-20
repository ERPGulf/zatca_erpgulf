"""the function for the button in  wizard"""

import json
import base64
import requests
from frappe import _
import frappe
import lxml.etree as ET


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
            _("unexpected error occurred api for company {company_abbr} " + str(e))
        )
        return None


@frappe.whitelist(allow_guest=False)
def wizard_button(company_abbr, button, pos=0, machine=None):
    """Compliance check for ZATCA based on file type and company abbreviation."""
    try:
        app_path = frappe.get_app_path("zatca_erpgulf")
        # Map buttons to their corresponding XML file paths
        button_file_mapping = {
            "simplified_invoice_button": app_path + "/simplifeid invoice.xml",
            "standard_invoice_button": app_path + "/standard invoice.xml",
            "simplified_credit_note_button": app_path + "/simplifeild credit note.xml",
            "standard_credit_note_button": app_path + "/standard credit note.xml",
            "simplified_debit_note_button": app_path + "/simplified debit note.xml",
            "standard_debit_note_button": app_path + "/standard debit note.xml",
        }

        # Determine the selected XML file based on the button clicked
        signed_xml_filename = button_file_mapping.get(button)
        if not signed_xml_filename:
            frappe.throw(f"Invalid button selected: {button}")

        # Validate and fetch company name
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(_(f"Company with abbreviation {company_abbr} not found."))

        # Parse XML and extract encoded hash a nd UUI D
        namespaces = {
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "sig": "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2",
            "sac": "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
            "xades": "http://uri.etsi.org/01903/v1.3.2#",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        }

        tree = ET.parse(signed_xml_filename)
        root = tree.getroot()

        # Extract DigestValue
        digest_value_element = root.find(
            "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@Id='invoiceSignedData']/ds:DigestValue",
            namespaces,
        )
        if digest_value_element is None or not digest_value_element.text:
            frappe.throw(_("DigestValue not found in the XML file."))
        encoded_hash = digest_value_element.text.strip()

        # Extract UUID
        uuid_element = root.find("cbc:UUID", namespaces)
        if uuid_element is None or not uuid_element.text:
            frappe.throw("UUID not found in the XML file.")
        uuid1 = uuid_element.text.strip()

        # Read and encode the entire XML file
        with open(signed_xml_filename, "rb") as file:
            xml_content = file.read()
        xml_base64_encoded = base64.b64encode(xml_content).decode("utf-8")

        # Prepare payload
        payload = json.dumps(
            {
                "invoiceHash": encoded_hash,
                "uuid": uuid1,
                "invoice": xml_base64_encoded,
            }
        )

        # Check for CSID in company doc
        # csid = company_doc.custom_basic_auth_from_csid
        # if not csid:
        #     frappe.throw(f"CSID for company {company_abbr} not found.")
        if pos == 1:
            if not machine:
                frappe.throw("Machine name is required for offline POS.")
            doc_type = "ZATCA Multiple Setting"
            doc_name = machine
            doc = frappe.get_doc(doc_type, doc_name)
        else:
            doc_type = frappe.get_doc("Company", company_name)
            doc_name = company_name
            doc = frappe.get_doc(doc_type, doc_name)

        csid = doc.custom_basic_auth_from_csid
        if not csid:
            frappe.throw(_(f"CSID not found in {doc_type} for {doc_name}."))

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
            timeout=300,
        )

        # Handle response
        if response.status_code != 200:
            frappe.throw(_(f"Error from ZATCA API: {response.text}"))

        return response.json()

    except Exception as e:
        frappe.throw(_(f"Error in wizard_button: {str(e)}"))
