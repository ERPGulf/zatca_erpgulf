from lxml import etree
import hashlib
import base64 
import lxml.etree as MyTree
from datetime import datetime
import xml.etree.ElementTree as ET
import frappe
from zatca_erpgulf.zatca_erpgulf.posxml import xml_tags,salesinvoice_data,add_document_level_discount_with_tax_template,add_document_level_discount_with_tax,invoice_Typecode_Simplified,invoice_Typecode_Standard,doc_Reference,additional_Reference ,company_Data,customer_Data,delivery_And_PaymentMeans,tax_Data,item_data,xml_structuring,invoice_Typecode_Compliance,delivery_And_PaymentMeans_for_Compliance,doc_Reference_compliance,tax_Data_with_template,item_data_with_template
import pyqrcode
# frappe.init(site="prod.erpgulf.com")
# frappe.connect()
import binascii
from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.bindings._rust import ObjectIdentifier
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
import json
import requests
from cryptography.hazmat.primitives import serialization
import asn1
from zatca_erpgulf.zatca_erpgulf.sign_invoice import xml_base64_Decode,get_API_url,success_Log,error_Log,removeTags,canonicalize_xml,getInvoiceHash,digital_signature,extract_certificate_details,certificate_hash,signxml_modify,generate_Signed_Properties_Hash,populate_The_UBL_Extensions_Output,generate_tlv_xml,get_tlv_for_value,update_Qr_toXml,structuring_signedxml,attach_QR_Image,compliance_api_call


def reporting_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, pos_invoice_doc):
    try:
        # Retrieve the company abbreviation based on the company in the sales invoice
        company_abbr = frappe.db.get_value("Company", {"name": pos_invoice_doc.company}, "abbr")
        
        if not company_abbr:
            frappe.throw(f"Company with abbreviation {pos_invoice_doc.company} not found.")
        
        # Retrieve the company document using the abbreviation
        company_doc = frappe.get_doc('Company', {"abbr": company_abbr})
        
        # Prepare the payload without JSON formatting
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_Decode(signed_xmlfile_name),
        }
        
        # Directly retrieve the production CSID from the company's document field
        production_csid = company_doc.custom_basic_auth_from_production


        if production_csid:
            headers = {
                'accept': 'application/json',
                'accept-language': 'en',
                'Clearance-Status': '0',
                'Accept-Version': 'V2',
                'Authorization': 'Basic ' + production_csid,
                'Content-Type': 'application/json',
                'Cookie': 'TS0106293e=0132a679c0639d13d069bcba831384623a2ca6da47fac8d91bef610c47c7119dcdd3b817f963ec301682dae864351c67ee3a402866'
            }    
        else:
            frappe.throw(f"Production CSID for company {company_abbr} not found.")
        
        try:
            response = requests.post(
                url=get_API_url(company_abbr, base_url="invoices/reporting/single"), 
                headers=headers, 
                json=payload
            )
            
            if response.status_code in (400, 405, 406, 409):
                invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
                invoice_doc.db_set('custom_uuid', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'Not Submitted', commit=True, update_modified=True)
                frappe.throw(f"Error: The request you are sending to Zatca is in incorrect format. Please report to system administrator. Status code: {response.status_code}<br><br> {response.text}")
            
            if response.status_code in (401, 403, 407, 451):
                invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
                invoice_doc.db_set('custom_uuid', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'Not Submitted', commit=True, update_modified=True)
                frappe.throw(f"Error: Zatca Authentication failed. Your access token may be expired or not valid. Please contact your system administrator. Status code: {response.status_code}<br><br> {response.text}")
            
            if response.status_code not in (200, 202):
                invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
                invoice_doc.db_set('custom_uuid', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'Not Submitted', commit=True, update_modified=True)
                frappe.throw(f"Error: Zatca server busy or not responding. Try after sometime or contact your system administrator. Status code: {response.status_code}<br><br> {response.text}")
            
            if response.status_code in (200, 202):
                msg = "SUCCESS: <br><br>" if response.status_code == 200 else "REPORTED WITH WARNINGS: <br><br> Please copy the below message and send it to your system administrator to fix this warnings before next submission <br><br>"
                msg += f"Status Code: {response.status_code}<br><br> Zatca Response: {response.text}<br><br>"
                frappe.msgprint(msg)
                
                # Update PIH data without JSON formatting
                company_doc.custom_pih = encoded_hash
                company_doc.save(ignore_permissions=True)
                
                invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
                invoice_doc.db_set('custom_uuid', uuid1, commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'REPORTED', commit=True, update_modified=True)

                success_Log(response.text, uuid1, invoice_number)
            else:
                error_Log()
        except Exception as e:
            frappe.throw(f"Error in reporting API-2: {str(e)}")
    
    except Exception as e:
        frappe.throw(f"Error in reporting API-1: {str(e)}")



def clearance_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, pos_invoice_doc):
    try:
        # Retrieve the company name based on the abbreviation in the POS Invoice
        company_abbr = frappe.db.get_value("Company", {"name": pos_invoice_doc.company}, "abbr")
        if not company_abbr:
            frappe.throw(f"There is a problem with company name in invoice  {pos_invoice_doc.company} not found.")
       
        # Retrieve the Company document using the company name
        # company_doc = frappe.get_doc('Company', company_abbr)
        company_doc = frappe.get_doc('Company', {"abbr": company_abbr})

        # Directly retrieve the production CSID from the specific field in the Company's document
        production_csid = company_doc.custom_basic_auth_from_production or ""

        # Prepare the payload
        payload = {
            "invoiceHash": encoded_hash,
            "uuid": uuid1,
            "invoice": xml_base64_Decode(signed_xmlfile_name),
        }

        if production_csid:
            headers = {
                'accept': 'application/json',
                'accept-language': 'en',
                'Clearance-Status': '1',
                'Accept-Version': 'V2',
                'Authorization': 'Basic ' + production_csid,
                'Content-Type': 'application/json',
                'Cookie': 'TS0106293e=0132a679c03c628e6c49de86c0f6bb76390abb4416868d6368d6d7c05da619c8326266f5bc262b7c0c65a6863cd3b19081d64eee99'
            }
        else:
            frappe.throw(f"Production CSID for company {company_abbr} not found.")

        
        response = requests.post(
            url=get_API_url(company_abbr, base_url="invoices/clearance/single"), 
            headers=headers, 
            json=payload
        )

        if response.status_code in (400, 405, 406, 409):
            invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
            invoice_doc.db_set('custom_uuid', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "Not Submitted", commit=True, update_modified=True)

            frappe.throw(f"Error: The request you are sending to Zatca is in incorrect format. Status code: {response.status_code}<br><br>{response.text}")

        if response.status_code in (401, 403, 407, 451):
            invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
            invoice_doc.db_set('custom_uuid', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "Not Submitted", commit=True, update_modified=True)

            frappe.throw(f"Error: Zatca Authentication failed. Status code: {response.status_code}<br><br>{response.text}")

        if response.status_code not in (200, 202):
            invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
            invoice_doc.db_set('custom_uuid', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "Not Submitted", commit=True, update_modified=True)

            frappe.throw(f"Error: Zatca server busy or not responding. Status code: {response.status_code}")

        if response.status_code in (200, 202):
            msg = "CLEARED WITH WARNINGS: <br><br>" if response.status_code == 202 else "SUCCESS: <br><br>"
            msg += f"Status Code: {response.status_code}<br><br>Zatca Response: {response.text}<br><br>"
            frappe.msgprint(msg)

            # Update PIH in the Company doctype without JSON formatting
            company_doc.custom_pih = encoded_hash
            company_doc.save(ignore_permissions=True)

            # Update the POs Invoice with the UUID and status
            invoice_doc = frappe.get_doc('POS Invoice', invoice_number)
            invoice_doc.db_set('custom_uuid', uuid1, commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "CLEARED", commit=True, update_modified=True)

            data = response.json()
            base64_xml = data.get("clearedInvoice")
            xml_cleared = base64.b64decode(base64_xml).decode('utf-8')

            # Attach the cleared XML to the POS Invoice
            file = frappe.get_doc({
                "doctype": "File",
                "file_name": "Cleared xml file " + pos_invoice_doc.name,
                "attached_to_doctype": pos_invoice_doc.doctype,
                "attached_to_name": pos_invoice_doc.name,
                "content": xml_cleared
            })
            file.save(ignore_permissions=True)

            success_Log(response.text, uuid1, invoice_number)
            return xml_cleared
        else:
            error_Log()

    except Exception as e:
        frappe.throw("Error in clearance API: " + str(e))        


@frappe.whitelist(allow_guest=True)
def zatca_Call(invoice_number, compliance_type="0", any_item_has_tax_template=False, company_abbr=None):
    try:
        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw("Invoice Number is NOT Valid: " + str(invoice_number))

        invoice = xml_tags()
        invoice, uuid1, pos_invoice_doc = salesinvoice_data(invoice, invoice_number)

        # Get the company abbreviation
        company_abbr = frappe.db.get_value("Company", {"name": pos_invoice_doc.company}, "abbr")

        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                invoice = invoice_Typecode_Simplified(invoice, pos_invoice_doc)
            else:
                invoice = invoice_Typecode_Standard(invoice, pos_invoice_doc)
        else:
            invoice = invoice_Typecode_Compliance(invoice, compliance_type)

        invoice = doc_Reference(invoice, pos_invoice_doc, invoice_number)
        invoice = additional_Reference(invoice, company_abbr)
        invoice = company_Data(invoice, pos_invoice_doc)
        invoice = customer_Data(invoice, pos_invoice_doc)
        invoice = delivery_And_PaymentMeans(invoice, pos_invoice_doc, pos_invoice_doc.is_return)
        if not any_item_has_tax_template:
            invoice = add_document_level_discount_with_tax(invoice, pos_invoice_doc)
        else:
            invoice = add_document_level_discount_with_tax_template(invoice, pos_invoice_doc)
    
        if not any_item_has_tax_template:
            invoice = tax_Data(invoice, pos_invoice_doc)
        else:
            invoice = tax_Data_with_template(invoice, pos_invoice_doc)

        if not any_item_has_tax_template:
            invoice = item_data(invoice, pos_invoice_doc)
        else:
            invoice = item_data_with_template(invoice, pos_invoice_doc)

        pretty_xml_string = xml_structuring(invoice, pos_invoice_doc)

        try:
            with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'r') as file:
                file_content = file.read()
        except FileNotFoundError:
            frappe.throw("XML file not found")

        tag_removed_xml = removeTags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash1, encoded_hash = getInvoiceHash(canonicalized_xml)
        encoded_signature = digital_signature(hash1,company_abbr)
        issuer_name, serial_number = extract_certificate_details(company_abbr)
        encoded_certificate_hash = certificate_hash(company_abbr)
        namespaces, signing_time = signxml_modify(company_abbr)
        signed_properties_base64 = generate_Signed_Properties_Hash(signing_time, issuer_name, serial_number, encoded_certificate_hash)
        populate_The_UBL_Extensions_Output(encoded_signature, namespaces, signed_properties_base64, encoded_hash, company_abbr)
        tlv_data = generate_tlv_xml(company_abbr)

        tagsBufsArray = []
        for tag_num, tag_value in tlv_data.items():
            tagsBufsArray.append(get_tlv_for_value(tag_num, tag_value))

        qrCodeBuf = b"".join(tagsBufsArray)
        qrCodeB64 = base64.b64encode(qrCodeBuf).decode('utf-8')
        update_Qr_toXml(qrCodeB64,company_abbr)
        signed_xmlfile_name = structuring_signedxml()

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                reporting_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, pos_invoice_doc)
                attach_QR_Image(qrCodeB64, pos_invoice_doc)
            else:
                xml_cleared = clearance_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, pos_invoice_doc)
                attach_QR_Image(qrCodeB64, pos_invoice_doc)
        else:
            compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name, company_abbr)
            attach_QR_Image(qrCodeB64, pos_invoice_doc)

    except Exception as e:
        frappe.log_error(title='Zatca invoice call failed', message=frappe.get_traceback())        


@frappe.whitelist(allow_guest=True)
def zatca_Call_compliance(invoice_number, company_abbr, compliance_type="0", any_item_has_tax_template=False):

    try:
        
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc('Company', company_name)
          

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
        any_item_has_tax_template = any(item.item_tax_template for item in pos_invoice_doc.items)
        if any_item_has_tax_template and not all(item.item_tax_template for item in pos_invoice_doc.items):
            frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")

        # Process the invoice based on the compliance type
        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)
        invoice = invoice_Typecode_Compliance(invoice, compliance_type)
        invoice = doc_Reference_compliance(invoice, pos_invoice_doc, invoice_number, compliance_type)
        invoice = additional_Reference(invoice,company_abbr)
        invoice = company_Data(invoice, pos_invoice_doc)
        invoice = customer_Data(invoice, pos_invoice_doc)
        invoice = delivery_And_PaymentMeans_for_Compliance(invoice, pos_invoice_doc, compliance_type)
        if not any_item_has_tax_template:
            invoice = add_document_level_discount_with_tax(invoice, pos_invoice_doc)
        else:
            invoice = add_document_level_discount_with_tax_template(invoice, pos_invoice_doc)
    
        # Add tax and item data
        if not any_item_has_tax_template:
            invoice = tax_Data(invoice, pos_invoice_doc)
        else:
            invoice = tax_Data_with_template(invoice, pos_invoice_doc)

        if not any_item_has_tax_template:
            invoice = item_data(invoice, pos_invoice_doc)
        else:
            item_data_with_template(invoice, pos_invoice_doc)
              

        # Generate and process the XML data
        pretty_xml_string = xml_structuring(invoice, pos_invoice_doc)
        with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'r') as file:
            file_content = file.read()

        tag_removed_xml = removeTags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash1, encoded_hash = getInvoiceHash(canonicalized_xml)
        encoded_signature = digital_signature(hash1, company_abbr)
        issuer_name, serial_number = extract_certificate_details(company_abbr)
        encoded_certificate_hash = certificate_hash(company_abbr)
        namespaces, signing_time = signxml_modify(company_abbr)
        signed_properties_base64 = generate_Signed_Properties_Hash(signing_time, issuer_name, serial_number, encoded_certificate_hash)
        populate_The_UBL_Extensions_Output(encoded_signature, namespaces, signed_properties_base64, encoded_hash,company_abbr)
        
        # Generate the TLV data and QR code
        tlv_data = generate_tlv_xml(company_abbr)
        
        tagsBufsArray = []
        for tag_num, tag_value in tlv_data.items():
            tagsBufsArray.append(get_tlv_for_value(tag_num, tag_value))
        
        qrCodeBuf = b"".join(tagsBufsArray)
        qrCodeB64 = base64.b64encode(qrCodeBuf).decode('utf-8')

        update_Qr_toXml(qrCodeB64, company_abbr)
        signed_xmlfile_name = structuring_signedxml()
       
        # Make the compliance API call
        compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name, company_abbr)

    except Exception as e:
        frappe.log_error(title='Zatca invoice call failed', message=frappe.get_traceback())
        frappe.throw("Error in Zatca invoice call: " + str(e))


@frappe.whitelist(allow_guest=True)
def zatca_Background_(invoice_number):
    try:
        pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        company_name = pos_invoice_doc.company

        # Retrieve the company document to access settings
        settings = frappe.get_doc('Company', company_name)
        company_abbr = settings.abbr

        any_item_has_tax_template = any(item.item_tax_template for item in pos_invoice_doc.items)
        if any_item_has_tax_template and not all(item.item_tax_template for item in pos_invoice_doc.items):
            frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")
        tax_categories = set()
        for item in pos_invoice_doc.items:
            if item.item_tax_template:
                item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                tax_categories.add(zatca_tax_category)  
                for tax in item_tax_template.taxes:
                    tax_rate = float(tax.tax_rate)

                    if f"{tax_rate:.2f}" not in ['5.00', '15.00'] and zatca_tax_category not in ["Zero Rated", "Exempted", "Services outside scope of tax / Not subject to VAT"]:
                        frappe.throw("Zatca tax category should be 'Zero Rated', 'Exempted' or 'Services outside scope of tax / Not subject to VAT' for items with tax rate not equal to 5.00 or 15.00.")

                    if f"{tax_rate:.2f}" == '15.00' and zatca_tax_category != "Standard":
                        frappe.throw("Check the Zatca category code and enable it as standard.")
        base_discount_amount = pos_invoice_doc.get('base_discount_amount', 0.0)                
        if len(tax_categories) > 1 and base_discount_amount>0:
            frappe.throw("ZATCA does not respond for multiple items with multiple tax categories with doc-level discount. Please ensure all items have the same tax category.")
        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw("Please save and submit the invoice before sending to Zatca: " + str(invoice_number))

        if pos_invoice_doc.docstatus in [0, 2]:
            frappe.throw("Please submit the invoice before sending to Zatca: " + str(invoice_number))

        if pos_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw("Already submitted to Zakat and Tax Authority")

        if settings.custom_zatca_invoice_enabled != 1:
            frappe.throw("Zatca Invoice is not enabled in Company Settings, Please contact your system administrator")

        zatca_Call(invoice_number, "0", any_item_has_tax_template, company_abbr)

    except Exception as e:
        frappe.throw("Error in background call: " + str(e))

        
@frappe.whitelist(allow_guest=True)
def zatca_Background_on_submit(doc, method=None):
    
    try:
    
        pos_invoice_doc = doc
        invoice_number = pos_invoice_doc.name

        # Ensure the POS Invoice document is correctly loaded
        pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)

        # Retrieve the company abbreviation using the company name from the POS Invoice
        company_abbr = frappe.db.get_value("Company", {"name": pos_invoice_doc.company}, "abbr")
        if not company_abbr:
            frappe.throw(f"Company abbreviation for {pos_invoice_doc.company} not found.")
        
        any_item_has_tax_template = False

        for item in pos_invoice_doc.items:
            if item.item_tax_template:
                any_item_has_tax_template = True
                break
        
        if any_item_has_tax_template:
            for item in pos_invoice_doc.items:
                if not item.item_tax_template:
                    frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")
        tax_categories = set()
        for item in pos_invoice_doc.items:
            if item.item_tax_template:
                item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                tax_categories.add(zatca_tax_category)
                for tax in item_tax_template.taxes:
                    tax_rate = float(tax.tax_rate)
                    
                    if f"{tax_rate:.2f}" not in ['5.00', '15.00'] and zatca_tax_category not in ["Zero Rated", "Exempted", "Services outside scope of tax / Not subject to VAT"]:
                        frappe.throw("Zatca tax category should be 'Zero Rated', 'Exempted' or 'Services outside scope of tax / Not subject to VAT' for items with tax rate not equal to 5.00 or 15.00.")
                    
                    if f"{tax_rate:.2f}" == '15.00' and zatca_tax_category != "Standard":
                        frappe.throw("Check the Zatca category code and enable it as standard.")
        base_discount_amount = pos_invoice_doc.get('base_discount_amount', 0.0)                  
        if len(tax_categories) > 1 and base_discount_amount >0:
            frappe.throw("ZATCA does not respond for multiple items with multiple tax categories with doc-level discount. Please ensure all items have the same tax category.")
        # Check if Zatca Invoice is enabled in the Company document
        company_doc = frappe.get_doc('Company', {"abbr": company_abbr})
        if company_doc.custom_zatca_invoice_enabled != 1:
            frappe.throw("Zatca Invoice is not enabled in the Company settings, Please contact your system administrator")
        
        if not frappe.db.exists("POS Invoice", invoice_number):
            frappe.throw("Please save and submit the invoice before sending to Zatca:  " + str(invoice_number))
        
        if pos_invoice_doc.docstatus in [0, 2]:
            frappe.throw("Please submit the invoice before sending to Zatca:  " + str(invoice_number))
            
        if pos_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw("Already submitted to Zakat and Tax Authority")
        
    
        zatca_Call(invoice_number, "0", any_item_has_tax_template, company_abbr)
        
    except Exception as e:
        frappe.throw("Error in background call: " + str(e))

