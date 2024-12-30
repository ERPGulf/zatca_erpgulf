"""the function for the button in  wizard"""

        value = compliance_api_call(
            uuid1, encoded_hash, signed_xmlfile_name
        

import frappe
from zatca_erpgulf.zatca_erpgulf.sign_invoice_first import compliance_api_call

# Define a mapping for file paths based on compliance types
FILE_PATHS = {
    "1": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/simplifiedinvoice.xml.xml",
    "2": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/standard invoice.xml",
    "3": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/simplifeild credit note.xml.xml",
    "4": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/standard credit note.xml.xml",
    "5": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/simplified debit note.xml.xml",
    "6": "/opt/zatca/frappe-bench/apps/zatca_erpgulf/standard debit note.xml.xml",
}

@frappe.whitelist(allow_guest=False)
def wizard_button(company_abbr):
    """Compliance check for Zatca based on file type and company abbreviation."""
    try:
        # Validate and fetch company name
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)
        compliance_type = None

        # Determine compliance type based on custom validation type
        validation_type_to_compliance = {
            "Simplified Invoice": "1",
            "Standard Invoice": "2",
            "Simplified Credit Note": "3",
            "Standard Credit Note": "4",
            "Simplified Debit Note": "5",
            "Standard Debit Note": "6",
        }
        payload = json.dumps(
            {
                "invoiceHash": encoded_hash,
                "uuid": uuid1,
                "invoice": xml_base64_decode(signed_xmlfile_name),
            }
        )

        csid = company_doc.custom_basic_auth_from_csid
        if not csid:
            frappe.throw((f"CSID for company {company_abbr} not found"))

        headers = {
            "accept": "application/json",
            "Accept-Language": "en",
            "Accept-Version": "V2",
            "Authorization": "Basic " + csid,
            "Content-Type": "application/json",
        }
        # frappe.throw(get_api_url(company_abbr, base_url="compliance/invoices"))
        response = requests.request(
            "POST",
            url=get_api_url(company_abbr, base_url="compliance/invoices"),
            headers=headers,
            data=payload,
            timeout=30,
        )
        # frappe.throw(response.status_code)
        frappe.throw(response.text)

    except (ValueError, TypeError, KeyError, frappe.ValidationError) as e:
        frappe.log_error(title="Zatca invoice call failed", message=frappe.get_traceback())
        frappe.throw("Error in Zatca invoice call: " + str(e))
        return None
