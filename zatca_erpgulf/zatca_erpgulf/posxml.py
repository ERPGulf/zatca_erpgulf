#utilites for zatca2024

import frappe
import os
# frappe.init(site="prod.erpgulf.com")
# frappe.connect()
import xml.etree.ElementTree as ET
from lxml import etree
import xml.dom.minidom as minidom
import uuid 
from frappe.utils import now
import re
from lxml import etree
from frappe.utils.data import  get_time
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import json
import xml.etree.ElementTree as ElementTree

def get_Tax_for_Item(full_string,item):
            try:                                          # getting tax percentage and tax amount
                data = json.loads(full_string)
                tax_percentage=data.get(item,[0,0])[0]
                tax_amount = data.get(item, [0, 0])[1]
                return tax_amount,tax_percentage
            except Exception as e:
                    frappe.throw("error occured in tax for item"+ str(e) )

def get_ICV_code(invoice_number):
                try:
                    icv_code =  re.sub(r'\D', '', invoice_number)   # taking the number part only from doc name
                    return icv_code
                except Exception as e:
                    frappe.throw("error in getting icv number:  "+ str(e) )
                    
def  get_Issue_Time(invoice_number): 
                doc = frappe.get_doc("POS Invoice", invoice_number)
                time = get_time(doc.posting_time)
                issue_time = time.strftime("%H:%M:%S")  #time in format of  hour,mints,secnds
                # utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
                # issue_time = utc_now.strftime('%H:%M:%SZ') 
                return issue_time
  
def xml_tags():
            try: 
                invoice = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" )
                invoice.set("xmlns:cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
                invoice.set("xmlns:cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")
                invoice.set("xmlns:ext", "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2")   
                ubl_extensions = ET.SubElement(invoice, "ext:UBLExtensions")
                ubl_extension = ET.SubElement(ubl_extensions, "ext:UBLExtension")
                extension_uri = ET.SubElement(ubl_extension, "ext:ExtensionURI")
                extension_uri.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
                extension_content = ET.SubElement(ubl_extension, "ext:ExtensionContent")
                UBL_Document_Signatures = ET.SubElement(extension_content , "sig:UBLDocumentSignatures"    )
                UBL_Document_Signatures.set("xmlns:sig" , "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2")
                UBL_Document_Signatures.set("xmlns:sac" , "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2")
                UBL_Document_Signatures.set("xmlns:sbc" , "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2")
                Signature_Information = ET.SubElement(UBL_Document_Signatures , "sac:SignatureInformation"  )
                id = ET.SubElement(Signature_Information , "cbc:ID"  )
                id.text = "urn:oasis:names:specification:ubl:signature:1"
                Referenced_SignatureID = ET.SubElement(Signature_Information , "sbc:ReferencedSignatureID"  )
                Referenced_SignatureID.text = "urn:oasis:names:specification:ubl:signature:Invoice"
                Signature = ET.SubElement(Signature_Information , "ds:Signature"  )
                Signature.set("Id" , "signature" )
                Signature.set("xmlns:ds" , "http://www.w3.org/2000/09/xmldsig#" )
                Signed_Info = ET.SubElement(Signature , "ds:SignedInfo"  )
                Canonicalization_Method = ET.SubElement(Signed_Info , "ds:CanonicalizationMethod"  )
                Canonicalization_Method.set("Algorithm" , "http://www.w3.org/2006/12/xml-c14n11"  )
                Signature_Method = ET.SubElement(Signed_Info , "ds:SignatureMethod"  )
                Signature_Method.set("Algorithm" , "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"  )
                Reference = ET.SubElement(Signed_Info , "ds:Reference"  )
                Reference.set("Id"  , "invoiceSignedData")
                Reference.set("URI"  , "")
                Transforms = ET.SubElement(Reference , "ds:Transforms" )
                Transform = ET.SubElement(Transforms , "ds:Transform" )
                Transform.set("Algorithm" , "http://www.w3.org/TR/1999/REC-xpath-19991116")
                XPath = ET.SubElement(Transform , "ds:XPath" )
                XPath.text = "not(//ancestor-or-self::ext:UBLExtensions)"
                Transform2 = ET.SubElement(Transforms , "ds:Transform" )
                Transform2.set("Algorithm" , "http://www.w3.org/TR/1999/REC-xpath-19991116")
                XPath2 = ET.SubElement(Transform2 , "ds:XPath" )
                XPath2.text = "not(//ancestor-or-self::cac:Signature)"
                Transform3 = ET.SubElement(Transforms , "ds:Transform" )
                Transform3.set("Algorithm" , "http://www.w3.org/TR/1999/REC-xpath-19991116")
                XPath3 = ET.SubElement(Transform3 , "ds:XPath" )
                XPath3.text = "not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])"
                Transform4 = ET.SubElement(Transforms , "ds:Transform" )
                Transform4.set("Algorithm" , "http://www.w3.org/2006/12/xml-c14n11")
                Diges_Method = ET.SubElement(Reference , "ds:DigestMethod" )
                Diges_Method.set("Algorithm" , "http://www.w3.org/2001/04/xmlenc#sha256")
                Diges_value = ET.SubElement(Reference , "ds:DigestValue" )
                Diges_value.text = "O/vEnAxjLAlw8kQUy8nq/5n8IEZ0YeIyBFvdQA8+iFM="
                Reference2 = ET.SubElement(Signed_Info , "ds:Reference"  )
                Reference2.set("URI" , "#xadesSignedProperties")
                Reference2.set("Type" , "http://www.w3.org/2000/09/xmldsig#SignatureProperties")
                Digest_Method1 = ET.SubElement(Reference2 , "ds:DigestMethod"  )
                Digest_Method1.set("Algorithm" , "http://www.w3.org/2001/04/xmlenc#sha256")
                Digest_value1 = ET.SubElement(Reference2 , "ds:DigestValue"  )
                Digest_value1.text="YjQwZmEyMjM2NDU1YjQwNjM5MTFmYmVkODc4NjM2NTc0N2E3OGFmZjVlMzA1ODAwYWE5Y2ZmYmFjZjRiNjQxNg=="
                Signature_Value = ET.SubElement(Signature , "ds:SignatureValue"  )
                Signature_Value.text = "MEQCIDGBRHiPo6yhXIQ9df6pMEkufcGnoqYaS+O8Jn0xagBiAiBtoxpbrwfEJHhUGQHTqzD1ORX5+Z/tumM0wLfZ4cuYRg=="
                KeyInfo = ET.SubElement(Signature , "ds:KeyInfo"  )
                X509Data = ET.SubElement(KeyInfo , "ds:X509Data"  )
                X509Certificate = ET.SubElement(X509Data , "ds:X509Certificate"  )
                X509Certificate.text = "MIID6TCCA5CgAwIBAgITbwAAf8tem6jngr16DwABAAB/yzAKBggqhkjOPQQDAjBjMRUwEwYKCZImiZPyLGQBGRYFbG9jYWwxEzARBgoJkiaJk/IsZAEZFgNnb3YxFzAVBgoJkiaJk/IsZAEZFgdleHRnYXp0MRwwGgYDVQQDExNUU1pFSU5WT0lDRS1TdWJDQS0xMB4XDTIyMDkxNDEzMjYwNFoXDTI0MDkxMzEzMjYwNFowTjELMAkGA1UEBhMCU0ExEzARBgNVBAoTCjMxMTExMTExMTExDDAKBgNVBAsTA1RTVDEcMBoGA1UEAxMTVFNULTMxMTExMTExMTEwMTExMzBWMBAGByqGSM49AgEGBSuBBAAKA0IABGGDDKDmhWAITDv7LXqLX2cmr6+qddUkpcLCvWs5rC2O29W/hS4ajAK4Qdnahym6MaijX75Cg3j4aao7ouYXJ9GjggI5MIICNTCBmgYDVR0RBIGSMIGPpIGMMIGJMTswOQYDVQQEDDIxLVRTVHwyLVRTVHwzLWE4NjZiMTQyLWFjOWMtNDI0MS1iZjhlLTdmNzg3YTI2MmNlMjEfMB0GCgmSJomT8ixkAQEMDzMxMTExMTExMTEwMTExMzENMAsGA1UEDAwEMTEwMDEMMAoGA1UEGgwDVFNUMQwwCgYDVQQPDANUU1QwHQYDVR0OBBYEFDuWYlOzWpFN3no1WtyNktQdrA8JMB8GA1UdIwQYMBaAFHZgjPsGoKxnVzWdz5qspyuZNbUvME4GA1UdHwRHMEUwQ6BBoD+GPWh0dHA6Ly90c3RjcmwuemF0Y2EuZ292LnNhL0NlcnRFbnJvbGwvVFNaRUlOVk9JQ0UtU3ViQ0EtMS5jcmwwga0GCCsGAQUFBwEBBIGgMIGdMG4GCCsGAQUFBzABhmJodHRwOi8vdHN0Y3JsLnphdGNhLmdvdi5zYS9DZXJ0RW5yb2xsL1RTWkVpbnZvaWNlU0NBMS5leHRnYXp0Lmdvdi5sb2NhbF9UU1pFSU5WT0lDRS1TdWJDQS0xKDEpLmNydDArBggrBgEFBQcwAYYfaHR0cDovL3RzdGNybC56YXRjYS5nb3Yuc2Evb2NzcDAOBgNVHQ8BAf8EBAMCB4AwHQYDVR0lBBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMDMCcGCSsGAQQBgjcVCgQaMBgwCgYIKwYBBQUHAwIwCgYIKwYBBQUHAwMwCgYIKoZIzj0EAwIDRwAwRAIgOgjNPJW017lsIijmVQVkP7GzFO2KQKd9GHaukLgIWFsCIFJF9uwKhTMxDjWbN+1awsnFI7RLBRxA/6hZ+F1wtaqU"
                Object = ET.SubElement(Signature , "ds:Object"  )
                QualifyingProperties = ET.SubElement(Object , "xades:QualifyingProperties"  )
                QualifyingProperties.set("Target" , "signature")
                QualifyingProperties.set("xmlns:xades" , "http://uri.etsi.org/01903/v1.3.2#")
                SignedProperties = ET.SubElement(QualifyingProperties , "xades:SignedProperties"  )
                SignedProperties.set("Id" , "xadesSignedProperties")
                SignedSignatureProperties = ET.SubElement(SignedProperties , "xades:SignedSignatureProperties"  )
                SigningTime = ET.SubElement(SignedSignatureProperties , "xades:SigningTime"  )
                SigningTime.text = "2024-01-24T11:36:34Z"
                SigningCertificate = ET.SubElement(SignedSignatureProperties , "xades:SigningCertificate"  )
                Cert = ET.SubElement(SigningCertificate , "xades:Cert"  )
                CertDigest = ET.SubElement(Cert , "xades:CertDigest"  )
                Digest_Method2 = ET.SubElement(CertDigest , "ds:DigestMethod"  )
                Digest_Value2 = ET.SubElement(CertDigest , "ds:DigestValue"  )
                Digest_Method2.set("Algorithm" , "http://www.w3.org/2001/04/xmlenc#sha256")
                Digest_Value2.text = "YTJkM2JhYTcwZTBhZTAxOGYwODMyNzY3NTdkZDM3YzhjY2IxOTIyZDZhM2RlZGJiMGY0NDUzZWJhYWI4MDhmYg=="
                IssuerSerial = ET.SubElement(Cert , "xades:IssuerSerial"  )
                X509IssuerName = ET.SubElement(IssuerSerial , "ds:X509IssuerName"  )
                X509SerialNumber = ET.SubElement(IssuerSerial , "ds:X509SerialNumber"  )
                X509IssuerName.text = "CN=TSZEINVOICE-SubCA-1, DC=extgazt, DC=gov, DC=local"
                X509SerialNumber.text = "2475382886904809774818644480820936050208702411"
                return invoice
            except Exception as e:
                    frappe.throw("error in xml tags formation:  "+ str(e) )

def salesinvoice_data(invoice,invoice_number):
            try:
                pos_invoice_doc = frappe.get_doc('POS Invoice' ,invoice_number)
                cbc_ProfileID = ET.SubElement(invoice, "cbc:ProfileID")
                cbc_ProfileID.text = "reporting:1.0"
                cbc_ID = ET.SubElement(invoice, "cbc:ID")
                cbc_ID.text = str(pos_invoice_doc.name)
                cbc_UUID = ET.SubElement(invoice, "cbc:UUID")
                cbc_UUID.text =  str(uuid.uuid1())
                uuid1= cbc_UUID.text
                cbc_IssueDate = ET.SubElement(invoice, "cbc:IssueDate")
                cbc_IssueDate.text = str(pos_invoice_doc.posting_date)
                cbc_IssueTime = ET.SubElement(invoice, "cbc:IssueTime")
                cbc_IssueTime.text = get_Issue_Time(invoice_number)
                return invoice ,uuid1 ,pos_invoice_doc
            except Exception as e:
                    frappe.throw("error occured in salesinvoice data"+ str(e) )

def invoice_Typecode_Compliance(invoice,compliance_type):
                    # 0 is default. Not for compliance test. But normal reporting or clearance call.
                    # 1 is for compliance test. Simplified invoice
                    # 2 is for compliance test. Standard invoice
                    # 3 is for compliance test. Simplified Credit Note
                    # 4 is for compliance test. Standard Credit Note
                    # 5 is for compliance test. Simplified Debit Note
                    # 6 is for compliance test. Standard Debit Note
            # frappe.throw(str("here 5 " + str(compliance_type)))
            try:                         
                # cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                # cbc_InvoiceTypeCode.set("name", "0200000")
                # cbc_InvoiceTypeCode.text = "388"
                # return invoice
                 
                if compliance_type == "1":       # simplified invoice
                    cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode") 
                    cbc_InvoiceTypeCode.set("name", "0200000")
                    cbc_InvoiceTypeCode.text = "388"
                    
                elif compliance_type == "2":       # standard invoice
                    cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                    cbc_InvoiceTypeCode.set("name", "0100000")
                    cbc_InvoiceTypeCode.text = "388"
                  
                elif compliance_type == "3":       # simplified Credit note
                    cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                    cbc_InvoiceTypeCode.set("name", "0200000")
                    cbc_InvoiceTypeCode.text = "381"
                    
                   
                elif compliance_type == "4":       # Standard Credit note
                    cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                    cbc_InvoiceTypeCode.set("name", "0100000")
                    cbc_InvoiceTypeCode.text = "381"
                   
                elif compliance_type == "5":       # simplified Debit note
                    cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                    cbc_InvoiceTypeCode.set("name", "0211000")
                    cbc_InvoiceTypeCode.text = "383"
                   
                elif compliance_type == "6":       # Standard Debit note
                    cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                    cbc_InvoiceTypeCode.set("name", "0100000")
                    cbc_InvoiceTypeCode.text = "383"
                return invoice
                
                
                
            except Exception as e:
                    frappe.throw("error occured in Compliance typecode"+ str(e) )


def invoice_Typecode_Simplified(invoice,pos_invoice_doc):
            try:                             
                cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                if pos_invoice_doc.is_return == 0:         
                    cbc_InvoiceTypeCode.set("name", "0200000") # Simplified
                    cbc_InvoiceTypeCode.text = "388"
                elif pos_invoice_doc.is_return == 1:       # return items and simplified invoice
                    cbc_InvoiceTypeCode.set("name", "0200000")  # Simplified
                    cbc_InvoiceTypeCode.text = "381"  # Credit note
                return invoice
            except Exception as e:
                    frappe.throw("error occured in simplified invoice typecode"+ str(e) )

def invoice_Typecode_Standard(invoice,pos_invoice_doc):
            try:
                    cbc_InvoiceTypeCode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
                    cbc_InvoiceTypeCode.set("name", "0100000") # Standard
                    if pos_invoice_doc.is_return == 0:
                        cbc_InvoiceTypeCode.text = "388"
                    elif pos_invoice_doc.is_return == 1:     # return items and simplified invoice
                        cbc_InvoiceTypeCode.text = "381" # Credit note
                    return invoice
            except Exception as e:
                    frappe.throw("Error in standard invoice type code: "+ str(e))
                    
def doc_Reference(invoice,pos_invoice_doc,invoice_number):
            try:
                cbc_DocumentCurrencyCode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
                cbc_DocumentCurrencyCode.text = pos_invoice_doc.currency
                cbc_TaxCurrencyCode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
                cbc_TaxCurrencyCode.text = "SAR"  # SAR is as zatca requires tax amount in SAR
                if pos_invoice_doc.is_return == 1:
                                invoice=billing_reference_for_credit_and_debit_note(invoice,pos_invoice_doc)
                cac_AdditionalDocumentReference = ET.SubElement(invoice, "cac:AdditionalDocumentReference")
                cbc_ID_1 = ET.SubElement(cac_AdditionalDocumentReference, "cbc:ID")
                cbc_ID_1.text = "ICV"
                cbc_UUID_1 = ET.SubElement(cac_AdditionalDocumentReference, "cbc:UUID")
                cbc_UUID_1.text = str(get_ICV_code(invoice_number))
                return invoice  
            except Exception as e:
                    frappe.throw("Error occured in  reference doc" + str(e) )


def doc_Reference_compliance(invoice,pos_invoice_doc,invoice_number, compliance_type):
            try:
                cbc_DocumentCurrencyCode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
                cbc_DocumentCurrencyCode.text = pos_invoice_doc.currency
                cbc_TaxCurrencyCode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
                cbc_TaxCurrencyCode.text = pos_invoice_doc.currency
                
                if compliance_type == "3" or compliance_type == "4" or compliance_type == "5" or compliance_type == "6":
                
                    cac_BillingReference = ET.SubElement(invoice, "cac:BillingReference")
                    cac_InvoiceDocumentReference = ET.SubElement(cac_BillingReference, "cac:InvoiceDocumentReference")
                    cbc_ID13 = ET.SubElement(cac_InvoiceDocumentReference, "cbc:ID")
                    cbc_ID13.text = "6666666"  # field from return against invoice. 
                
                cac_AdditionalDocumentReference = ET.SubElement(invoice, "cac:AdditionalDocumentReference")
                cbc_ID_1 = ET.SubElement(cac_AdditionalDocumentReference, "cbc:ID")
                cbc_ID_1.text = "ICV"
                cbc_UUID_1 = ET.SubElement(cac_AdditionalDocumentReference, "cbc:UUID")
                cbc_UUID_1.text = str(get_ICV_code(invoice_number))
                return invoice  
            except Exception as e:
                    frappe.throw("Error occured in  reference doc" + str(e) )

def get_pih_for_company(pih_data, company_name):
                
                try:
                    for entry in pih_data.get("data", []):
                        if entry.get("company") == company_name:
                            return entry.get("pih")
                    frappe.throw("Error while retrieving  PIH of company for production:  " + str(e) )
                except Exception as e:
                        frappe.throw("Error in getting PIH of company for production:  " + str(e) )


def additional_Reference(invoice, company_abbr):
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc('Company', company_name)

        # Create the first AdditionalDocumentReference element for PIH
        cac_AdditionalDocumentReference2 = ET.SubElement(invoice, "cac:AdditionalDocumentReference")
        cbc_ID_1_1 = ET.SubElement(cac_AdditionalDocumentReference2, "cbc:ID")
        cbc_ID_1_1.text = "PIH"
        cac_Attachment = ET.SubElement(cac_AdditionalDocumentReference2, "cac:Attachment")
        cbc_EmbeddedDocumentBinaryObject = ET.SubElement(cac_Attachment, "cbc:EmbeddedDocumentBinaryObject")
        cbc_EmbeddedDocumentBinaryObject.set("mimeCode", "text/plain")

        # Directly retrieve the PIH data without JSON parsing
        pih = company_doc.custom_pih  # Assuming this is already in the correct format
        
        cbc_EmbeddedDocumentBinaryObject.text = pih

        # Create the second AdditionalDocumentReference element for QR
        cac_AdditionalDocumentReference22 = ET.SubElement(invoice, "cac:AdditionalDocumentReference")
        cbc_ID_1_12 = ET.SubElement(cac_AdditionalDocumentReference22, "cbc:ID")
        cbc_ID_1_12.text = "QR"
        cac_Attachment22 = ET.SubElement(cac_AdditionalDocumentReference22, "cac:Attachment")
        cbc_EmbeddedDocumentBinaryObject22 = ET.SubElement(cac_Attachment22, "cbc:EmbeddedDocumentBinaryObject")
        cbc_EmbeddedDocumentBinaryObject22.set("mimeCode", "text/plain")
        cbc_EmbeddedDocumentBinaryObject22.text = "GsiuvGjvchjbFhibcDhjv1886G"  # Example QR code

        # Create the Signature element
        cac_sign = ET.SubElement(invoice, "cac:Signature")
        cbc_id_sign = ET.SubElement(cac_sign, "cbc:ID")
        cbc_method_sign = ET.SubElement(cac_sign, "cbc:SignatureMethod")
        cbc_id_sign.text = "urn:oasis:names:specification:ubl:signature:Invoice"
        cbc_method_sign.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"

        return invoice

    except Exception as e:
        frappe.throw(f"Error occurred in additional references: {str(e)}")




def company_Data(invoice,pos_invoice_doc):
            try:
                company_doc = frappe.get_doc("Company", pos_invoice_doc.company)
                # frappe.throw(str(company_doc))
                customer_doc= frappe.get_doc("Customer",pos_invoice_doc.customer)
                cac_AccountingSupplierParty = ET.SubElement(invoice, "cac:AccountingSupplierParty")
                cac_Party_1 = ET.SubElement(cac_AccountingSupplierParty, "cac:Party")
                cac_PartyIdentification = ET.SubElement(cac_Party_1, "cac:PartyIdentification")
                cbc_ID_2 = ET.SubElement(cac_PartyIdentification, "cbc:ID")
                cbc_ID_2.set("schemeID", "CRN")
                cbc_ID_2.text =company_doc.custom_company_registration
                # frappe.throw(cbc_ID_2.text)   # COmpany CR - Need to have a field in company doctype called company_registration 
                address_list = frappe.get_list("Address", filters={"is_your_company_address": "1"}, fields=["address_line1", "address_line2","city","pincode","state"])
                # frappe.throw(str(address_list))
                if len(address_list) == 0:
                    frappe.throw("Zatca requires proper address. Please add your company address in address master")
                for address in address_list:
                    cac_PostalAddress = ET.SubElement(cac_Party_1, "cac:PostalAddress")
                    cbc_StreetName = ET.SubElement(cac_PostalAddress, "cbc:StreetName")
                    cbc_StreetName.text = address.address_line1
                    cbc_BuildingNumber = ET.SubElement(cac_PostalAddress, "cbc:BuildingNumber")
                    cbc_BuildingNumber.text = address.address_line2 
                    cbc_PlotIdentification = ET.SubElement(cac_PostalAddress, "cbc:PlotIdentification")
                    cbc_PlotIdentification.text =  address.address_line1
                    cbc_CitySubdivisionName = ET.SubElement(cac_PostalAddress, "cbc:CitySubdivisionName")
                    cbc_CitySubdivisionName.text = address.city
                    cbc_CityName = ET.SubElement(cac_PostalAddress, "cbc:CityName")
                    cbc_CityName.text = address.city
                    cbc_PostalZone = ET.SubElement(cac_PostalAddress, "cbc:PostalZone")
                    cbc_PostalZone.text = address.pincode
                    cbc_CountrySubentity = ET.SubElement(cac_PostalAddress, "cbc:CountrySubentity")
                    cbc_CountrySubentity.text = address.state
                    break
                cac_Country = ET.SubElement(cac_PostalAddress, "cac:Country")
                cbc_IdentificationCode = ET.SubElement(cac_Country, "cbc:IdentificationCode")
                cbc_IdentificationCode.text = "SA"
                #frappe.throw(f"cac:Country element created with cbc:IdentificationCode set to {cbc_IdentificationCode.text}")
                cac_PartyTaxScheme = ET.SubElement(cac_Party_1, "cac:PartyTaxScheme")
                cbc_CompanyID = ET.SubElement(cac_PartyTaxScheme, "cbc:CompanyID")
                cbc_CompanyID.text = company_doc.tax_id
                # frappe.throw(f"Company Tax ID set to: {cbc_CompanyID.text}")
                cac_TaxScheme = ET.SubElement(cac_PartyTaxScheme, "cac:TaxScheme")
                cbc_ID_3 = ET.SubElement(cac_TaxScheme, "cbc:ID")
                cbc_ID_3.text = "VAT"
                # frappe.throw(f"Tax Scheme ID set to: {cbc_ID_3.text}")
                cac_PartyLegalEntity = ET.SubElement(cac_Party_1, "cac:PartyLegalEntity")
                cbc_RegistrationName = ET.SubElement(cac_PartyLegalEntity, "cbc:RegistrationName")
                cbc_RegistrationName.text = pos_invoice_doc.company
                # frappe.throw(f"Registration Name set to: {cbc_RegistrationName.text}")
                return invoice
            except Exception as e:
                    frappe.throw("error occured in company data"+ str(e) )

def customer_Data(invoice,pos_invoice_doc):
            try:
                customer_doc= frappe.get_doc("Customer",pos_invoice_doc.customer)
                # frappe.throw(str(customer_doc))
                cac_AccountingCustomerParty = ET.SubElement(invoice, "cac:AccountingCustomerParty")
                cac_Party_2 = ET.SubElement(cac_AccountingCustomerParty, "cac:Party")
                cac_PartyIdentification_1 = ET.SubElement(cac_Party_2, "cac:PartyIdentification")
                cbc_ID_4 = ET.SubElement(cac_PartyIdentification_1, "cbc:ID")
                cbc_ID_4.set("schemeID", "CRN")
                cbc_ID_4.text =customer_doc.tax_id
                # frappe.throw(f"Customer Tax ID set to: {cbc_ID_4.text}")
                if int(frappe.__version__.split('.')[0]) == 13:
                    address = frappe.get_doc("Address", pos_invoice_doc.customer_address)    
                else:
                    address = frappe.get_doc("Address", customer_doc.customer_primary_address)
                cac_PostalAddress_1 = ET.SubElement(cac_Party_2, "cac:PostalAddress")
                cbc_StreetName_1 = ET.SubElement(cac_PostalAddress_1, "cbc:StreetName")
                cbc_StreetName_1.text = address.address_line1
                cbc_BuildingNumber_1 = ET.SubElement(cac_PostalAddress_1, "cbc:BuildingNumber")
                cbc_BuildingNumber_1.text = address.address_line2
                cbc_PlotIdentification_1 = ET.SubElement(cac_PostalAddress_1, "cbc:PlotIdentification")
                if hasattr(address, 'po_box'):
                    cbc_PlotIdentification_1.text = address.po_box
                else:
                    cbc_PlotIdentification_1.text = address.address_line1
                cbc_CitySubdivisionName_1 = ET.SubElement(cac_PostalAddress_1, "cbc:CitySubdivisionName")
                cbc_CitySubdivisionName_1.text = address.address_line2
                cbc_CityName_1 = ET.SubElement(cac_PostalAddress_1, "cbc:CityName")
                cbc_CityName_1.text = address.city
                cbc_PostalZone_1 = ET.SubElement(cac_PostalAddress_1, "cbc:PostalZone")
                cbc_PostalZone_1.text =address.pincode
                cbc_CountrySubentity_1 = ET.SubElement(cac_PostalAddress_1, "cbc:CountrySubentity")
                cbc_CountrySubentity_1.text =address.state
                cac_Country_1 = ET.SubElement(cac_PostalAddress_1, "cac:Country")
                cbc_IdentificationCode_1 = ET.SubElement(cac_Country_1, "cbc:IdentificationCode")
                cbc_IdentificationCode_1.text = "SA" 
                cac_PartyTaxScheme_1 = ET.SubElement(cac_Party_2, "cac:PartyTaxScheme")
                cac_TaxScheme_1 = ET.SubElement(cac_PartyTaxScheme_1, "cac:TaxScheme")
                cbc_ID_5 = ET.SubElement(cac_TaxScheme_1, "cbc:ID")
                cbc_ID_5.text = "VAT"
                cac_PartyLegalEntity_1 = ET.SubElement(cac_Party_2, "cac:PartyLegalEntity")
                cbc_RegistrationName_1 = ET.SubElement(cac_PartyLegalEntity_1, "cbc:RegistrationName")
                cbc_RegistrationName_1.text = pos_invoice_doc.customer
                return invoice
            except Exception as e:
                    frappe.throw("error occured in customer data"+ str(e) )

def delivery_And_PaymentMeans(invoice,pos_invoice_doc, is_return):
            try:
                cac_Delivery = ET.SubElement(invoice, "cac:Delivery")
                cbc_ActualDeliveryDate = ET.SubElement(cac_Delivery, "cbc:ActualDeliveryDate")
                cbc_ActualDeliveryDate.text = str(pos_invoice_doc.due_date)
                cac_PaymentMeans = ET.SubElement(invoice, "cac:PaymentMeans")
                cbc_PaymentMeansCode = ET.SubElement(cac_PaymentMeans, "cbc:PaymentMeansCode")
                cbc_PaymentMeansCode.text = "30"
                
                if is_return == 1:
                    cbc_InstructionNote = ET.SubElement(cac_PaymentMeans, "cbc:InstructionNote")
                    cbc_InstructionNote.text = "Cancellation"    
                return invoice
            except Exception as e:
                    frappe.throw("Delivery and payment means failed"+ str(e) )
def delivery_And_PaymentMeans_for_Compliance(invoice,pos_invoice_doc, compliance_type):
            try:
                cac_Delivery = ET.SubElement(invoice, "cac:Delivery")
                cbc_ActualDeliveryDate = ET.SubElement(cac_Delivery, "cbc:ActualDeliveryDate")
                cbc_ActualDeliveryDate.text = str(pos_invoice_doc.due_date)
                cac_PaymentMeans = ET.SubElement(invoice, "cac:PaymentMeans")
                cbc_PaymentMeansCode = ET.SubElement(cac_PaymentMeans, "cbc:PaymentMeansCode")
                cbc_PaymentMeansCode.text = "30"
                
                if compliance_type == "3" or compliance_type == "4" or compliance_type == "5" or compliance_type == "6":
                    cbc_InstructionNote = ET.SubElement(cac_PaymentMeans, "cbc:InstructionNote")
                    cbc_InstructionNote.text = "Cancellation"    
                return invoice
            except Exception as e:
                    frappe.throw("Delivery and payment means failed"+ str(e) )

def add_document_level_discount_with_tax(invoice, pos_invoice_doc):
    try:
        # Create the AllowanceCharge element
        cac_AllowanceCharge = ET.SubElement(invoice, "cac:AllowanceCharge")
        
        # ChargeIndicator
        cbc_ChargeIndicator = ET.SubElement(cac_AllowanceCharge, "cbc:ChargeIndicator")
        cbc_ChargeIndicator.text = "false"  # Indicates a discount

        # AllowanceChargeReason
        cbc_AllowanceChargeReason = ET.SubElement(cac_AllowanceCharge, "cbc:AllowanceChargeReason")
        cbc_AllowanceChargeReason.text = "Discount"

        # Assuming this is within your add_document_level_discount_with_tax function
        cbc_Amount = ET.SubElement(cac_AllowanceCharge, "cbc:Amount", currencyID=pos_invoice_doc.currency)
        base_discount_amount = pos_invoice_doc.get('discount_amount', 0.0)
        cbc_Amount.text = f"{base_discount_amount:.2f}"


        # Tax Category Section
        cac_TaxCategory = ET.SubElement(cac_AllowanceCharge, "cac:TaxCategory")
        cbc_ID = ET.SubElement(cac_TaxCategory, "cbc:ID")

        # Determine the VAT category code from the sales_invoice_doc
        if pos_invoice_doc.custom_zatca_tax_category == "Standard":
                    cbc_ID.text = "S"
        elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
                    cbc_ID.text = "Z"
        elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
                    cbc_ID.text = "E"
        elif pos_invoice_doc.custom_zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
                    cbc_ID.text = "O"
        # Retrieve the VAT percentage from the first tax entry in the sales_invoice_doc
        tax_percentage = float(pos_invoice_doc.get('taxes', [{}])[0].get('rate', 0))
        cbc_Percent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
        cbc_Percent.text = f"{float(pos_invoice_doc.taxes[0].rate):.2f}"



        cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
        cbc_TaxSchemeID = ET.SubElement(cac_TaxScheme, "cbc:ID")
        cbc_TaxSchemeID.text = "VAT"

        return invoice

    except Exception as e:
        frappe.throw("Error occurred while processing allowance charge data without template: " + str(e))

def add_document_level_discount_with_tax_template(invoice, pos_invoice_doc):
    try:
        # Create the AllowanceCharge element
        cac_AllowanceCharge = ET.SubElement(invoice, "cac:AllowanceCharge")
        
        # ChargeIndicator
        cbc_ChargeIndicator = ET.SubElement(cac_AllowanceCharge, "cbc:ChargeIndicator")
        cbc_ChargeIndicator.text = "false"  # Indicates a discount

        # AllowanceChargeReason
        cbc_AllowanceChargeReason = ET.SubElement(cac_AllowanceCharge, "cbc:AllowanceChargeReason")
        cbc_AllowanceChargeReason.text = "Discount"

        # Discount Amount
        cbc_Amount = ET.SubElement(cac_AllowanceCharge, "cbc:Amount", currencyID=pos_invoice_doc.currency)
        base_discount_amount = pos_invoice_doc.get('discount_amount', 0.0)
        cbc_Amount.text = f"{base_discount_amount:.2f}"

        # Tax Category Section
        cac_TaxCategory = ET.SubElement(cac_AllowanceCharge, "cac:TaxCategory")
        cbc_ID = ET.SubElement(cac_TaxCategory, "cbc:ID")

        # Retrieve the VAT category code from the first applicable tax template in the items
        vat_category = 'Standard'
        tax_percentage = 0.0
        for item in pos_invoice_doc.items:
            item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
            vat_category = item_tax_template.custom_zatca_tax_category
            tax_percentage = item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15
            break  # Assuming that all items will have the same tax category and percentage

        # Set VAT category code in the XML
        if vat_category == "Standard":
            cbc_ID.text = "S"
        elif vat_category == "Zero Rated":
            cbc_ID.text = "Z"
        elif vat_category == "Exempted":
            cbc_ID.text = "E"
        elif vat_category == "Services outside scope of tax / Not subject to VAT":
            cbc_ID.text = "O"
        else:
            frappe.throw("Invalid VAT category code. Must be one of 'Standard', 'Zero Rated', 'Exempted', or 'Services outside scope of tax / Not subject to VAT'.")

        # Set VAT percentage in the XML
        cbc_Percent = ET.SubElement(cac_TaxCategory, "cbc:Percent")
        cbc_Percent.text = f"{tax_percentage:.2f}"

        # Tax Scheme
        cac_TaxScheme = ET.SubElement(cac_TaxCategory, "cac:TaxScheme")
        cbc_TaxSchemeID = ET.SubElement(cac_TaxScheme, "cbc:ID")
        cbc_TaxSchemeID.text = "VAT"

        return invoice

    except Exception as e:
        frappe.throw("Error occurred while processing allowance charge data: " + str(e))

def add_line_item_discount(cac_Price, single_item, pos_invoice_doc):
    cac_AllowanceCharge = ET.SubElement(cac_Price, "cac:AllowanceCharge")

    cbc_ChargeIndicator = ET.SubElement(cac_AllowanceCharge, "cbc:ChargeIndicator")
    cbc_ChargeIndicator.text = "false"  # Indicates a discount

    cbc_AllowanceChargeReason = ET.SubElement(cac_AllowanceCharge, "cbc:AllowanceChargeReason")
    cbc_AllowanceChargeReason.text = "discount"

    cbc_Amount = ET.SubElement(cac_AllowanceCharge, "cbc:Amount", currencyID=pos_invoice_doc.currency)
    cbc_Amount.text = str(abs(single_item.discount_amount))

    cbc_BaseAmount = ET.SubElement(cac_AllowanceCharge, "cbc:BaseAmount", currencyID=pos_invoice_doc.currency)
    cbc_BaseAmount.text = str(abs(single_item.price_list_rate))


    return cac_Price


                    
                                        
def billing_reference_for_credit_and_debit_note(invoice,pos_invoice_doc):
            try:
                #details of original invoice
                cac_BillingReference = ET.SubElement(invoice, "cac:BillingReference")
                cac_InvoiceDocumentReference = ET.SubElement(cac_BillingReference, "cac:InvoiceDocumentReference")
                cbc_ID13 = ET.SubElement(cac_InvoiceDocumentReference, "cbc:ID")
                cbc_ID13.text = pos_invoice_doc.return_against  # field from return against invoice. 
                
                return invoice
            except Exception as e:
                    frappe.throw("credit and debit note billing failed"+ str(e) )

def get_exemption_reason_map():
    return {
        "VATEX-SA-29": "Financial services mentioned in Article 29 of the VAT Regulations.",
        "VATEX-SA-29-7": "Life insurance services mentioned in Article 29 of the VAT Regulations.",
        "VATEX-SA-30": "Real estate transactions mentioned in Article 30 of the VAT Regulations.",
        "VATEX-SA-32": "Export of goods.",
        "VATEX-SA-33": "Export of services.",
        "VATEX-SA-34-1": "The international transport of Goods.",
        "VATEX-SA-34-2": "International transport of passengers.",
        "VATEX-SA-34-3": "Services directly connected and incidental to a Supply of international passenger transport.",
        "VATEX-SA-34-4": "Supply of a qualifying means of transport.",
        "VATEX-SA-34-5": "Any services relating to Goods or passenger transportation, as defined in article twenty five of these Regulations.",
        "VATEX-SA-35": "Medicines and medical equipment.",
        "VATEX-SA-36": "Qualifying metals.",
        "VATEX-SA-EDU": "Private education to citizen.",
        "VATEX-SA-HEA ": "Private healthcare to citizen.",
        "VATEX-SA-MLTRY": "Supply of qualified military goods",
        "VATEX-SA-OOS": "The reason is a free text, has to be provided by the taxpayer on case to case basis."
    
    }

# def tax_Data(invoice,pos_invoice_doc):
            
#             try:
                
                
#                 taxable_amount = pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)
                
#                 cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
#                 cbc_TaxAmount_SAR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
#                 cbc_TaxAmount_SAR.set("currencyID", pos_invoice_doc.currency) # SAR is as zatca requires tax amount in SAR
#                 tax_rate = float(pos_invoice_doc.taxes[0].rate)
#                 tax_amount_without_retention = taxable_amount * tax_rate / 100
#                 cbc_TaxAmount.text = f"{abs(round(tax_amount_without_retention, 2)):.2f}"   # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
#                 #end for SAR currency
                
                
#                 # taxable_amount = pos_invoice_doc.base_total - pos_invoice_doc.get('base_discount_amount', 0.0)
#                 cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
#                 cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
#                 cbc_TaxAmount.set("currencyID", pos_invoice_doc.currency) # SAR is as zatca requires tax amount in SAR
#                 tax_amount_without_retention =  round(abs(get_tax_total_from_items(pos_invoice_doc)),2)
#                 # cbc_TaxAmount.text = str(round( tax_amount_without_retention,2))     # str( abs(sales_invoice_doc.base_total_taxes_and_charges))
#                 if float(pos_invoice_doc.taxes[0].rate) > 0:
#                     tax_rate = float(pos_invoice_doc.taxes[0].rate)
#                     tax_amount_without_retention = taxable_amount * tax_rate / 100
#                     cbc_TaxAmount.text = f"{abs(round(tax_amount_without_retention, 2)):.2f}"
#                 else:
#                       cbc_TaxAmount.text = str(round( tax_amount_without_retention,2))
                          
                
#                 cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
#                 cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
#                 cbc_TaxableAmount.set("currencyID", pos_invoice_doc.currency)
#                 # cbc_TaxableAmount.text =str(abs(round(sales_invoice_doc.net_total,2)))
#                 if float(pos_invoice_doc.taxes[0].rate) > 0:
#                     taxable_amount = pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)
#                     cbc_TaxableAmount.text = str(abs(round(taxable_amount, 2)))
#                 else:
#                       cbc_TaxableAmount.text =str(abs(round(pos_invoice_doc.net_total,2)))
                          
#                 cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
#                 cbc_TaxAmount_2.set("currencyID", pos_invoice_doc.currency)
#                 tax_rate = float(pos_invoice_doc.taxes[0].rate)
#                 cbc_TaxAmount_2.text = str(abs(round(taxable_amount * tax_rate / 100, 2)))
                
#                 # cbc_TaxAmount_2.text = str(round( tax_amount_without_retention,2))# str(abs(sales_invoice_doc.base_total_taxes_and_charges))
#                 cac_TaxCategory_1 = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
#                 cbc_ID_8 = ET.SubElement(cac_TaxCategory_1, "cbc:ID")
#                 if pos_invoice_doc.custom_zatca_tax_category == "Standard":
#                     cbc_ID_8.text = "S"
#                 elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
#                     cbc_ID_8.text = "Z"
#                 elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
#                     cbc_ID_8.text = "E"
#                 elif pos_invoice_doc.custom_zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
#                     cbc_ID_8.text = "O"
#                 cbc_Percent_1 = ET.SubElement(cac_TaxCategory_1, "cbc:Percent")
#                 # cbc_Percent_1.text = str(sales_invoice_doc.taxes[0].rate)
#                 cbc_Percent_1.text = f"{float(pos_invoice_doc.taxes[0].rate):.2f}" 
#                 exemption_reason_map = get_exemption_reason_map()
#                 if pos_invoice_doc.custom_zatca_tax_category != "Standard":
#                     cbc_TaxExemptionReasonCode = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReasonCode")
#                     cbc_TaxExemptionReasonCode.text = pos_invoice_doc.custom_exemption_reason_code
#                     cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReason")
#                     reason_code = pos_invoice_doc.custom_exemption_reason_code
#                     if reason_code in exemption_reason_map:
#                         cbc_TaxExemptionReason.text = exemption_reason_map[reason_code]       
#                 cac_TaxScheme_3 = ET.SubElement(cac_TaxCategory_1, "cac:TaxScheme")
#                 cbc_ID_9 = ET.SubElement(cac_TaxScheme_3, "cbc:ID")
#                 cbc_ID_9.text = "VAT"
                
#                 cac_LegalMonetaryTotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
#                 cbc_LineExtensionAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:LineExtensionAmount")
#                 cbc_LineExtensionAmount.set("currencyID", pos_invoice_doc.currency)
#                 cbc_LineExtensionAmount.text =  str(abs(pos_invoice_doc.total))
#                 cbc_TaxExclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount")
#                 cbc_TaxExclusiveAmount.set("currencyID", pos_invoice_doc.currency)
#                 cbc_TaxExclusiveAmount.text = str(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)))
#                 cbc_TaxInclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount")
#                 cbc_TaxInclusiveAmount.set("currencyID", pos_invoice_doc.currency)
#                 cbc_TaxInclusiveAmount.text = str(round(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))

#                 # cac_LegalMonetaryTotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
#                 # cbc_LineExtensionAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:LineExtensionAmount")
#                 # cbc_LineExtensionAmount.set("currencyID", sales_invoice_doc.currency)
#                 # cbc_LineExtensionAmount.text =  str(abs(sales_invoice_doc.base_total))
#                 # cbc_TaxExclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount")
#                 # cbc_TaxExclusiveAmount.set("currencyID", sales_invoice_doc.currency)
#                 # if float(sales_invoice_doc.taxes[0].rate) > 0:
#                 #     cbc_TaxExclusiveAmount.text =str(abs(sales_invoice_doc.base_total - sales_invoice_doc.get('base_discount_amount', 0.0)))
#                 # else :
#                 #       cbc_TaxExclusiveAmount.text = str(abs(sales_invoice_doc.net_total))
#                 # cbc_TaxInclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount")
#                 # cbc_TaxInclusiveAmount.set("currencyID", sales_invoice_doc.currency)
#                 # if float(sales_invoice_doc.taxes[0].rate) > 0:
#                 #     cbc_TaxInclusiveAmount.text = str(round(abs(sales_invoice_doc.base_total - sales_invoice_doc.get('base_discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))
#                 # else:
#                 #       cbc_TaxInclusiveAmount.text = str(round(abs(sales_invoice_doc.net_total) + abs(tax_amount_without_retention),2))
#                 cbc_AllowanceTotalAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:AllowanceTotalAmount")
#                 cbc_AllowanceTotalAmount.set("currencyID", pos_invoice_doc.currency)
#                 cbc_AllowanceTotalAmount.text = str(round(abs(pos_invoice_doc.get('discount_amount', 0.0)), 2))
#                 # cbc_AllowanceTotalAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:AllowanceTotalAmount")
#                 # cbc_AllowanceTotalAmount.set("currencyID", sales_invoice_doc.currency)
#                 # cbc_AllowanceTotalAmount.text = str(round(abs(discount), 2))
#                 # cbc_PayableAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableAmount")
#                 # cbc_PayableAmount.set("currencyID", sales_invoice_doc.currency)
#                 # if float(sales_invoice_doc.taxes[0].rate) > 0:
#                 #     cbc_PayableAmount.text = str(round(abs(sales_invoice_doc.base_total - sales_invoice_doc.get('base_discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))
#                 # else :
#                 #       cbc_PayableAmount.text = str(round(abs(sales_invoice_doc.net_total) + abs(tax_amount_without_retention),2))
#                 cbc_PayableAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableAmount")
#                 cbc_PayableAmount.set("currencyID", pos_invoice_doc.currency)
#                 cbc_PayableAmount.text = str(round(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))
#                 return invoice
             
#             except Exception as e:
#                         frappe.throw("error occured in tax data"+ str(e) )


def tax_Data(invoice, pos_invoice_doc):
    try:
        # Handle SAR-specific logic
        if pos_invoice_doc.currency == "SAR":
            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount_SAR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount_SAR.set("currencyID", "SAR")  # ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(abs(get_tax_total_from_items(pos_invoice_doc)), 2)
            cbc_TaxAmount_SAR.text = str(tax_amount_without_retention_sar)  # Tax amount in SAR

            taxable_amount = pos_invoice_doc.base_total - pos_invoice_doc.get('base_discount_amount', 0.0)
            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount.set("currencyID", pos_invoice_doc.currency)
            tax_amount_without_retention = round(abs(get_tax_total_from_items(pos_invoice_doc)), 2)
            
            
            tax_rate = float(pos_invoice_doc.taxes[0].rate)
            tax_amount_without_retention = taxable_amount * float(pos_invoice_doc.taxes[0].rate) / 100
            cbc_TaxAmount.text = f"{abs(round(tax_amount_without_retention, 2)):.2f}"

            # Tax Subtotal
            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
            cbc_TaxableAmount.set("currencyID", pos_invoice_doc.currency)

            
            taxable_amount = pos_invoice_doc.base_total - pos_invoice_doc.get('base_discount_amount', 0.0)
            cbc_TaxableAmount.text = str(abs(round(taxable_amount, 2)))
            
            tax_rate = float(pos_invoice_doc.taxes[0].rate)
            cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
            cbc_TaxAmount_2.set("currencyID", pos_invoice_doc.currency)
            cbc_TaxAmount_2.text = str(abs(round(taxable_amount * float(pos_invoice_doc.taxes[0].rate) / 100, 2)))

        # Handle USD-specific logic
        else:
            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount_USD_1 = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount_USD_1.set("currencyID", pos_invoice_doc.currency)  # USD currency
            taxable_amount_1 = pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)
            tax_rate = float(pos_invoice_doc.taxes[0].rate)
            tax_amount_without_retention = taxable_amount_1 * float(pos_invoice_doc.taxes[0].rate) / 100
            cbc_TaxAmount_USD_1.text = str(round(tax_amount_without_retention, 2))
            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount_USD = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount_USD.set("currencyID", pos_invoice_doc.currency)  # USD currency
            taxable_amount_1 = pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)
            tax_rate = float(pos_invoice_doc.taxes[0].rate)
            tax_amount_without_retention = taxable_amount_1 * float(pos_invoice_doc.taxes[0].rate) / 100
            cbc_TaxAmount_USD.text = str(round(tax_amount_without_retention, 2))

            # Tax Subtotal
            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
            cbc_TaxableAmount.set("currencyID", pos_invoice_doc.currency)
            cbc_TaxableAmount.text = str(abs(round(taxable_amount_1, 2)))

            cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
            cbc_TaxAmount_2.set("currencyID", pos_invoice_doc.currency)
            cbc_TaxAmount_2.text = str(abs(round(taxable_amount_1 * float(pos_invoice_doc.taxes[0].rate) / 100, 2)))

        # Tax Category and Scheme
        

        cac_TaxCategory_1 = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
        cbc_ID_8 = ET.SubElement(cac_TaxCategory_1, "cbc:ID")
        
        if pos_invoice_doc.custom_zatca_tax_category == "Standard":
            cbc_ID_8.text = "S"
        elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
            cbc_ID_8.text = "Z"
        elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
            cbc_ID_8.text = "E"
        elif pos_invoice_doc.custom_zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
            cbc_ID_8.text = "O"
        
        cbc_Percent_1 = ET.SubElement(cac_TaxCategory_1, "cbc:Percent")
        cbc_Percent_1.text = f"{float(pos_invoice_doc.taxes[0].rate):.2f}"

        # Exemption Reason (if applicable)
        exemption_reason_map = get_exemption_reason_map()
        if pos_invoice_doc.custom_zatca_tax_category != "Standard":
            cbc_TaxExemptionReasonCode = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReasonCode")
            cbc_TaxExemptionReasonCode.text = pos_invoice_doc.custom_exemption_reason_code
            cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReason")
            reason_code = pos_invoice_doc.custom_exemption_reason_code
            if reason_code in exemption_reason_map:
                cbc_TaxExemptionReason.text = exemption_reason_map[reason_code]
        
        # Tax Scheme
        cac_TaxScheme_3 = ET.SubElement(cac_TaxCategory_1, "cac:TaxScheme")
        cbc_ID_9 = ET.SubElement(cac_TaxScheme_3, "cbc:ID")
        cbc_ID_9.text = "VAT"

        # Legal Monetary Total (adjust for both SAR and USD)
        cac_LegalMonetaryTotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
        cbc_LineExtensionAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:LineExtensionAmount")
        cbc_LineExtensionAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_LineExtensionAmount.text = str(abs(pos_invoice_doc.total))

        cbc_TaxExclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount")
        cbc_TaxExclusiveAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_TaxExclusiveAmount.text = str(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)))

        cbc_TaxInclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount")
        cbc_TaxInclusiveAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_TaxInclusiveAmount.text = "{:.2f}".format(round(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))

        cbc_AllowanceTotalAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:AllowanceTotalAmount")
        cbc_AllowanceTotalAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_AllowanceTotalAmount.text = str(abs(pos_invoice_doc.get('discount_amount', 0.0)))

        cbc_PayableAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableAmount")
        cbc_PayableAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_PayableAmount.text = "{:.2f}".format(round(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))

        return invoice

    except Exception as e:
        frappe.throw("Error occurred in tax data: " + str(e))

# def tax_Data_with_template(invoice, pos_invoice_doc):
#     try:
#         # Initialize tax category totals
#         tax_category_totals = {}
#         for item in pos_invoice_doc.items:
#             item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
#             zatca_tax_category = item_tax_template.custom_zatca_tax_category

#             if zatca_tax_category not in tax_category_totals:
#                 tax_category_totals[zatca_tax_category] = {
#                     "taxable_amount": 0,
#                     "tax_amount": 0,
#                     "tax_rate": item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15,
#                     "exemption_reason_code": item_tax_template.custom_exemption_reason_code
#                 }

#             tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.base_amount)

#         first_tax_category = next(iter(tax_category_totals))  # Get the first tax category
#         base_discount_amount = pos_invoice_doc.get('base_discount_amount', 0.0)

#         # Subtract the base discount from the taxable amount of the first tax category
#         tax_category_totals[first_tax_category]["taxable_amount"] -= base_discount_amount

#         total_tax = sum(
#             tax_category_totals[zatca_tax_category]["taxable_amount"] * (tax_category_totals[zatca_tax_category]["tax_rate"] / 100)
#             for zatca_tax_category in tax_category_totals
#         )

#         # For foreign currency
#         if pos_invoice_doc.currency != "SAR":
#             cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
#             cbc_TaxAmount_SAR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
#             cbc_TaxAmount_SAR.set("currencyID", "SAR")  # SAR is as ZATCA requires tax amount in SAR
#             tax_amount_without_retention_sar = round(pos_invoice_doc.conversion_rate * abs(total_tax), 2)
#             cbc_TaxAmount_SAR.text = str(round(tax_amount_without_retention_sar, 2))

#         # For SAR currency
#         if pos_invoice_doc.currency == "SAR":
#             cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
#             cbc_TaxAmount_SAR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
#             cbc_TaxAmount_SAR.set("currencyID", "SAR")  # SAR is as ZATCA requires tax amount in SAR
#             tax_amount_without_retention_sar = round(abs(total_tax), 2)
#             cbc_TaxAmount_SAR.text = str(round(tax_amount_without_retention_sar, 2))

#         cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
#         cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
#         cbc_TaxAmount.set("currencyID", pos_invoice_doc.currency)
#         tax_amount_without_retention = round(abs(total_tax), 2)
#         cbc_TaxAmount.text = str(round(tax_amount_without_retention, 2))

#         processed_tax_templates = set()

#         # Group items by ZATCA tax category
#         tax_category_totals = {}

#         for item in pos_invoice_doc.items:
#             item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
#             zatca_tax_category = item_tax_template.custom_zatca_tax_category

#             if zatca_tax_category not in tax_category_totals:
#                 tax_category_totals[zatca_tax_category] = {
#                     "taxable_amount": 0,
#                     "tax_amount": 0,
#                     "tax_rate": item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15,
#                     "exemption_reason_code": item_tax_template.custom_exemption_reason_code
#                 }

#             tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.base_amount)

#         first_tax_category = next(iter(tax_category_totals))
#         tax_category_totals[first_tax_category]["taxable_amount"] -= pos_invoice_doc.get('base_discount_amount', 0.0)

#         for item in pos_invoice_doc.items:
#             item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
#             zatca_tax_category = item_tax_template.custom_zatca_tax_category

#             if zatca_tax_category not in tax_category_totals:
#                 tax_category_totals[zatca_tax_category] = {
#                     "taxable_amount": 0,
#                     "tax_amount": 0,
#                     "tax_rate": item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15,
#                     "exemption_reason_code": item_tax_template.custom_exemption_reason_code
#                 }

#         for zatca_tax_category, totals in tax_category_totals.items():
#             tax_category_totals[zatca_tax_category]["tax_amount"] += abs(
#                 round(tax_category_totals[zatca_tax_category]["taxable_amount"] * tax_category_totals[zatca_tax_category]["tax_rate"] / 100, 2)
#             )

#         # Create XML elements for each ZATCA tax category
#         for zatca_tax_category, totals in tax_category_totals.items():
#             cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
#             cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
#             cbc_TaxableAmount.set("currencyID", pos_invoice_doc.currency)
#             cbc_TaxableAmount.text = str(totals["taxable_amount"])

#             cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
#             cbc_TaxAmount_2.set("currencyID", pos_invoice_doc.currency)
#             cbc_TaxAmount_2.text = str(round(totals["tax_amount"], 2))

#             cac_TaxCategory_1 = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
#             cbc_ID_8 = ET.SubElement(cac_TaxCategory_1, "cbc:ID")

#             if zatca_tax_category == "Standard":
#                 cbc_ID_8.text = "S"
#             elif zatca_tax_category == "Zero Rated":
#                 cbc_ID_8.text = "Z"
#             elif zatca_tax_category == "Exempted":
#                 cbc_ID_8.text = "E"
#             elif zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
#                 cbc_ID_8.text = "O"

#             cbc_Percent_1 = ET.SubElement(cac_TaxCategory_1, "cbc:Percent")
#             cbc_Percent_1.text = f"{totals['tax_rate']:.2f}"

#             if zatca_tax_category != "Standard":
#                 cbc_TaxExemptionReasonCode = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReasonCode")
#                 cbc_TaxExemptionReasonCode.text = totals["exemption_reason_code"]
#                 cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReason")

#                 exemption_reason_map = get_exemption_reason_map()
#                 if totals["exemption_reason_code"] in exemption_reason_map:
#                     cbc_TaxExemptionReason.text = exemption_reason_map[totals["exemption_reason_code"]]

#             cac_TaxScheme = ET.SubElement(cac_TaxCategory_1, "cac:TaxScheme")
#             cbc_TaxScheme_ID = ET.SubElement(cac_TaxScheme, "cbc:ID")
#             cbc_TaxScheme_ID.text = "VAT"

#         # Discount
#         cac_LegalMonetaryTotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
#         cbc_LineExtensionAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:LineExtensionAmount")
#         cbc_LineExtensionAmount.set("currencyID", pos_invoice_doc.currency)
#         cbc_LineExtensionAmount.text = str(abs(pos_invoice_doc.base_total))

#         # Tax-Exclusive Amount (base_total - base_discount_amount)
#         cbc_TaxExclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount")
#         cbc_TaxExclusiveAmount.set("currencyID", pos_invoice_doc.currency)
#         cbc_TaxExclusiveAmount.text = str(abs(pos_invoice_doc.base_total - pos_invoice_doc.get('base_discount_amount', 0.0)))

#         # Tax-Inclusive Amount (Tax-Exclusive Amount + tax_amount_without_retention)
#         cbc_TaxInclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount")
#         cbc_TaxInclusiveAmount.set("currencyID", pos_invoice_doc.currency)
#         cbc_TaxInclusiveAmount.text = str(round(abs(pos_invoice_doc.base_total - pos_invoice_doc.get('base_discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))

#         cbc_AllowanceTotalAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:AllowanceTotalAmount")
#         cbc_AllowanceTotalAmount.set("currencyID", pos_invoice_doc.currency)
#         cbc_AllowanceTotalAmount.text = str(round(abs(pos_invoice_doc.get('base_discount_amount', 0.0)), 2))

#         cbc_PayableAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableAmount")
#         cbc_PayableAmount.set("currencyID", pos_invoice_doc.currency)
#         cbc_PayableAmount.text = str(round(abs(pos_invoice_doc.base_total - pos_invoice_doc.get('base_discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))

#         return invoice

#     except Exception as e:
#         frappe.throw("Error occurred in tax data: " + str(e))
def tax_Data_with_template(invoice, pos_invoice_doc):
    try:
        # Initialize tax category totals
        tax_category_totals = {}
        for item in pos_invoice_doc.items:
            item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
            zatca_tax_category = item_tax_template.custom_zatca_tax_category

            if zatca_tax_category not in tax_category_totals:
                tax_category_totals[zatca_tax_category] = {
                    "taxable_amount": 0,
                    "tax_amount": 0,
                    "tax_rate": item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15,
                    "exemption_reason_code": item_tax_template.custom_exemption_reason_code
                }
            if pos_invoice_doc.currency == "SAR" :
                  tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.base_amount)
            else : 
                  tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.amount)     

        first_tax_category = next(iter(tax_category_totals))  # Get the first tax category
        base_discount_amount = pos_invoice_doc.get('discount_amount', 0.0)

        # Subtract the base discount from the taxable amount of the first tax category
        tax_category_totals[first_tax_category]["taxable_amount"] -= base_discount_amount

        total_tax = sum(
            tax_category_totals[zatca_tax_category]["taxable_amount"] * (tax_category_totals[zatca_tax_category]["tax_rate"] / 100)
            for zatca_tax_category in tax_category_totals
        )

        # For foreign currency
        

        # For SAR currency
        if pos_invoice_doc.currency == "SAR":
            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount_SAR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount_SAR.set("currencyID", "SAR")  # SAR is as ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_TaxAmount_SAR.text = str(round(tax_amount_without_retention_sar, 2))

            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount.set("currencyID", pos_invoice_doc.currency)
            tax_amount_without_retention = round(abs(total_tax), 2)
            cbc_TaxAmount.text = str(round(tax_amount_without_retention, 2))
        else :
            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount_SAR = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount_SAR.set("currencyID", pos_invoice_doc.currency)  # SAR is as ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(abs(total_tax), 2)
            cbc_TaxAmount_SAR.text = str(round(tax_amount_without_retention_sar, 2))

            cac_TaxTotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_TaxAmount = ET.SubElement(cac_TaxTotal, "cbc:TaxAmount")
            cbc_TaxAmount.set("currencyID", pos_invoice_doc.currency)
            tax_amount_without_retention = round(abs(total_tax), 2)
            cbc_TaxAmount.text = str(round(tax_amount_without_retention, 2))    


        processed_tax_templates = set()

        # Group items by ZATCA tax category
        tax_category_totals = {}

        for item in pos_invoice_doc.items:
            item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
            zatca_tax_category = item_tax_template.custom_zatca_tax_category

            if zatca_tax_category not in tax_category_totals:
                tax_category_totals[zatca_tax_category] = {
                    "taxable_amount": 0,
                    "tax_amount": 0,
                    "tax_rate": item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15,
                    "exemption_reason_code": item_tax_template.custom_exemption_reason_code
                }
            if pos_invoice_doc.currency == "SAR":
                  tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.base_amount)
            else :
                  tax_category_totals[zatca_tax_category]["taxable_amount"] += abs(item.amount)      

        first_tax_category = next(iter(tax_category_totals))
        tax_category_totals[first_tax_category]["taxable_amount"] -= pos_invoice_doc.get('discount_amount', 0.0)

        for item in pos_invoice_doc.items:
            item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
            zatca_tax_category = item_tax_template.custom_zatca_tax_category

            if zatca_tax_category not in tax_category_totals:
                tax_category_totals[zatca_tax_category] = {
                    "taxable_amount": 0,
                    "tax_amount": 0,
                    "tax_rate": item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15,
                    "exemption_reason_code": item_tax_template.custom_exemption_reason_code
                }

        for zatca_tax_category, totals in tax_category_totals.items():
            tax_category_totals[zatca_tax_category]["tax_amount"] += abs(
                round(tax_category_totals[zatca_tax_category]["taxable_amount"] * tax_category_totals[zatca_tax_category]["tax_rate"] / 100, 2)
            )

        # Create XML elements for each ZATCA tax category
        for zatca_tax_category, totals in tax_category_totals.items():
            cac_TaxSubtotal = ET.SubElement(cac_TaxTotal, "cac:TaxSubtotal")
            cbc_TaxableAmount = ET.SubElement(cac_TaxSubtotal, "cbc:TaxableAmount")
            cbc_TaxableAmount.set("currencyID", pos_invoice_doc.currency)
            cbc_TaxableAmount.text = str(totals["taxable_amount"])

            cbc_TaxAmount_2 = ET.SubElement(cac_TaxSubtotal, "cbc:TaxAmount")
            cbc_TaxAmount_2.set("currencyID", pos_invoice_doc.currency)
            cbc_TaxAmount_2.text = str(round(totals["tax_amount"], 2))

            cac_TaxCategory_1 = ET.SubElement(cac_TaxSubtotal, "cac:TaxCategory")
            cbc_ID_8 = ET.SubElement(cac_TaxCategory_1, "cbc:ID")

            if zatca_tax_category == "Standard":
                cbc_ID_8.text = "S"
            elif zatca_tax_category == "Zero Rated":
                cbc_ID_8.text = "Z"
            elif zatca_tax_category == "Exempted":
                cbc_ID_8.text = "E"
            elif zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
                cbc_ID_8.text = "O"

            cbc_Percent_1 = ET.SubElement(cac_TaxCategory_1, "cbc:Percent")
            cbc_Percent_1.text = f"{totals['tax_rate']:.2f}"

            if zatca_tax_category != "Standard":
                cbc_TaxExemptionReasonCode = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReasonCode")
                cbc_TaxExemptionReasonCode.text = totals["exemption_reason_code"]
                cbc_TaxExemptionReason = ET.SubElement(cac_TaxCategory_1, "cbc:TaxExemptionReason")

                exemption_reason_map = get_exemption_reason_map()
                if totals["exemption_reason_code"] in exemption_reason_map:
                    cbc_TaxExemptionReason.text = exemption_reason_map[totals["exemption_reason_code"]]

            cac_TaxScheme = ET.SubElement(cac_TaxCategory_1, "cac:TaxScheme")
            cbc_TaxScheme_ID = ET.SubElement(cac_TaxScheme, "cbc:ID")
            cbc_TaxScheme_ID.text = "VAT"

        # Discount
        cac_LegalMonetaryTotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
        cbc_LineExtensionAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:LineExtensionAmount")
        cbc_LineExtensionAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_LineExtensionAmount.text = str(abs(pos_invoice_doc.total))

        # Tax-Exclusive Amount (base_total - base_discount_amount)
        cbc_TaxExclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxExclusiveAmount")
        cbc_TaxExclusiveAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_TaxExclusiveAmount.text = str(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)))

        # Tax-Inclusive Amount (Tax-Exclusive Amount + tax_amount_without_retention)
        cbc_TaxInclusiveAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:TaxInclusiveAmount")
        cbc_TaxInclusiveAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_TaxInclusiveAmount.text = str(round(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))

        cbc_AllowanceTotalAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:AllowanceTotalAmount")
        cbc_AllowanceTotalAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_AllowanceTotalAmount.text = str(round(abs(pos_invoice_doc.get('discount_amount', 0.0)), 2))

        cbc_PayableAmount = ET.SubElement(cac_LegalMonetaryTotal, "cbc:PayableAmount")
        cbc_PayableAmount.set("currencyID", pos_invoice_doc.currency)
        cbc_PayableAmount.text = str(round(abs(pos_invoice_doc.total - pos_invoice_doc.get('discount_amount', 0.0)) + abs(tax_amount_without_retention), 2))

        return invoice

    except Exception as e:
        frappe.throw("Error occurred in tax data: " + str(e))




def get_tax_total_from_items(pos_invoice_doc):
            try:
                total_tax = 0
                for single_item in pos_invoice_doc.items : 
                    item_tax_amount,tax_percent =  get_Tax_for_Item(pos_invoice_doc.taxes[0].item_wise_tax_detail,single_item.item_code)
                    total_tax = total_tax + (single_item.net_amount * (tax_percent/100))
                return total_tax 
            except Exception as e:
                    frappe.throw("Error occured in get_tax_total_from_items "+ str(e) )

# def item_data(invoice,pos_invoice_doc):
#             try:
#                 for single_item in pos_invoice_doc.items : 
#                     item_tax_amount,item_tax_percentage =  get_Tax_for_Item(pos_invoice_doc.taxes[0].item_wise_tax_detail,single_item.item_code)
#                     cac_InvoiceLine = ET.SubElement(invoice, "cac:InvoiceLine")
#                     cbc_ID_10 = ET.SubElement(cac_InvoiceLine, "cbc:ID")
#                     cbc_ID_10.text = str(single_item.idx)
#                     cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity")
#                     cbc_InvoicedQuantity.set("unitCode", str(single_item.uom))
#                     cbc_InvoicedQuantity.text = str(abs(single_item.qty))
#                     cbc_LineExtensionAmount_1 = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount")
#                     cbc_LineExtensionAmount_1.set("currencyID", pos_invoice_doc.currency)
#                     cbc_LineExtensionAmount_1.text=  str(abs(single_item.net_amount))
#                     cac_TaxTotal_2 = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")
#                     cbc_TaxAmount_3 = ET.SubElement(cac_TaxTotal_2, "cbc:TaxAmount")
#                     cbc_TaxAmount_3.set("currencyID", pos_invoice_doc.currency)
#                     cbc_TaxAmount_3.text = str(abs(round(item_tax_percentage * single_item.net_amount / 100,2)))
#                     cbc_RoundingAmount = ET.SubElement(cac_TaxTotal_2, "cbc:RoundingAmount")
#                     cbc_RoundingAmount.set("currencyID", pos_invoice_doc.currency)
#                     cbc_RoundingAmount.text=str(abs(round(single_item.amount + (item_tax_percentage * single_item.amount / 100),2)))
#                     cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
#                     cbc_Name = ET.SubElement(cac_Item, "cbc:Name")
#                     cbc_Name.text = single_item.item_code
#                     cac_ClassifiedTaxCategory = ET.SubElement(cac_Item, "cac:ClassifiedTaxCategory")
#                     cbc_ID_11 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:ID")
#                     if pos_invoice_doc.custom_zatca_tax_category == "Standard":
#                         cbc_ID_11 .text = "S"
#                     elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
#                         cbc_ID_11 .text = "Z"
#                     elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
#                         cbc_ID_11 .text = "E"
#                     elif pos_invoice_doc.custom_zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
#                         cbc_ID_11 .text = "O"
#                     cbc_Percent_2 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:Percent")
#                     cbc_Percent_2.text = f"{float(item_tax_percentage):.2f}"
#                     cac_TaxScheme_4 = ET.SubElement(cac_ClassifiedTaxCategory, "cac:TaxScheme")
#                     cbc_ID_12 = ET.SubElement(cac_TaxScheme_4, "cbc:ID")
#                     cbc_ID_12.text = "VAT"
#                     cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")
#                     cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount")
#                     cbc_PriceAmount.set("currencyID", pos_invoice_doc.currency)
#                     cbc_PriceAmount.text =  str(abs(single_item.base_net_rate))
                    
#                 return invoice
#             except Exception as e:
#                     frappe.throw("error occured in item data"+ str(e) )

# def item_data_with_template(invoice, pos_invoice_doc):
#     try:
#         for single_item in pos_invoice_doc.items:
#             item_tax_template = frappe.get_doc('Item Tax Template', single_item.item_tax_template)
#             item_tax_percentage = item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15
            
#             cac_InvoiceLine = ET.SubElement(invoice, "cac:InvoiceLine")
#             cbc_ID_10 = ET.SubElement(cac_InvoiceLine, "cbc:ID")
#             cbc_ID_10.text = str(single_item.idx)
#             cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity")
#             cbc_InvoicedQuantity.set("unitCode", str(single_item.uom))
#             cbc_InvoicedQuantity.text = str(abs(single_item.qty))
#             cbc_LineExtensionAmount_1 = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount")
#             cbc_LineExtensionAmount_1.set("currencyID", pos_invoice_doc.currency)
#             cbc_LineExtensionAmount_1.text = str(abs(single_item.amount))
            
#             cac_TaxTotal_2 = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")
#             cbc_TaxAmount_3 = ET.SubElement(cac_TaxTotal_2, "cbc:TaxAmount")
#             cbc_TaxAmount_3.set("currencyID", pos_invoice_doc.currency)
#             cbc_TaxAmount_3.text = str(abs(round(item_tax_percentage * single_item.amount / 100, 2)))
#             cbc_RoundingAmount = ET.SubElement(cac_TaxTotal_2, "cbc:RoundingAmount")
#             cbc_RoundingAmount.set("currencyID", pos_invoice_doc.currency)
#             cbc_RoundingAmount.text = str(abs(round(single_item.amount + (item_tax_percentage * single_item.amount / 100), 2)))
            
#             cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
#             cbc_Name = ET.SubElement(cac_Item, "cbc:Name")
#             cbc_Name.text = single_item.item_code
            
#             cac_ClassifiedTaxCategory = ET.SubElement(cac_Item, "cac:ClassifiedTaxCategory")
#             cbc_ID_11 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:ID")
#             zatca_tax_category = item_tax_template.custom_zatca_tax_category
#             if zatca_tax_category == "Standard":
#                 cbc_ID_11.text = "S"
#             elif zatca_tax_category == "Zero Rated":
#                 cbc_ID_11.text = "Z"
#             elif zatca_tax_category == "Exempted":
#                 cbc_ID_11.text = "E"
#             elif zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
#                 cbc_ID_11.text = "O"
            
#             cbc_Percent_2 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:Percent")
#             cbc_Percent_2.text = f"{float(item_tax_percentage):.2f}"
            
#             cac_TaxScheme_4 = ET.SubElement(cac_ClassifiedTaxCategory, "cac:TaxScheme")
#             cbc_ID_12 = ET.SubElement(cac_TaxScheme_4, "cbc:ID")
#             cbc_ID_12.text = "VAT"
            
#             cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")
#             cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount")
#             cbc_PriceAmount.set("currencyID", pos_invoice_doc.currency)
#             # cbc_PriceAmount.text = str(abs(single_item.base_net_rate))
#             cbc_PriceAmount.text = "{:.6f}".format(abs(single_item.rate))
            
#         return invoice
#     except Exception as e:
#         frappe.throw("Error occurred in item data" + str(e))
def item_data(invoice,pos_invoice_doc):
            try:
                for single_item in pos_invoice_doc.items : 
                    item_tax_amount,item_tax_percentage =  get_Tax_for_Item(pos_invoice_doc.taxes[0].item_wise_tax_detail,single_item.item_code)
                    cac_InvoiceLine = ET.SubElement(invoice, "cac:InvoiceLine")
                    cbc_ID_10 = ET.SubElement(cac_InvoiceLine, "cbc:ID")
                    cbc_ID_10.text = str(single_item.idx)
                    cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity")
                    cbc_InvoicedQuantity.set("unitCode", str(single_item.uom))
                    cbc_InvoicedQuantity.text = str(abs(single_item.qty))
                    cbc_LineExtensionAmount_1 = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount")
                    cbc_LineExtensionAmount_1.set("currencyID", pos_invoice_doc.currency)
                    if pos_invoice_doc.currency == "SAR":
                        cbc_LineExtensionAmount_1.text=  str(abs(single_item.base_amount))
                    else :
                        cbc_LineExtensionAmount_1.text=  str(abs(single_item.amount))    
                    cac_TaxTotal_2 = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")
                    cbc_TaxAmount_3 = ET.SubElement(cac_TaxTotal_2, "cbc:TaxAmount")
                    cbc_TaxAmount_3.set("currencyID", pos_invoice_doc.currency)
                    cbc_TaxAmount_3.text = str(abs(round(item_tax_percentage * single_item.net_amount / 100,2)))
                    cbc_RoundingAmount = ET.SubElement(cac_TaxTotal_2, "cbc:RoundingAmount")
                    cbc_RoundingAmount.set("currencyID", pos_invoice_doc.currency)
                    # cbc_RoundingAmount.text=str(abs(round(single_item.base_net_amount + (item_tax_percentage * single_item.base_net_amount / 100),2)))
                    if pos_invoice_doc.currency == "SAR":
                        if float(pos_invoice_doc.taxes[0].rate) > 0:
                            cbc_RoundingAmount.text=str(abs(round(single_item.base_amount + (item_tax_percentage * single_item.net_amount / 100),2)))
                        else:
                            cbc_RoundingAmount.text=str(abs(round(single_item.amount + (item_tax_percentage * single_item.amount / 100),2)))
                    else :
                        if float(pos_invoice_doc.taxes[0].rate) > 0:
                            cbc_RoundingAmount.text=str(abs(round(single_item.amount + (item_tax_percentage * single_item.net_amount / 100),2)))
                        else:
                            cbc_RoundingAmount.text=str(abs(round(single_item.amount + (item_tax_percentage * single_item.amount / 100),2)))
                    cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
                    cbc_Name = ET.SubElement(cac_Item, "cbc:Name")
                    cbc_Name.text = single_item.item_code
                    cac_ClassifiedTaxCategory = ET.SubElement(cac_Item, "cac:ClassifiedTaxCategory")
                    cbc_ID_11 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:ID")
                    if pos_invoice_doc.custom_zatca_tax_category == "Standard":
                        cbc_ID_11 .text = "S"
                    elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
                        cbc_ID_11 .text = "Z"
                    elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
                        cbc_ID_11 .text = "E"
                    elif pos_invoice_doc.custom_zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
                        cbc_ID_11 .text = "O"
                    cbc_Percent_2 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:Percent")
                    cbc_Percent_2.text = f"{float(item_tax_percentage):.2f}"
                    cac_TaxScheme_4 = ET.SubElement(cac_ClassifiedTaxCategory, "cac:TaxScheme")
                    cbc_ID_12 = ET.SubElement(cac_TaxScheme_4, "cbc:ID")
                    cbc_ID_12.text = "VAT"
                    cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")
                    cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount")
                    cbc_PriceAmount.set("currencyID", pos_invoice_doc.currency)
                    company_name = pos_invoice_doc.company
                    settings = frappe.get_doc('Company', company_name)
                    if settings.custom_submit_line_item_discount_to_zatca != 1:
                          cbc_PriceAmount.text =  str(abs(single_item.price_list_rate) - abs(single_item.discount_amount))
                    
                    if settings.custom_submit_line_item_discount_to_zatca == 1:            
                        cbc_PriceAmount.text = str(abs(single_item.price_list_rate) - abs(single_item.discount_amount))

                        cbc_BaseQuantity = ET.SubElement(cac_Price, "cbc:BaseQuantity", unitCode=str(single_item.uom))
                        cbc_BaseQuantity.text = "1"

                        add_line_item_discount(cac_Price,single_item,pos_invoice_doc)
                    
                return invoice
            except Exception as e:
                    frappe.throw("error occured in item data"+ str(e) )

def item_data_with_template(invoice, pos_invoice_doc):
    try:
        for single_item in pos_invoice_doc.items:
            item_tax_template = frappe.get_doc('Item Tax Template', single_item.item_tax_template)
            item_tax_percentage = item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15
            
            cac_InvoiceLine = ET.SubElement(invoice, "cac:InvoiceLine")
            cbc_ID_10 = ET.SubElement(cac_InvoiceLine, "cbc:ID")
            cbc_ID_10.text = str(single_item.idx)
            cbc_InvoicedQuantity = ET.SubElement(cac_InvoiceLine, "cbc:InvoicedQuantity")
            cbc_InvoicedQuantity.set("unitCode", str(single_item.uom))
            cbc_InvoicedQuantity.text = str(abs(single_item.qty))
            cbc_LineExtensionAmount_1 = ET.SubElement(cac_InvoiceLine, "cbc:LineExtensionAmount")
            cbc_LineExtensionAmount_1.set("currencyID", pos_invoice_doc.currency)
            cbc_LineExtensionAmount_1.text = str(abs(single_item.amount))
            
            cac_TaxTotal_2 = ET.SubElement(cac_InvoiceLine, "cac:TaxTotal")
            cbc_TaxAmount_3 = ET.SubElement(cac_TaxTotal_2, "cbc:TaxAmount")
            cbc_TaxAmount_3.set("currencyID", pos_invoice_doc.currency)
            cbc_TaxAmount_3.text = str(abs(round(item_tax_percentage * single_item.amount / 100, 2)))
            cbc_RoundingAmount = ET.SubElement(cac_TaxTotal_2, "cbc:RoundingAmount")
            cbc_RoundingAmount.set("currencyID", pos_invoice_doc.currency)
            cbc_RoundingAmount.text = str(abs(round(single_item.amount + (item_tax_percentage * single_item.amount / 100), 2)))
            
            cac_Item = ET.SubElement(cac_InvoiceLine, "cac:Item")
            cbc_Name = ET.SubElement(cac_Item, "cbc:Name")
            cbc_Name.text = single_item.item_code
            
            cac_ClassifiedTaxCategory = ET.SubElement(cac_Item, "cac:ClassifiedTaxCategory")
            cbc_ID_11 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:ID")
            zatca_tax_category = item_tax_template.custom_zatca_tax_category
            if zatca_tax_category == "Standard":
                cbc_ID_11.text = "S"
            elif zatca_tax_category == "Zero Rated":
                cbc_ID_11.text = "Z"
            elif zatca_tax_category == "Exempted":
                cbc_ID_11.text = "E"
            elif zatca_tax_category == "Services outside scope of tax / Not subject to VAT":
                cbc_ID_11.text = "O"
            
            cbc_Percent_2 = ET.SubElement(cac_ClassifiedTaxCategory, "cbc:Percent")
            cbc_Percent_2.text = f"{float(item_tax_percentage):.2f}"
            
            cac_TaxScheme_4 = ET.SubElement(cac_ClassifiedTaxCategory, "cac:TaxScheme")
            cbc_ID_12 = ET.SubElement(cac_TaxScheme_4, "cbc:ID")
            cbc_ID_12.text = "VAT"
            
            cac_Price = ET.SubElement(cac_InvoiceLine, "cac:Price")
            cbc_PriceAmount = ET.SubElement(cac_Price, "cbc:PriceAmount")
            cbc_PriceAmount.set("currencyID", pos_invoice_doc.currency)
            # cbc_PriceAmount.text = str(abs(single_item.base_net_rate))
            company_name = pos_invoice_doc.company
            settings = frappe.get_doc('Company', company_name)
            if settings.custom_submit_line_item_discount_to_zatca != 1:
                  cbc_PriceAmount.text = "{:.6f}".format(abs(single_item.rate))
            if settings.custom_submit_line_item_discount_to_zatca == 1:     
                cbc_PriceAmount.text = "{:.6f}".format(abs(single_item.rate))
                cbc_BaseQuantity = ET.SubElement(cac_Price, "cbc:BaseQuantity", unitCode=str(single_item.uom))
                cbc_BaseQuantity.text = "1"

                add_line_item_discount(cac_Price,single_item,pos_invoice_doc)
            
        return invoice
    except Exception as e:
        frappe.throw("Error occurred in item data" + str(e))




def xml_structuring(invoice,pos_invoice_doc):
            try:
                xml_declaration = "<?xml version='1.0' encoding='UTF-8'?>\n"
                tree = ET.ElementTree(invoice)
                with open(frappe.local.site + "/private/files/xml_files.xml", 'wb') as file:
                    tree.write(file, encoding='utf-8', xml_declaration=True)
                with open(frappe.local.site + "/private/files/xml_files.xml", 'r') as file:
                    xml_string = file.read()
                xml_dom = minidom.parseString(xml_string)
                pretty_xml_string = xml_dom.toprettyxml(indent="  ")   # created xml into formatted xml form 
                with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'w') as file:
                    file.write(pretty_xml_string)
                          # Attach the getting xml for each invoice
                try:
                    if frappe.db.exists("File", {"file_name": "E-invoice-" + pos_invoice_doc.name + ".xml"}):
                        frappe.db.delete("File", {"file_name": "E-invoice-" + pos_invoice_doc.name + ".xml"})
                    # if frappe.db.exists("File",{ "attached_to_name": pos_invoice_doc.name, "attached_to_doctype": pos_invoice_doc.doctype }):
                    #     frappe.db.delete("File",{ "attached_to_name":pos_invoice_doc.name, "attached_to_doctype": pos_invoice_doc.doctype })
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
                
                try:
                    fileX = frappe.get_doc(
                        {   "doctype": "File",        
                            "file_type": "xml",  
                            "file_name":  "E-invoice-" + pos_invoice_doc.name + ".xml",
                            "attached_to_doctype":pos_invoice_doc.doctype,
                            "attached_to_name":pos_invoice_doc.name, 
                            "content": pretty_xml_string,
                            "is_private": 1,})
                    fileX.save()
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
                
                try:
                    frappe.db.get_value('File', {'attached_to_name':pos_invoice_doc.name, 'attached_to_doctype': pos_invoice_doc.doctype}, ['file_name'])
                except Exception as e:
                    frappe.throw(frappe.get_traceback())
            except Exception as e:
                    frappe.throw("Error occured in XML structuring and attach. Please contact your system administrator"+ str(e) )