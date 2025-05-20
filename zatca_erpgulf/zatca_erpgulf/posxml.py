"""
This module contains functions to generate, structure, and
manage ZATCA-compliant UBL XML invoices . functions to handle company,
customer, tax, line items, discounts, delivery, and payment information.
The XML is generated according to ZATCA (Zakat, Tax, and Customs Authority)
requirements for VAT compliance in Saudi Arabia.
The primary goal of this module is to produce a UBL-compliant
 XML file for invoices, debit notes, and credit notes.
The file also handles compliance with e-invoicing and clearance rules
for ZATCA and provides support for multiple currencies (SAR and USD).
"""

import xml.etree.ElementTree as ET
import uuid
import re
import json
from frappe.utils.data import get_time
from frappe import _
import frappe


def get_tax_for_item(full_string, item):
    """Function for get tax item"""
    try:  # getting tax percentage and tax amount
        data = json.loads(full_string)
        tax_percentage = data.get(item, [0, 0])[0]
        tax_amount = data.get(item, [0, 0])[1]
        return tax_amount, tax_percentage
    except json.JSONDecodeError as e:
        frappe.throw(_("JSON decoding error occurred in tax for item: " + str(e)))
        return None
    except KeyError as e:
        frappe.throw(_(f"Key error occurred while accessing item '{item}': " + str(e)))
        return None
    except TypeError as e:
        frappe.throw(_("Type error occurred in tax for item: " + str(e)))
        return None


def get_icv_code(invoice_number):
    """Function for ICV code"""
    try:
        icv_code = re.sub(
            r"\D", "", invoice_number
        )  # taking the numb er part onl y from doc name
        return icv_code
    except TypeError as e:
        frappe.throw(_("Type error in getting ICV number: " + str(e)))
        return None
    except re.error as e:
        frappe.throw(_("Regex error in getting ICV number: " + str(e)))
        return None


def get_issue_time(invoice_number):
    """Function for Issue time"""
    doc = frappe.get_doc("POS Invoice", invoice_number)
    time = get_time(doc.posting_time)
    issue_time = time.strftime("%H:%M:%S")  # time in format of  hour,mints,secnds
    return issue_time


def xml_tags():
    """Function for XML tags"""
    try:
        invoice = ET.Element(
            "Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
        )
        invoice.set(
            "xmlns:cac",
            "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        )
        invoice.set(
            "xmlns:cbc",
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        )
        invoice.set(
            "xmlns:ext",
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        )
        ubl_extensions = ET.SubElement(invoice, "ext:UBLExtensions")
        ubl_extension = ET.SubElement(ubl_extensions, "ext:UBLExtension")
        extension_uri = ET.SubElement(ubl_extension, "ext:ExtensionURI")
        extension_uri.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
        extension_content = ET.SubElement(ubl_extension, "ext:ExtensionContent")
        ubl_document_signatures = ET.SubElement(
            extension_content, "sig:UBLDocumentSignatures"
        )
        ubl_document_signatures.set(
            "xmlns:sig",
            "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2",
        )
        ubl_document_signatures.set(
            "xmlns:sac",
            "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
        )
        ubl_document_signatures.set(
            "xmlns:sbc",
            "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2",
        )
        signature_information = ET.SubElement(
            ubl_document_signatures, "sac:SignatureInformation"
        )
        id_obj = ET.SubElement(signature_information, "cbc:ID")
        id_obj.text = "urn:oasis:names:specification:ubl:signature:1"
        referenced_signatureid = ET.SubElement(
            signature_information, "sbc:ReferencedSignatureID"
        )
        referenced_signatureid.text = (
            "urn:oasis:names:specification:ubl:signature:Invoice"
        )
        signature = ET.SubElement(signature_information, "ds:Signature")
        signature.set("Id", "signature")
        signature.set("xmlns:ds", "http://www.w3.org/2000/09/xmldsig#")
        signed_info = ET.SubElement(signature, "ds:SignedInfo")
        canonicalization_method = ET.SubElement(
            signed_info, "ds:CanonicalizationMethod"
        )
        canonicalization_method.set("Algorithm", "http://www.w3.org/2006/12/xml-c14n11")
        signature_method = ET.SubElement(signed_info, "ds:SignatureMethod")
        signature_method.set(
            "Algorithm", "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"
        )
        reference = ET.SubElement(signed_info, "ds:Reference")
        reference.set("Id", "invoiceSignedData")
        reference.set("URI", "")
        transforms = ET.SubElement(reference, "ds:Transforms")
        transform = ET.SubElement(transforms, "ds:Transform")
        transform.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
        xpath = ET.SubElement(transform, "ds:XPath")
        xpath.text = "not(//ancestor-or-self::ext:UBLExtensions)"
        transform2 = ET.SubElement(transforms, "ds:Transform")
        transform2.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
        xpath2 = ET.SubElement(transform2, "ds:XPath")
        xpath2.text = "not(//ancestor-or-self::cac:Signature)"
        transform3 = ET.SubElement(transforms, "ds:Transform")
        transform3.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
        xpath3 = ET.SubElement(transform3, "ds:XPath")
        xpath3.text = (
            "not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])"
        )
        transform4 = ET.SubElement(transforms, "ds:Transform")
        transform4.set("Algorithm", "http://www.w3.org/2006/12/xml-c14n11")
        diges_method = ET.SubElement(reference, "ds:DigestMethod")
        diges_method.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
        diges_value = ET.SubElement(reference, "ds:DigestValue")
        diges_value.text = "O/vEnAxjLAlw8kQUy8nq/5n8IEZ0YeIyBFvdQA8+iFM="
        reference2 = ET.SubElement(signed_info, "ds:Reference")
        reference2.set("URI", "#xadesSignedProperties")
        reference2.set("Type", "http://www.w3.org/2000/09/xmldsig#SignatureProperties")
        digest_method1 = ET.SubElement(reference2, "ds:DigestMethod")
        digest_method1.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
        digest_value1 = ET.SubElement(reference2, "ds:DigestValue")
        digest_value1.text = "YjQwZmEyMjM2NDU1YjQwNjM5MTFmYmVkODc4NjM2"
        signature_value = ET.SubElement(signature, "ds:SignatureValue")
        signature_value.text = (
            "MEQCIDGBRHiPo6yhXIQ9df6pMEkufcGnoqYaS+O8Jn0xagBiAiBtoxpbrwf"
        )
        keyinfo = ET.SubElement(signature, "ds:KeyInfo")
        x509data = ET.SubElement(keyinfo, "ds:X509Data")
        x509certificate = ET.SubElement(x509data, "ds:X509Certificate")
        x509certificate.text = "MIID6TCCA5CgAwIBAgITbwAAf8tem6jngr16DwABAAB"
        object_data = ET.SubElement(signature, "ds:Object")
        qualifyingproperties = ET.SubElement(object_data, "xades:QualifyingProperties")
        qualifyingproperties.set("Target", "signature")
        qualifyingproperties.set("xmlns:xades", "http://uri.etsi.org/01903/v1.3.2#")
        signedproperties = ET.SubElement(qualifyingproperties, "xades:SignedProperties")
        signedproperties.set("Id", "xadesSignedProperties")
        signedsignatureproperties = ET.SubElement(
            signedproperties, "xades:SignedSignatureProperties"
        )
        signingtime = ET.SubElement(signedsignatureproperties, "xades:SigningTime")
        signingtime.text = "2024-01-24T11:36:34Z"
        signingcertificate = ET.SubElement(
            signedsignatureproperties, "xades:SigningCertificate"
        )
        cert = ET.SubElement(signingcertificate, "xades:Cert")
        certdigest = ET.SubElement(cert, "xades:CertDigest")
        digest_method2 = ET.SubElement(certdigest, "ds:DigestMethod")
        digest_value2 = ET.SubElement(certdigest, "ds:DigestValue")
        digest_method2.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
        digest_value2.text = "YTJkM2JhYTcwZTBhZTAxOGYwODMyNzY3NTdkZDM3Yz"
        issuerserial = ET.SubElement(cert, "xades:IssuerSerial")
        x509issuername = ET.SubElement(issuerserial, "ds:X509IssuerName")
        x509serialnumber = ET.SubElement(issuerserial, "ds:X509SerialNumber")
        x509issuername.text = "CN=TSZEINVOICE-SubCA-1, DC=extgazt, DC=gov, DC=local"
        x509serialnumber.text = "2475382886904809774818644480820936050208702411"
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error in XML tags formation: {e}"))
        return None


def salesinvoice_data(invoice, invoice_number):
    """Function for sales invoice data"""
    try:
        pos_invoice_doc = frappe.get_doc("POS Invoice", invoice_number)
        cbc_profileid = ET.SubElement(invoice, "cbc:ProfileID")
        cbc_profileid.text = "reporting:1.0"
        cbc_id = ET.SubElement(invoice, "cbc:ID")
        cbc_id.text = str(pos_invoice_doc.name)
        cbc_uuid = ET.SubElement(invoice, "cbc:UUID")
        cbc_uuid.text = str(uuid.uuid1())
        uuid1 = cbc_uuid.text
        cbc_issuedate = ET.SubElement(invoice, "cbc:IssueDate")
        cbc_issuedate.text = str(pos_invoice_doc.posting_date)
        cbc_issuetime = ET.SubElement(invoice, "cbc:IssueTime")
        cbc_issuetime.text = get_issue_time(invoice_number)
        return invoice, uuid1, pos_invoice_doc
    except (AttributeError, ValueError, frappe.ValidationError) as e:
        frappe.throw(_(("Error occurred in SalesInvoice data: " f"{str(e)}")))
        return None


def invoice_typecode_compliance(invoice, compliance_type):
    """Function for check invoice typecode compliance"""
    # 0 is default. Not for compliance test. But normal reporting or clearance call.
    # 1 is for compliance test. Simplified invoice
    # 2 is for compliance test. Standard invoice
    # 3 is for compliance test. Simplified Credit Note
    # 4 is for compliance test. Standard Credit Note
    # 5 is for compliance test. Simplified Debit Note
    # 6 is for compliance test. Standard Debit Note
    # frappe.throw(str("here 5 " + str(compliance_type)))
    try:

        if compliance_type == "1":  # simplified invoice
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0200000")
            cbc_invoicetypecode.text = "388"

        elif compliance_type == "2":  # standard invoice
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0100000")
            cbc_invoicetypecode.text = "388"

        elif compliance_type == "3":  # simplified Credit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0200000")
            cbc_invoicetypecode.text = "381"

        elif compliance_type == "4":  # Standard Credit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0100000")
            cbc_invoicetypecode.text = "381"

        elif compliance_type == "5":  # simplified Debit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0211000")
            cbc_invoicetypecode.text = "383"

        elif compliance_type == "6":  # Standard Debit note
            cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
            cbc_invoicetypecode.set("name", "0100000")
            cbc_invoicetypecode.text = "383"
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error occurred in compliance typecode: {e}"))
        return None


def invoice_typecode_simplified(invoice, pos_invoice_doc):
    """function for invoice type code simplification"""
    try:
        cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
        if pos_invoice_doc.is_return == 0:
            cbc_invoicetypecode.set("name", "0200000")  # Simplified
            cbc_invoicetypecode.text = "388"
        elif pos_invoice_doc.is_return == 1:  # return items and simplified invoice
            cbc_invoicetypecode.set("name", "0200000")  # Simplified
            cbc_invoicetypecode.text = "381"  # Credit note
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error occurred in simplified invoice typecode: {e}"))
        return None


def invoice_typecode_standard(invoice, pos_invoice_doc):
    """function for invoice typecode standard"""
    try:
        cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
        cbc_invoicetypecode.set("name", "0100000")  # Standard
        if pos_invoice_doc.is_return == 0:
            cbc_invoicetypecode.text = "388"
        elif pos_invoice_doc.is_return == 1:  # return items and simplified invoice
            cbc_invoicetypecode.text = "381"  # Credit note
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error in standard invoice type code: {e}"))
        return None


def doc_reference(invoice, pos_invoice_doc, invoice_number):
    """function for doc reference"""
    try:
        cbc_documentcurrencycode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
        cbc_documentcurrencycode.text = pos_invoice_doc.currency
        cbc_taxcurrencycode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
        cbc_taxcurrencycode.text = "SAR"  # SAR is as zatca requires tax amount in SAR
        if pos_invoice_doc.is_return == 1:
            invoice = billing_reference_for_credit_and_debit_note(
                invoice, pos_invoice_doc
            )
        cac_additionaldocumentreference = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1 = ET.SubElement(cac_additionaldocumentreference, "cbc:ID")
        cbc_id_1.text = "ICV"
        cbc_uuid_1 = ET.SubElement(cac_additionaldocumentreference, "cbc:UUID")
        cbc_uuid_1.text = str(get_icv_code(invoice_number))
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error occurred in reference doc: {e}"))
        return None


def doc_reference_compliance(invoice, pos_invoice_doc, invoice_number, compliance_type):
    """Function for doc reference compliance"""
    try:
        cbc_documentcurrencycode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
        cbc_documentcurrencycode.text = pos_invoice_doc.currency
        cbc_taxcurrencycode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
        cbc_taxcurrencycode.text = pos_invoice_doc.currency

        if compliance_type in {"3", "4", "5", "6"}:

            cac_billingreference = ET.SubElement(invoice, "cac:BillingReference")
            cac_invoicedocumentreference = ET.SubElement(
                cac_billingreference, "cac:InvoiceDocumentReference"
            )
            cbc_id13 = ET.SubElement(cac_invoicedocumentreference, "cbc:ID")
            cbc_id13.text = "6666666"  # field from return against invoice.

        cac_additionaldocumentreference = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1 = ET.SubElement(cac_additionaldocumentreference, "cbc:ID")
        cbc_id_1.text = "ICV"
        cbc_uuid_1 = ET.SubElement(cac_additionaldocumentreference, "cbc:UUID")
        cbc_uuid_1.text = str(get_icv_code(invoice_number))
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error occurred in reference doc: {e}"))
        return None


def get_pih_for_company(pih_data, company_name):
    """function for get pih for company"""
    try:
        for entry in pih_data.get("data", []):
            if entry.get("company") == company_name:
                return entry.get("pih")
        frappe.throw(_("Error while retrieving  PIH of company for production:  "))
    except (KeyError, AttributeError, ValueError) as e:
        frappe.throw(
            _(f"Error in getting PIH of company '{company_name}' for production: {e}")
        )
        return None  # Ensures consistent return


def additional_reference(invoice, company_abbr, pos_invoice_doc):
    """Function for additional reference"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)

        # Create the first AdditionalDocumentReference element for PIH
        cac_additionaldocumentreference2 = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1_1 = ET.SubElement(cac_additionaldocumentreference2, "cbc:ID")
        cbc_id_1_1.text = "PIH"
        cac_attachment = ET.SubElement(
            cac_additionaldocumentreference2, "cac:Attachment"
        )
        cbc_embeddeddocumentbinaryobject = ET.SubElement(
            cac_attachment, "cbc:EmbeddedDocumentBinaryObject"
        )
        cbc_embeddeddocumentbinaryobject.set("mimeCode", "text/plain")

        # Directly retrieve the PIH data without JSON parsing
        # pih = company_doc.custom_pih  # Assuming this is already in the correct format
        if pos_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "Zatca Multiple Setting", pos_invoice_doc.custom_zatca_pos_name
            )
            pih = zatca_settings.custom_pih
        else:
            pih = company_doc.custom_pih

        cbc_embeddeddocumentbinaryobject.text = pih

        # Create the second AdditionalDocumentReference element for QR
        cac_additionaldocumentreference22 = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1_12 = ET.SubElement(cac_additionaldocumentreference22, "cbc:ID")
        cbc_id_1_12.text = "QR"
        cac_attachment22 = ET.SubElement(
            cac_additionaldocumentreference22, "cac:Attachment"
        )
        cbc_embeddeddocumentbinaryobject22 = ET.SubElement(
            cac_attachment22, "cbc:EmbeddedDocumentBinaryObject"
        )
        cbc_embeddeddocumentbinaryobject22.set("mimeCode", "text/plain")
        cbc_embeddeddocumentbinaryobject22.text = (
            "GsiuvGjvchjbFhibcDhjv1886G"  # Example QR code
        )

        # Create the Signature element
        cac_sign = ET.SubElement(invoice, "cac:Signature")
        cbc_id_sign = ET.SubElement(cac_sign, "cbc:ID")
        cbc_method_sign = ET.SubElement(cac_sign, "cbc:SignatureMethod")
        cbc_id_sign.text = "urn:oasis:names:specification:ubl:signature:Invoice"
        cbc_method_sign.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"

        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred in additional references: {e}"))
        return None


# def company_data(invoice, pos_invoice_doc):
#     """ "function for company data"""
#     try:
#         company_doc = frappe.get_doc("Company", pos_invoice_doc.company)
#         cac_accountingsupplierparty = ET.SubElement(
#             invoice, "cac:AccountingSupplierParty"
#         )
#         cac_party_1 = ET.SubElement(cac_accountingsupplierparty, "cac:Party")
#         cac_partyidentification = ET.SubElement(cac_party_1, "cac:PartyIdentification")
#         cbc_id_2 = ET.SubElement(cac_partyidentification, "cbc:ID")
#         cbc_id_2.set("schemeID", "CRN")
#         cbc_id_2.text = company_doc.custom_company_registration
#         address_list = frappe.get_list(
#             "Address",
#             filters={"is_your_company_address": "1"},
#             fields=["address_line1", "address_line2", "city", "pincode", "state"],
#         )
#         # frappe.throw(str(address_list))
#         if len(address_list) == 0:
#             frappe.throw(
#                 "Zatca requires proper address. Please add your company address in address master"
#             )

#         for address in address_list:

#             cac_postaladdress = ET.SubElement(cac_party_1, "cac:PostalAddress")
#             cbc_streetname = ET.SubElement(cac_postaladdress, "cbc:StreetName")
#             cbc_streetname.text = address.address_line1
#             cbc_buildingnumber = ET.SubElement(cac_postaladdress, "cbc:BuildingNumber")
#             cbc_buildingnumber.text = address.address_line2
#             cbc_plotidentification = ET.SubElement(
#                 cac_postaladdress, "cbc:PlotIdentification"
#             )
#             cbc_plotidentification.text = address.address_line1
#             cbc_citysubdivisionname = ET.SubElement(
#                 cac_postaladdress, "cbc:CitySubdivisionName"
#             )
#             cbc_citysubdivisionname.text = address.city
#             cbc_cityname = ET.SubElement(cac_postaladdress, "cbc:CityName")
#             cbc_cityname.text = address.city
#             cbc_postalzone = ET.SubElement(cac_postaladdress, "cbc:PostalZone")
#             cbc_postalzone.text = address.pincode
#             cbc_countrysubentity = ET.SubElement(
#                 cac_postaladdress, "cbc:CountrySubentity"
#             )
#             cbc_countrysubentity.text = address.state
#             break
#         cac_country = ET.SubElement(cac_postaladdress, "cac:Country")
#         cbc_identificationcode = ET.SubElement(cac_country, "cbc:IdentificationCode")
#         cbc_identificationcode.text = "SA"
#         cac_partytaxscheme = ET.SubElement(cac_party_1, "cac:PartyTaxScheme")
#         cbc_companyid = ET.SubElement(cac_partytaxscheme, "cbc:CompanyID")
#         cbc_companyid.text = company_doc.tax_id
#         # frappe.throw(f"Company Tax ID set to: {cbc_CompanyID.text}")
#         cac_taxscheme = ET.SubElement(cac_partytaxscheme, "cac:TaxScheme")
#         cbc_id_3 = ET.SubElement(cac_taxscheme, "cbc:ID")
#         cbc_id_3.text = "VAT"
#         # frappe.throw(f"Tax Scheme ID set to: {cbc_ID_3.text}")
#         cac_partylegalentity = ET.SubElement(cac_party_1, "cac:PartyLegalEntity")
#         cbc_registrationname = ET.SubElement(
#             cac_partylegalentity, "cbc:RegistrationName"
#         )
#         cbc_registrationname.text = pos_invoice_doc.company
#         # frappe.throw(f"Registration Name set to: {cbc_RegistrationName.text}")
#         return invoice
#     except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
#         frappe.throw(f"Error occurred in company data: {e}")
#         return None


def get_address(pos_invoice_doc, company_doc):
    """
    Fetches the appropriate address for the POS invoice.
    - If company_doc.custom_costcenter is 1, use the Cost Center's address.
    - Otherwise, use the first available company address.
    """
    if company_doc.custom_costcenter == 1:
        if not pos_invoice_doc.cost_center:
            frappe.throw(_("No Cost Center is set in the POS invoice."))

        cost_center_doc = frappe.get_doc("Cost Center", pos_invoice_doc.cost_center)
        if cost_center_doc.custom_zatca_branch_address:
            address_list = frappe.get_all(
                "Address",
                fields=[
                    "address_line1",
                    "address_line2",
                    "custom_building_number",
                    "city",
                    "pincode",
                    "state",
                ],
                filters=[["name", "=", cost_center_doc.custom_zatca_branch_address]],
            )
            if not address_list:
                frappe.throw("ZATCA requires a proper address. Please add")
            if address_list:
                return address_list[0]

    # Fallback to company address if cost center is not used
    address_list = frappe.get_all(
        "Address",
        fields=[
            "address_line1",
            "address_line2",
            "custom_building_number",
            "city",
            "pincode",
            "state",
        ],
        filters=[
            ["is_your_company_address", "=", "1"],
            ["Dynamic Link", "link_name", "=", company_doc.name],
        ],
    )

    if not address_list:
        frappe.throw(_("require address of company"))

    # Return the first valid address from Company
    for address in address_list:
        return address


def company_data(invoice, pos_invoice_doc):
    """Function for adding company data to the POS invoice"""
    try:
        company_doc = frappe.get_doc("Company", pos_invoice_doc.company)

        # If Company requires Cost Center but it's missing, throw an error
        if company_doc.custom_costcenter == 1 and not pos_invoice_doc.cost_center:
            frappe.throw(_(" No Cost Center is set in the POS invoice.Give the feild"))

        # Determine whether to fetch data from Cost Center or Company
        if company_doc.custom_costcenter == 1:
            cost_center_doc = frappe.get_doc("Cost Center", pos_invoice_doc.cost_center)
            custom_registration_type = cost_center_doc.custom_zatca__registration_type
            custom_company_registration = (
                cost_center_doc.custom_zatca__registration_number
            )
        else:
            custom_registration_type = company_doc.custom_registration_type
            custom_company_registration = company_doc.custom_company_registration

        cac_accountingsupplierparty = ET.SubElement(
            invoice, "cac:AccountingSupplierParty"
        )
        cac_party_1 = ET.SubElement(cac_accountingsupplierparty, "cac:Party")
        cac_partyidentification = ET.SubElement(cac_party_1, "cac:PartyIdentification")
        cbc_id_2 = ET.SubElement(cac_partyidentification, "cbc:ID")
        cbc_id_2.set("schemeID", custom_registration_type)
        cbc_id_2.text = custom_company_registration

        # Get the appropriate address
        address = get_address(pos_invoice_doc, company_doc)

        cac_postaladdress = ET.SubElement(cac_party_1, "cac:PostalAddress")
        cbc_streetname = ET.SubElement(cac_postaladdress, "cbc:StreetName")
        cbc_streetname.text = address.address_line1
        cbc_buildingnumber = ET.SubElement(cac_postaladdress, "cbc:BuildingNumber")
        cbc_buildingnumber.text = address.custom_building_number
        cbc_plotidentification = ET.SubElement(
            cac_postaladdress, "cbc:PlotIdentification"
        )
        cbc_plotidentification.text = address.address_line1
        cbc_citysubdivisionname = ET.SubElement(
            cac_postaladdress, "cbc:CitySubdivisionName"
        )
        cbc_citysubdivisionname.text = address.city
        cbc_cityname = ET.SubElement(cac_postaladdress, "cbc:CityName")
        cbc_cityname.text = address.city
        cbc_postalzone = ET.SubElement(cac_postaladdress, "cbc:PostalZone")
        cbc_postalzone.text = address.pincode
        cbc_countrysubentity = ET.SubElement(cac_postaladdress, "cbc:CountrySubentity")
        cbc_countrysubentity.text = address.state

        cac_country = ET.SubElement(cac_postaladdress, "cac:Country")
        cbc_identificationcode = ET.SubElement(cac_country, "cbc:IdentificationCode")
        cbc_identificationcode.text = "SA"

        cac_partytaxscheme = ET.SubElement(cac_party_1, "cac:PartyTaxScheme")
        cbc_companyid = ET.SubElement(cac_partytaxscheme, "cbc:CompanyID")
        cbc_companyid.text = company_doc.tax_id

        cac_taxscheme = ET.SubElement(cac_partytaxscheme, "cac:TaxScheme")
        cbc_id_3 = ET.SubElement(cac_taxscheme, "cbc:ID")
        cbc_id_3.text = "VAT"

        cac_partylegalentity = ET.SubElement(cac_party_1, "cac:PartyLegalEntity")
        cbc_registrationname = ET.SubElement(
            cac_partylegalentity, "cbc:RegistrationName"
        )
        cbc_registrationname.text = pos_invoice_doc.company

        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred in company data: {e}"))
        return None


def customer_data(invoice, pos_invoice_doc):
    """function for customer data"""
    try:
        customer_doc = frappe.get_doc("Customer", pos_invoice_doc.customer)
        # frappe.throw(str(customer_doc))
        cac_accountingcustomerparty = ET.SubElement(
            invoice, "cac:AccountingCustomerParty"
        )
        cac_party_2 = ET.SubElement(cac_accountingcustomerparty, "cac:Party")
        cac_partyidentification_1 = ET.SubElement(
            cac_party_2, "cac:PartyIdentification"
        )
        cbc_id_4 = ET.SubElement(cac_partyidentification_1, "cbc:ID")
        cbc_id_4.set("schemeID", "CRN")
        cbc_id_4.text = customer_doc.tax_id
        # frappe.throw(f"Customer Tax ID set to: {cbc_ID_4.text}")
        if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
            address = frappe.get_doc("Address", pos_invoice_doc.customer_address)
        else:
            address = frappe.get_doc("Address", customer_doc.customer_primary_address)
        cac_postaladdress_1 = ET.SubElement(cac_party_2, "cac:PostalAddress")
        cbc_streetname_1 = ET.SubElement(cac_postaladdress_1, "cbc:StreetName")
        cbc_streetname_1.text = address.address_line1
        cbc_buildingnumber_1 = ET.SubElement(cac_postaladdress_1, "cbc:BuildingNumber")
        cbc_buildingnumber_1.text = address.custom_building_number
        cbc_plotidentification_1 = ET.SubElement(
            cac_postaladdress_1, "cbc:PlotIdentification"
        )
        if hasattr(address, "po_box"):
            cbc_plotidentification_1.text = address.po_box
        else:
            cbc_plotidentification_1.text = address.address_line1
        cbc_citysubdivisionname_1 = ET.SubElement(
            cac_postaladdress_1, "cbc:CitySubdivisionName"
        )
        cbc_citysubdivisionname_1.text = address.address_line2
        cbc_cityname_1 = ET.SubElement(cac_postaladdress_1, "cbc:CityName")
        cbc_cityname_1.text = address.city
        cbc_postalzone_1 = ET.SubElement(cac_postaladdress_1, "cbc:PostalZone")
        cbc_postalzone_1.text = address.pincode
        cbc_countrysubentity_1 = ET.SubElement(
            cac_postaladdress_1, "cbc:CountrySubentity"
        )
        cbc_countrysubentity_1.text = address.state
        cac_country_1 = ET.SubElement(cac_postaladdress_1, "cac:Country")
        cbc_identificationcode_1 = ET.SubElement(
            cac_country_1, "cbc:IdentificationCode"
        )
        cbc_identificationcode_1.text = "SA"
        # cac_partytaxscheme_1 = ET.SubElement(cac_party_2, "cac:PartyTaxScheme")
        # if address.country == "Saudi Arabia":
        #     cbc_company_id = ET.SubElement(cac_partytaxscheme_1, "cbc:CompanyID")
        #     cbc_company_id.text = customer_doc.tax_id
        cac_partytaxscheme_1 = ET.SubElement(cac_party_2, "cac:PartyTaxScheme")
        cac_taxscheme_1 = ET.SubElement(cac_partytaxscheme_1, "cac:TaxScheme")
        cbc_id_5 = ET.SubElement(cac_taxscheme_1, "cbc:ID")
        cbc_id_5.text = "VAT"
        cac_partylegalentity_1 = ET.SubElement(cac_party_2, "cac:PartyLegalEntity")
        cbc_registrationname_1 = ET.SubElement(
            cac_partylegalentity_1, "cbc:RegistrationName"
        )
        cbc_registrationname_1.text = customer_doc.customer_name
        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred in company data: {e}"))
        return None


def delivery_and_paymentmeans(invoice, pos_invoice_doc, is_return):
    """Function for delivey and paymentmens"""
    try:
        cac_delivery = ET.SubElement(invoice, "cac:Delivery")
        cbc_actualdeliverydate = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
        cbc_actualdeliverydate.text = str(pos_invoice_doc.due_date)
        cac_paymentmeans = ET.SubElement(invoice, "cac:PaymentMeans")
        cbc_paymentmeanscode = ET.SubElement(cac_paymentmeans, "cbc:PaymentMeansCode")
        cbc_paymentmeanscode.text = "30"

        if is_return == 1:
            cbc_instructionnote = ET.SubElement(cac_paymentmeans, "cbc:InstructionNote")
            cbc_instructionnote.text = "Cancellation"
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Delivery and payment means failed: {e}"))
        return None  # Ensures all return paths explicitly return a value


def delivery_and_paymentmeans_for_compliance(invoice, pos_invoice_doc, compliance_type):
    """function for delivery and paymentmens for compliance"""
    try:
        cac_delivery = ET.SubElement(invoice, "cac:Delivery")
        cbc_actualdeliverydate = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
        cbc_actualdeliverydate.text = str(pos_invoice_doc.due_date)
        cac_paymentmeans = ET.SubElement(invoice, "cac:PaymentMeans")
        cbc_paymentmeanscode = ET.SubElement(cac_paymentmeans, "cbc:PaymentMeansCode")
        cbc_paymentmeanscode.text = "30"

        if compliance_type in {"3", "4", "5", "6"}:
            cbc_instructionnote = ET.SubElement(cac_paymentmeans, "cbc:InstructionNote")
            cbc_instructionnote.text = "Cancellation"
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Delivery and payment means failed: {e}"))
        return None  # Ensures all return paths explicitly return a value


def add_document_level_discount_with_tax(invoice, pos_invoice_doc):
    """function for add document level discount"""
    try:
        # Create the AllowanceCharge element
        cac_allowancecharge = ET.SubElement(invoice, "cac:AllowanceCharge")

        # ChargeIndicator
        cbc_chargeindicator = ET.SubElement(cac_allowancecharge, "cbc:ChargeIndicator")
        cbc_chargeindicator.text = "false"  # Indicates a discount

        # AllowanceChargeReason
        cbc_allowancechargereason = ET.SubElement(
            cac_allowancecharge, "cbc:AllowanceChargeReason"
        )
        cbc_allowancechargereason.text = "Discount"

        # Assuming this is within your add_document_level_discount_with_tax function
        cbc_amount = ET.SubElement(
            cac_allowancecharge, "cbc:Amount", currencyID=pos_invoice_doc.currency
        )
        base_discount_amount = pos_invoice_doc.get("discount_amount", 0.0)
        cbc_amount.text = f"{base_discount_amount:.2f}"

        # Tax Category Section
        cac_taxcategory = ET.SubElement(cac_allowancecharge, "cac:TaxCategory")
        cbc_id = ET.SubElement(cac_taxcategory, "cbc:ID")

        # Determine the VAT category code from the sales_invoice_doc
        if pos_invoice_doc.custom_zatca_tax_category == "Standard":
            cbc_id.text = "S"
        elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
            cbc_id.text = "Z"
        elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
            cbc_id.text = "E"
        elif (
            pos_invoice_doc.custom_zatca_tax_category
            == "Services outside scope of tax / Not subject to VAT"
        ):
            cbc_id.text = "O"
        # Retrieve the VAT percentage from the first tax entry in the sales_invoice_doc
        cbc_percent = ET.SubElement(cac_taxcategory, "cbc:Percent")

        cbc_percent.text = f"{float(pos_invoice_doc.taxes[0].rate):.2f}"

        cac_taxscheme = ET.SubElement(cac_taxcategory, "cac:TaxScheme")
        cbc_taxschemeid = ET.SubElement(cac_taxscheme, "cbc:ID")
        cbc_taxschemeid.text = "VAT"
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(
            _(
                f"Error occurred while processing allowance charge data without template: {e}"
            )
        )
        return None


def add_document_level_discount_with_tax_template(invoice, pos_invoice_doc):
    """add document level discount"""
    try:
        # Create the AllowanceCharge element
        cac_allowancecharge = ET.SubElement(invoice, "cac:AllowanceCharge")
        # ChargeIndicator
        cbc_chargeindicator = ET.SubElement(cac_allowancecharge, "cbc:ChargeIndicator")
        cbc_chargeindicator.text = "false"  # Indicates a discount
        # AllowanceChargeReason
        cbc_allowancechargereason = ET.SubElement(
            cac_allowancecharge, "cbc:AllowanceChargeReason"
        )
        cbc_allowancechargereason.text = "Discount"
        # Discount Amount
        cbc_amount = ET.SubElement(
            cac_allowancecharge, "cbc:Amount", currencyID=pos_invoice_doc.currency
        )
        base_discount_amount = pos_invoice_doc.get("discount_amount", 0.0)
        cbc_amount.text = f"{base_discount_amount:.2f}"
        # Tax Category Section
        cac_taxcategory = ET.SubElement(cac_allowancecharge, "cac:TaxCategory")
        cbc_id = ET.SubElement(cac_taxcategory, "cbc:ID")
        # Retrieve the VAT category code from the first applicable tax template in the items
        vat_category = "Standard"
        tax_percentage = 0.0
        for item in pos_invoice_doc.items:
            item_tax_template = frappe.get_doc(
                "Item Tax Template", item.item_tax_template
            )
            vat_category = item_tax_template.custom_zatca_tax_category
            tax_percentage = (
                item_tax_template.taxes[0].tax_rate if item_tax_template.taxes else 15
            )
            break  # Assuming that all items will have the same tax category and percentage
        # Set VAT category code in the XML
        if vat_category == "Standard":
            cbc_id.text = "S"
        elif vat_category == "Zero Rated":
            cbc_id.text = "Z"
        elif vat_category == "Exempted":
            cbc_id.text = "E"
        elif vat_category == "Services outside scope of tax / Not subject to VAT":
            cbc_id.text = "O"
        else:
            frappe.throw(
                "Invalid VAT category code. Must be one of 'Standard', 'Zero Rated', 'Exempted', "
                "or 'Services outside scope of tax / Not subject to VAT'."
            )

        cbc_percent = ET.SubElement(cac_taxcategory, "cbc:Percent")
        cbc_percent.text = f"{tax_percentage:.2f}"
        cac_taxscheme = ET.SubElement(cac_taxcategory, "cac:TaxScheme")
        cbc_taxschemeid = ET.SubElement(cac_taxscheme, "cbc:ID")
        cbc_taxschemeid.text = "VAT"
        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred while processing allowance charge data: {e}"))
        return None


def add_line_item_discount(cac_price, single_item, pos_invoice_doc):
    """adding line item discount"""
    cac_allowancecharge = ET.SubElement(cac_price, "cac:AllowanceCharge")

    cbc_chargeindicator = ET.SubElement(cac_allowancecharge, "cbc:ChargeIndicator")
    cbc_chargeindicator.text = "false"  # Indicates a discount

    cbc_allowancechargereason = ET.SubElement(
        cac_allowancecharge, "cbc:AllowanceChargeReason"
    )
    cbc_allowancechargereason.text = "discount"

    cbc_amount = ET.SubElement(
        cac_allowancecharge, "cbc:Amount", currencyID=pos_invoice_doc.currency
    )
    cbc_amount.text = str(abs(single_item.discount_amount))

    cbc_baseamount = ET.SubElement(
        cac_allowancecharge, "cbc:BaseAmount", currencyID=pos_invoice_doc.currency
    )
    cbc_baseamount.text = str(abs(single_item.price_list_rate))

    return cac_price


def billing_reference_for_credit_and_debit_note(invoice, pos_invoice_doc):
    """function for billing reference for credit and debit note"""
    try:
        # details of original invoice
        cac_billingreference = ET.SubElement(invoice, "cac:BillingReference")
        cac_invoicedocumentreference = ET.SubElement(
            cac_billingreference, "cac:InvoiceDocumentReference"
        )
        cbc_id13 = ET.SubElement(cac_invoicedocumentreference, "cbc:ID")
        cbc_id13.text = (
            pos_invoice_doc.return_against
        )  # field from return against invoice.

        return invoice
    except (ValueError, KeyError, AttributeError) as error:
        frappe.throw(
            _(
                f"Error occurred while adding billing reference for credit/debit note: {str(error)}"
            )
        )
        return None


def get_exemption_reason_map():
    """Mapping of the exception reason code accoding to the reason code"""
    return {
        "VATEX-SA-29": (
            "Financial services mentioned in Article 29 of the VAT Regulations."
        ),
        "VATEX-SA-29-7": (
            "Life insurance services mentioned in Article 29 of the VAT Regulations."
        ),
        "VATEX-SA-30": (
            "Real estate transactions mentioned in Article 30 of the VAT Regulations."
        ),
        "VATEX-SA-32": "Export of goods.",
        "VATEX-SA-33": "Export of services.",
        "VATEX-SA-34-1": "The international transport of Goods.",
        "VATEX-SA-34-2": "International transport of passengers.",
        "VATEX-SA-34-3": (
            "Services directly connected and incidental to a Supply of "
            "international passenger transport."
        ),
        "VATEX-SA-34-4": "Supply of a qualifying means of transport.",
        "VATEX-SA-34-5": (
            "Any services relating to Goods or passenger transportation, as defined "
            "in article twenty five of these Regulations."
        ),
        "VATEX-SA-35": "Medicines and medical equipment.",
        "VATEX-SA-36": "Qualifying metals.",
        "VATEX-SA-EDU": "Private education to citizen.",
        "VATEX-SA-HEA": "Private healthcare to citizen.",
        "VATEX-SA-MLTRY": "Supply of qualified military goods",
        "VATEX-SA-OOS": (
            "The reason is a free text, has to be provided by the taxpayer on a "
            "case-by-case basis."
        ),
    }


def get_tax_total_from_items(pos_invoice_doc):
    """function for get tax total from items"""
    try:
        total_tax = 0
        for single_item in pos_invoice_doc.items:
            # _ = item_tax_amount
            _item_tax_amount, tax_percent = get_tax_for_item(
                pos_invoice_doc.taxes[0].item_wise_tax_detail, single_item.item_code
            )
            total_tax = total_tax + (single_item.net_amount * (tax_percent / 100))
        return total_tax
    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(_(f"Data processing error in tax data: {str(e)}"))


def tax_data(invoice, pos_invoice_doc):
    """Function for tax data"""
    try:
        pos_profile = pos_invoice_doc.pos_profile
        if not pos_profile:
            frappe.throw(_("POS Profile is not set in the POS Invoice."))
        pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
        taxes_and_charges = pos_profile_doc.taxes_and_charges

        taxes_template_doc = frappe.get_doc(
            "Sales Taxes and Charges Template", taxes_and_charges
        )

        tax_rate = taxes_template_doc.taxes[0]

        # Handle SAR-specific logic
        if pos_invoice_doc.currency == "SAR":
            cac_taxtotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_taxamount_sar = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_sar.set(
                "currencyID", "SAR"
            )  # ZATCA requires tax amount in SAR
            tax_amount_without_retention_sar = round(
                abs(get_tax_total_from_items(pos_invoice_doc)), 2
            )
            cbc_taxamount_sar.text = str(
                tax_amount_without_retention_sar
            )  # Tax amount in SAR

            if tax_rate.included_in_print_rate == 0:
                taxable_amount = pos_invoice_doc.base_total - pos_invoice_doc.get(
                    "base_discount_amount", 0.0
                )
            else:
                taxable_amount = pos_invoice_doc.base_net_total - pos_invoice_doc.get(
                    "base_discount_amount", 0.0
                )

            cac_taxtotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_taxamount = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount.set("currencyID", pos_invoice_doc.currency)
            tax_amount_without_retention = round(
                abs(get_tax_total_from_items(pos_invoice_doc)), 2
            )

            tax_amount_without_retention = (
                taxable_amount * float(pos_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount.text = f"{abs(round(tax_amount_without_retention, 2)):.2f}"
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, "cac:TaxSubtotal")
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, "cbc:TaxableAmount")
            cbc_taxableamount.set("currencyID", pos_invoice_doc.currency)
            if tax_rate.included_in_print_rate == 0:
                taxable_amount = pos_invoice_doc.base_total - pos_invoice_doc.get(
                    "base_discount_amount", 0.0
                )
            else:
                taxable_amount = pos_invoice_doc.base_net_total - pos_invoice_doc.get(
                    "base_discount_amount", 0.0
                )
            cbc_taxableamount.text = str(abs(round(taxable_amount, 2)))

            # tax_rate = float(pos_invoice_doc.taxes[0].rate)
            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
            cbc_taxamount_2.set("currencyID", pos_invoice_doc.currency)
            cbc_taxamount_2.text = str(
                abs(
                    round(
                        taxable_amount * float(pos_invoice_doc.taxes[0].rate) / 100, 2
                    )
                )
            )
        # Handle USD-specific logic
        else:
            cac_taxtotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_taxamount_usd_1 = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_usd_1.set(
                "currencyID", pos_invoice_doc.currency
            )  # USD currency
            if tax_rate.included_in_print_rate == 0:
                taxable_amount_1 = pos_invoice_doc.total - pos_invoice_doc.get(
                    "discount_amount", 0.0
                )
            else:
                taxable_amount_1 = pos_invoice_doc.net_total - pos_invoice_doc.get(
                    "discount_amount", 0.0
                )

            tax_amount_without_retention = (
                taxable_amount_1 * float(pos_invoice_doc.taxes[0].rate) / 100
            )

            cbc_taxamount_usd_1.text = str(round(tax_amount_without_retention, 2))
            cac_taxtotal = ET.SubElement(invoice, "cac:TaxTotal")
            cbc_taxamount_usd = ET.SubElement(cac_taxtotal, "cbc:TaxAmount")
            cbc_taxamount_usd.set(
                "currencyID", pos_invoice_doc.currency
            )  # USD currency
            if tax_rate.included_in_print_rate == 0:
                taxable_amount_1 = pos_invoice_doc.total - pos_invoice_doc.get(
                    "discount_amount", 0.0
                )
            else:
                taxable_amount_1 = pos_invoice_doc.net_total - pos_invoice_doc.get(
                    "discount_amount", 0.0
                )
            # tax_rate = float(pos_invoice_doc.taxes[0].rate)
            tax_amount_without_retention = (
                taxable_amount_1 * float(pos_invoice_doc.taxes[0].rate) / 100
            )
            cbc_taxamount_usd.text = str(round(tax_amount_without_retention, 2))

            # Tax Subtotal
            cac_taxsubtotal = ET.SubElement(cac_taxtotal, "cac:TaxSubtotal")
            cbc_taxableamount = ET.SubElement(cac_taxsubtotal, "cbc:TaxableAmount")
            cbc_taxableamount.set("currencyID", pos_invoice_doc.currency)
            cbc_taxableamount.text = str(abs(round(taxable_amount_1, 2)))

            cbc_taxamount_2 = ET.SubElement(cac_taxsubtotal, "cbc:TaxAmount")
            cbc_taxamount_2.set("currencyID", pos_invoice_doc.currency)
            cbc_taxamount_2.text = str(
                abs(
                    round(
                        taxable_amount_1 * float(pos_invoice_doc.taxes[0].rate) / 100, 2
                    )
                )
            )
        # Tax Category and Scheme
        cac_taxcategory_1 = ET.SubElement(cac_taxsubtotal, "cac:TaxCategory")
        cbc_id_8 = ET.SubElement(cac_taxcategory_1, "cbc:ID")

        if pos_invoice_doc.custom_zatca_tax_category == "Standard":
            cbc_id_8.text = "S"
        elif pos_invoice_doc.custom_zatca_tax_category == "Zero Rated":
            cbc_id_8.text = "Z"
        elif pos_invoice_doc.custom_zatca_tax_category == "Exempted":
            cbc_id_8.text = "E"
        elif (
            pos_invoice_doc.custom_zatca_tax_category
            == "Services outside scope of tax / Not subject to VAT"
        ):
            cbc_id_8.text = "O"

        cbc_percent_1 = ET.SubElement(cac_taxcategory_1, "cbc:Percent")
        cbc_percent_1.text = f"{float(pos_invoice_doc.taxes[0].rate):.2f}"

        # Exemption Reason (if applicable)
        exemption_reason_map = get_exemption_reason_map()
        if pos_invoice_doc.custom_zatca_tax_category != "Standard":
            cbc_taxexemptionreasoncode = ET.SubElement(
                cac_taxcategory_1, "cbc:TaxExemptionReasonCode"
            )
            cbc_taxexemptionreasoncode.text = (
                pos_invoice_doc.custom_exemption_reason_code
            )
            cbc_taxexemptionreason = ET.SubElement(
                cac_taxcategory_1, "cbc:TaxExemptionReason"
            )
            reason_code = pos_invoice_doc.custom_exemption_reason_code
            if reason_code in exemption_reason_map:
                cbc_taxexemptionreason.text = exemption_reason_map[reason_code]

        # Tax Scheme
        cac_taxscheme_3 = ET.SubElement(cac_taxcategory_1, "cac:TaxScheme")
        cbc_id_9 = ET.SubElement(cac_taxscheme_3, "cbc:ID")
        cbc_id_9.text = "VAT"

        # Legal Monetary Total (adjust for both SAR and USD)
        cac_legalmonetarytotal = ET.SubElement(invoice, "cac:LegalMonetaryTotal")
        cbc_lineextensionamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:LineExtensionAmount"
        )
        cbc_lineextensionamount.set("currencyID", pos_invoice_doc.currency)
        if tax_rate.included_in_print_rate == 0:
            cbc_lineextensionamount.text = str(round(abs(pos_invoice_doc.total), 2))
        else:
            cbc_lineextensionamount.text = str(round(abs(pos_invoice_doc.net_total), 2))
        cbc_taxexclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxExclusiveAmount"
        )
        cbc_taxexclusiveamount.set("currencyID", pos_invoice_doc.currency)
        if tax_rate.included_in_print_rate == 0:
            cbc_taxexclusiveamount.text = str(
                round(
                    abs(
                        pos_invoice_doc.total
                        - pos_invoice_doc.get("discount_amount", 0.0)
                    ),
                    2,
                )
            )
        else:
            cbc_taxexclusiveamount.text = str(
                round(
                    abs(
                        pos_invoice_doc.net_total
                        - pos_invoice_doc.get("discount_amount", 0.0)
                    ),
                    2,
                )
            )

        cbc_taxinclusiveamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:TaxInclusiveAmount"
        )
        cbc_taxinclusiveamount.set("currencyID", pos_invoice_doc.currency)
        if tax_rate.included_in_print_rate == 0:
            cbc_taxinclusiveamount.text = "{:.2f}".format(
                round(
                    abs(
                        pos_invoice_doc.total
                        - pos_invoice_doc.get("discount_amount", 0.0)
                    )
                    + abs(tax_amount_without_retention),
                    2,
                )
            )
        else:
            cbc_taxinclusiveamount.text = "{:.2f}".format(
                round(
                    abs(
                        pos_invoice_doc.net_total
                        - pos_invoice_doc.get("discount_amount", 0.0)
                    )
                    + abs(tax_amount_without_retention),
                    2,
                )
            )

        cbc_allowancetotalamount = ET.SubElement(
            cac_legalmonetarytotal, "cbc:AllowanceTotalAmount"
        )
        cbc_allowancetotalamount.set("currencyID", pos_invoice_doc.currency)
        cbc_allowancetotalamount.text = str(
            abs(pos_invoice_doc.get("discount_amount", 0.0))
        )

        cbc_payableamount = ET.SubElement(cac_legalmonetarytotal, "cbc:PayableAmount")
        cbc_payableamount.set("currencyID", pos_invoice_doc.currency)
        if tax_rate.included_in_print_rate == 0:
            cbc_payableamount.text = "{:.2f}".format(
                round(
                    abs(
                        pos_invoice_doc.total
                        - pos_invoice_doc.get("discount_amount", 0.0)
                    )
                    + abs(tax_amount_without_retention),
                    2,
                )
            )
        else:
            cbc_payableamount.text = "{:.2f}".format(
                round(
                    abs(
                        pos_invoice_doc.net_total
                        - pos_invoice_doc.get("discount_amount", 0.0)
                    )
                    + abs(tax_amount_without_retention),
                    2,
                )
            )
        return invoice

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        frappe.throw(_(f"Data processing error in tax data: {str(e)}"))
