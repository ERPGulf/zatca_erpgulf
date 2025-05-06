"""
This module contains utilities for ZATCA 2024 e-invoicing.
Includes functions for XML parsing, API interactions, and custom handling.
"""

import re
import uuid
import xml.etree.ElementTree as ET
from frappe import _
import frappe
from frappe.utils.data import get_time
from zatca_erpgulf.zatca_erpgulf.country_code import country_code_mapping

CBC_ID = "cbc:ID"
DS_TRANSFORM = "ds:Transform"


def get_icv_code(invoice_number):
    """
    Extracts the numeric part from the invoice number to generate the ICV code.
    """
    try:
        icv_code = re.sub(
            r"\D", "", invoice_number
        )  # taking the number part only  from doc name
        return icv_code
    except TypeError as e:
        frappe.throw(_("Type error in getting ICV number: " + str(e)))
        return None
    except re.error as e:
        frappe.throw(_("Regex error in getting ICV number: " + str(e)))
        return None


def get_issue_time(invoice_number):
    """
    Extracts and formats the posting time of a Sales Invoice as HH:MM:SS.
    """
    doc = frappe.get_doc("Sales Invoice", invoice_number)
    time = get_time(doc.posting_time)
    issue_time = time.strftime("%H:%M:%S")  # time in format of  hour,mints,secnds
    return issue_time


def billing_reference_for_credit_and_debit_note(invoice, sales_invoice_doc):
    """
    Adds billing reference details for credit and debit notes to the invoice XML.
    """
    try:
        # details of original invoice
        cac_billingreference = ET.SubElement(invoice, "cac:BillingReference")
        cac_invoicedocumentreference = ET.SubElement(
            cac_billingreference, "cac:InvoiceDocumentReference"
        )
        cbc_id13 = ET.SubElement(cac_invoicedocumentreference, CBC_ID)
        cbc_id13.text = (
            sales_invoice_doc.return_against
        )  # field from return against invoice.

        return invoice
    except (ValueError, KeyError, AttributeError) as error:
        frappe.throw(
            _(
                f"Error occurred while adding billing reference for credit/debit note: {str(error)}"
            )
        )
        return None


def xml_tags():
    """
    Creates an XML Invoice document with UBL, XAdES, and digital signature elements.
    """
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
        invoice_id = ET.SubElement(signature_information, CBC_ID)
        invoice_id.text = "urn:oasis:names:specification:ubl:signature:1"
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
        transform = ET.SubElement(transforms, DS_TRANSFORM)
        transform.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
        xpath = ET.SubElement(transform, "ds:XPath")
        xpath.text = "not(//ancestor-or-self::ext:UBLExtensions)"
        transform2 = ET.SubElement(transforms, DS_TRANSFORM)
        transform2.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
        xpath2 = ET.SubElement(transform2, "ds:XPath")
        xpath2.text = "not(//ancestor-or-self::cac:Signature)"
        transform3 = ET.SubElement(transforms, DS_TRANSFORM)
        transform3.set("Algorithm", "http://www.w3.org/TR/1999/REC-xpath-19991116")
        xpath3 = ET.SubElement(transform3, "ds:XPath")
        xpath3.text = (
            "not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])"
        )
        transform4 = ET.SubElement(transforms, DS_TRANSFORM)
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
        digest_value1.text = "YjQwZmEyMjM2NDU1YjQwNjM5MTFmYmVkO="
        signature_value = ET.SubElement(signature, "ds:SignatureValue")
        signature_value.text = "MEQCIDGBRHiPo6yhXIQ9df6pMEkufcGnoqYaS+O8Jn"
        keyinfo = ET.SubElement(signature, "ds:KeyInfo")
        x509data = ET.SubElement(keyinfo, "ds:X509Data")
        x509certificate = ET.SubElement(x509data, "ds:X509Certificate")
        x509certificate.text = (
            "MIID6TCCA5CgAwIBAgITbwAAf8tem6jngr16DwABAAB/yzAKBggqhkjOPQQ"
        )
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
        digest_value2.text = "YTJkM2JhYTcwZTBhZTAxOGYwODMyNzY3"
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
    """
    Populates the Sales Invoice XML with key elements and metadata.
    """
    try:
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)

        cbc_profile_id = ET.SubElement(invoice, "cbc:ProfileID")
        cbc_profile_id.text = "reporting:1.0"

        cbc_id = ET.SubElement(invoice, CBC_ID)
        cbc_id.text = str(sales_invoice_doc.name)

        cbc_uuid = ET.SubElement(invoice, "cbc:UUID")
        cbc_uuid.text = str(uuid.uuid1())
        uuid1 = cbc_uuid.text

        cbc_issue_date = ET.SubElement(invoice, "cbc:IssueDate")
        cbc_issue_date.text = str(sales_invoice_doc.posting_date)

        cbc_issue_time = ET.SubElement(invoice, "cbc:IssueTime")
        cbc_issue_time.text = get_issue_time(invoice_number)

        return invoice, uuid1, sales_invoice_doc
    except (AttributeError, ValueError, frappe.ValidationError) as e:
        frappe.throw(_(("Error occurred in SalesInvoice data: " f"{str(e)}")))
        return None


def invoice_typecode_compliance(invoice, compliance_type):
    """
    Creates and populates XML tags for a UBL Invoice document.
    """

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


def invoice_typecode_simplified(invoice, sales_invoice_doc):
    """
    Sets the InvoiceTypeCode for a simplified invoice based on sales invoice document attributes.
    """
    try:
        cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
        base_code = "02"
        checkbox_map = [
            sales_invoice_doc.custom_zatca_third_party_invoice,
            sales_invoice_doc.custom_zatca_nominal_invoice,
            sales_invoice_doc.custom_zatca_export_invoice,
            sales_invoice_doc.custom_summary_invoice,
            sales_invoice_doc.custom_self_billed_invoice,
        ]
        five_digit_code = "".join("1" if checkbox else "0" for checkbox in checkbox_map)
        final_code = base_code + five_digit_code
        if sales_invoice_doc.is_return == 0:
            cbc_invoicetypecode.set("name", final_code)
            cbc_invoicetypecode.text = "388"
        elif sales_invoice_doc.is_return == 1:
            cbc_invoicetypecode.set("name", final_code)
            cbc_invoicetypecode.text = "381"

        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error occurred in simplified invoice typecode: {e}"))
        return None


def invoice_typecode_standard(invoice, sales_invoice_doc):
    """
    Sets the InvoiceTypeCode for a standard invoice based on sales invoice document attributes.
    """
    try:
        cbc_invoicetypecode = ET.SubElement(invoice, "cbc:InvoiceTypeCode")
        base_code = "01"
        checkbox_map = [
            sales_invoice_doc.custom_zatca_third_party_invoice,
            sales_invoice_doc.custom_zatca_nominal_invoice,
            sales_invoice_doc.custom_zatca_export_invoice,
            sales_invoice_doc.custom_summary_invoice,
            sales_invoice_doc.custom_self_billed_invoice,
        ]

        five_digit_code = "".join("1" if checkbox else "0" for checkbox in checkbox_map)
        final_code = base_code + five_digit_code
        if sales_invoice_doc.is_return == 0:
            cbc_invoicetypecode.set("name", final_code)
            cbc_invoicetypecode.text = "388"
        elif sales_invoice_doc.is_return == 1:
            cbc_invoicetypecode.set("name", final_code)
            cbc_invoicetypecode.text = "381"
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error in standard invoice type code: {e}"))
        return None


def doc_reference(invoice, sales_invoice_doc, invoice_number):
    """
    Adds document reference elements to the XML invoice,
    including currency codes and additional document references.
    """
    try:
        cbc_documentcurrencycode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
        cbc_documentcurrencycode.text = sales_invoice_doc.currency
        cbc_taxcurrencycode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
        cbc_taxcurrencycode.text = "SAR"  # SAR is as zatca requires tax amount in SAR
        if sales_invoice_doc.is_return == 1:
            invoice = billing_reference_for_credit_and_debit_note(
                invoice, sales_invoice_doc
            )
        cac_additionaldocumentreference = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1 = ET.SubElement(cac_additionaldocumentreference, CBC_ID)
        cbc_id_1.text = "ICV"
        cbc_uuid_1 = ET.SubElement(cac_additionaldocumentreference, "cbc:UUID")
        cbc_uuid_1.text = str(get_icv_code(invoice_number))
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error occurred in reference doc: {e}"))
        return None


def doc_reference_compliance(
    invoice, sales_invoice_doc, invoice_number, compliance_type
):
    """
    Adds document reference elements to the XML invoice, including currency codes,
    billing references,and additional document references.
    """
    try:
        cbc_documentcurrencycode = ET.SubElement(invoice, "cbc:DocumentCurrencyCode")
        cbc_documentcurrencycode.text = sales_invoice_doc.currency
        cbc_taxcurrencycode = ET.SubElement(invoice, "cbc:TaxCurrencyCode")
        cbc_taxcurrencycode.text = sales_invoice_doc.currency

        if compliance_type in {"3", "4", "5", "6"}:
            cac_billingreference = ET.SubElement(invoice, "cac:BillingReference")
            cac_invoicedocumentreference = ET.SubElement(
                cac_billingreference, "cac:InvoiceDocumentReference"
            )
            cbc_id13 = ET.SubElement(cac_invoicedocumentreference, CBC_ID)
            cbc_id13.text = "6666666"  # field from return against invoice.

        cac_additionaldocumentreference = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1 = ET.SubElement(cac_additionaldocumentreference, CBC_ID)
        cbc_id_1.text = "ICV"
        cbc_uuid_1 = ET.SubElement(cac_additionaldocumentreference, "cbc:UUID")
        cbc_uuid_1.text = str(get_icv_code(invoice_number))
        return invoice
    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Error occurred in reference doc: {e}"))
        return None


def get_pih_for_company(pih_data, company_name):
    """
    Retrieves the PIH for a specific company from the provided data.
    """
    try:
        for entry in pih_data.get("data", []):
            if entry.get("company") == company_name:
                return entry.get("pih")

        frappe.throw(
            _(f"Error while retrieving PIH of company '{company_name}' for production.")
        )
        return None  # Ensures consistent return
    except (KeyError, AttributeError, ValueError) as e:
        frappe.throw(
            _(f"Error in getting PIH of company '{company_name}' for production: {e}")
        )
        return None  # Ensures consistent return


def additional_reference(invoice, company_abbr, sales_invoice_doc):
    """
    Adds additional document references to the XML invoice for PIH, QR, and Signature elements.
    """
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(_(f"Company with abbreviation {company_abbr} not found."))

        company_doc = frappe.get_doc("Company", company_name)

        # Create the first AdditionalDocumentReference element for PIH
        cac_additionaldocumentreference2 = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1_1 = ET.SubElement(cac_additionaldocumentreference2, CBC_ID)
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
        if sales_invoice_doc.custom_zatca_pos_name:
            zatca_settings = frappe.get_doc(
                "Zatca Multiple Setting", sales_invoice_doc.custom_zatca_pos_name
            )
            pih = zatca_settings.custom_pih
        else:
            pih = company_doc.custom_pih
        cbc_embeddeddocumentbinaryobject.text = pih

        # Create the second AdditionalDocumentReference element for QR
        cac_additionaldocumentreference22 = ET.SubElement(
            invoice, "cac:AdditionalDocumentReference"
        )
        cbc_id_1_12 = ET.SubElement(cac_additionaldocumentreference22, CBC_ID)
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
        cac_sign = ET.SubElement(invoice, "cac:Signature")
        cbc_id_sign = ET.SubElement(cac_sign, CBC_ID)
        cbc_method_sign = ET.SubElement(cac_sign, "cbc:SignatureMethod")
        cbc_id_sign.text = "urn:oasis:names:specification:ubl:signature:Invoice"
        cbc_method_sign.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"

        return invoice

    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred in additional references: {e}"))
        return None


def get_address(sales_invoice_doc, company_doc):
    """
    Fetches the appropriate address for the invoice.
    - If company_doc.custom_costcenter is 1, use the Cost Center's address.
    - If a cost center is selected but has no address, an error is raised.
    - Otherwise, use the first available company address.
    """
    if company_doc.custom_costcenter == 1 and sales_invoice_doc.cost_center:
        cost_center_doc = frappe.get_doc("Cost Center", sales_invoice_doc.cost_center)

        # Ensure the Cost Center has a linked address
        if not cost_center_doc.custom_zatca_branch_address:
            frappe.throw(_(
                f"No address is set for the selected Cost Center: {cost_center_doc.name}. Please add an address."
            ))

        address_list = frappe.get_all(
            "Address",
            fields=[
                "address_line1",
                "address_line2",
                "custom_building_number",
                "city",
                "pincode",
                "state",
                "country",
            ],
            filters={"name": cost_center_doc.custom_zatca_branch_address},
        )

        if not address_list:
            frappe.throw(
                f"ZATCA requires a proper address. Please add an address for Cost Center: {cost_center_doc.name}."
            )

        return address_list[0]  # Return the Cost Center's address

    # Fetch Company address only if no cost center is used
    address_list = frappe.get_all(
        "Address",
        fields=[
            "address_line1",
            "address_line2",
            "custom_building_number",
            "city",
            "pincode",
            "state",
            "country",
        ],
        filters={"is_your_company_address": 1},
    )

    if not address_list:
        frappe.throw(_("requires a proper company address. Please add an address"))

    for address in address_list:
        return address


def company_data(invoice, sales_invoice_doc):
    """
    Adds company data elements to the XML invoice, including supplier details, address,
    and tax information.
    """
    try:
        company_doc = frappe.get_doc("Company", sales_invoice_doc.company)
        if company_doc.custom_costcenter == 1 and not sales_invoice_doc.cost_center:
            frappe.throw(_("no Cost Center is set in the invoice.Give the feild"))
        # Determine whether to fetch data from Cost Center or Company
        if company_doc.custom_costcenter == 1 and sales_invoice_doc.cost_center:
            cost_center_doc = frappe.get_doc(
                "Cost Center", sales_invoice_doc.cost_center
            )
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
        cbc_id_2 = ET.SubElement(cac_partyidentification, CBC_ID)
        cbc_id_2.set("schemeID", custom_registration_type)
        cbc_id_2.text = custom_company_registration

        # Get the appropriate address
        address = get_address(sales_invoice_doc, company_doc)

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
        cbc_citysubdivisionname.text = address.address_line2
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
        cbc_id_3 = ET.SubElement(cac_taxscheme, CBC_ID)
        cbc_id_3.text = "VAT"

        cac_partylegalentity = ET.SubElement(cac_party_1, "cac:PartyLegalEntity")
        cbc_registrationname = ET.SubElement(
            cac_partylegalentity, "cbc:RegistrationName"
        )
        cbc_registrationname.text = sales_invoice_doc.company

        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred in company data: {e}"))
        return None


def customer_data(invoice, sales_invoice_doc):
    """
    customer data of address and need values
    """
    try:
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
        # frappe.throw(str(customer_doc))
        cac_accountingcustomerparty = ET.SubElement(
            invoice, "cac:AccountingCustomerParty"
        )
        cac_party_2 = ET.SubElement(cac_accountingcustomerparty, "cac:Party")
        cac_partyidentification_1 = ET.SubElement(
            cac_party_2, "cac:PartyIdentification"
        )
        cbc_id_4 = ET.SubElement(cac_partyidentification_1, CBC_ID)
        cbc_id_4.set("schemeID", str(customer_doc.custom_buyer_id_type))
        cbc_id_4.text = customer_doc.custom_buyer_id
        country_dict = country_code_mapping()
        address = None
        if customer_doc.custom_b2c != 1:
            if int(frappe.__version__.split(".", maxsplit=1)[0]) == 13:
                if sales_invoice_doc.customer_address:
                    address = frappe.get_doc(
                        "Address", sales_invoice_doc.customer_address
                    )
            else:
                if customer_doc.customer_primary_address:
                    address = frappe.get_doc(
                        "Address", customer_doc.customer_primary_address
                    )

            if not address:
                frappe.throw(_("Customer address is mandatory for non-B2C customers."))

            cac_postaladdress_1 = ET.SubElement(cac_party_2, "cac:PostalAddress")
            # frappe.throw(address.address_line1)
            if address.address_line1:
                cbc_streetname_1 = ET.SubElement(cac_postaladdress_1, "cbc:StreetName")
                cbc_streetname_1.text = address.address_line1

            if (
                hasattr(address, "custom_building_number")
                and address.custom_building_number
            ):
                cbc_buildingnumber_1 = ET.SubElement(
                    cac_postaladdress_1, "cbc:BuildingNumber"
                )
                cbc_buildingnumber_1.text = address.custom_building_number

            cbc_plotidentification_1 = ET.SubElement(
                cac_postaladdress_1, "cbc:PlotIdentification"
            )
            if hasattr(address, "po_box") and address.po_box:
                cbc_plotidentification_1.text = address.po_box
            elif address.address_line1:
                cbc_plotidentification_1.text = address.address_line1

            if address.address_line2:
                cbc_citysubdivisionname_1 = ET.SubElement(
                    cac_postaladdress_1, "cbc:CitySubdivisionName"
                )
                cbc_citysubdivisionname_1.text = address.address_line2

            if address.city:
                cbc_cityname_1 = ET.SubElement(cac_postaladdress_1, "cbc:CityName")
                cbc_cityname_1.text = address.city

            if address.pincode:
                cbc_postalzone_1 = ET.SubElement(cac_postaladdress_1, "cbc:PostalZone")
                cbc_postalzone_1.text = address.pincode

            if address.state:
                cbc_countrysubentity_1 = ET.SubElement(
                    cac_postaladdress_1, "cbc:CountrySubentity"
                )
                cbc_countrysubentity_1.text = address.state

            cac_country_1 = ET.SubElement(cac_postaladdress_1, "cac:Country")
            cbc_identificationcode_1 = ET.SubElement(
                cac_country_1, "cbc:IdentificationCode"
            )
            # frappe.throw(country_dict[address.country.lower()])
            if sales_invoice_doc.custom_zatca_export_invoice == 1:
                if address.country and address.country.lower() in country_dict:
                    cbc_identificationcode_1.text = country_dict[
                        address.country.lower()
                    ]
            else:
                cbc_identificationcode_1.text = "SA"
        cac_partytaxscheme_1 = ET.SubElement(cac_party_2, "cac:PartyTaxScheme")

        # Only include tax ID if country is Saudi Arabia
        if address and address.country == "Saudi Arabia":
            cbc_company_id = ET.SubElement(cac_partytaxscheme_1, "cbc:CompanyID")
            cbc_company_id.text = customer_doc.tax_id

        # Always include tax scheme
        cac_taxscheme_1 = ET.SubElement(cac_partytaxscheme_1, "cac:TaxScheme")
        cbc_id_5 = ET.SubElement(cac_taxscheme_1, "cbc:ID")
        cbc_id_5.text = "VAT"
        # cac_partytaxscheme_1 = ET.SubElement(cac_party_2, "cac:PartyTaxScheme")
        # cac_taxscheme_1 = ET.SubElement(cac_partytaxscheme_1, "cac:TaxScheme")
        # cbc_id_5 = ET.SubElement(cac_taxscheme_1, CBC_ID)
        # cbc_id_5.text = "VAT"
        cac_partylegalentity_1 = ET.SubElement(cac_party_2, "cac:PartyLegalEntity")
        cbc_registrationname_1 = ET.SubElement(
            cac_partylegalentity_1, "cbc:RegistrationName"
        )
        cbc_registrationname_1.text = customer_doc.customer_name

        return invoice
    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred in customer data: {e}"))
        return None


def delivery_and_payment_means(invoice, sales_invoice_doc, is_return):
    """
    Adds delivery and payment means elements to the XML invoice,
    including actual delivery date and payment means.
    """
    try:
        cac_delivery = ET.SubElement(invoice, "cac:Delivery")
        cbc_actual_delivery_date = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
        cbc_actual_delivery_date.text = str(sales_invoice_doc.due_date)

        cac_payment_means = ET.SubElement(invoice, "cac:PaymentMeans")
        cbc_payment_means_code = ET.SubElement(
            cac_payment_means, "cbc:PaymentMeansCode"
        )
        cbc_payment_means_code.text = "30"

        if is_return == 1:
            cbc_instruction_note = ET.SubElement(
                cac_payment_means, "cbc:InstructionNote"
            )
            cbc_instruction_note.text = "Cancellation"

        return invoice

    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Delivery and payment means failed: {e}"))
        return None  # Ensures all return paths explicitly return a value


def delivery_and_payment_means_for_compliance(
    invoice, sales_invoice_doc, compliance_type
):
    """
    Adds delivery and payment means elements to the XML invoice for compliance,
    including actual delivery date, payment means, and instruction notes for cancellations.
    """
    try:
        cac_delivery = ET.SubElement(invoice, "cac:Delivery")
        cbc_actual_delivery_date = ET.SubElement(cac_delivery, "cbc:ActualDeliveryDate")
        cbc_actual_delivery_date.text = str(sales_invoice_doc.due_date)

        cac_payment_means = ET.SubElement(invoice, "cac:PaymentMeans")
        cbc_payment_means_code = ET.SubElement(
            cac_payment_means, "cbc:PaymentMeansCode"
        )
        cbc_payment_means_code.text = "30"

        if compliance_type in {"3", "4", "5", "6"}:
            cbc_instruction_note = ET.SubElement(
                cac_payment_means, "cbc:InstructionNote"
            )
            cbc_instruction_note.text = "Cancellation"

        return invoice

    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(f"Delivery and payment means failed: {e}"))
        return None


def add_document_level_discount_with_tax(invoice, sales_invoice_doc):
    """
    Adds document-level discount elements to the XML invoice,
    including allowance charges, reason codes, and tax details.
    """
    try:

        cac_allowance_charge = ET.SubElement(invoice, "cac:AllowanceCharge")

        cbc_charge_indicator = ET.SubElement(
            cac_allowance_charge, "cbc:ChargeIndicator"
        )
        cbc_charge_indicator.text = "false"

        cbc_allowance_charge_reason_code = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReasonCode"
        )
        cbc_allowance_charge_reason_code.text = str(
            sales_invoice_doc.custom_zatca_discount_reason_code
        )

        cbc_allowance_charge_reason = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReason"
        )
        cbc_allowance_charge_reason.text = str(
            sales_invoice_doc.custom_zatca_discount_reason
        )

        cbc_amount = ET.SubElement(
            cac_allowance_charge, "cbc:Amount", currencyID=sales_invoice_doc.currency
        )
        if sales_invoice_doc.currency == "SAR":
            base_discount_amount = abs(
                sales_invoice_doc.get("base_discount_amount", 0.0)
            )
            cbc_amount.text = f"{base_discount_amount:.2f}"
        else:
            discount_amount = abs(sales_invoice_doc.get("discount_amount", 0.0))
            cbc_amount.text = f"{discount_amount:.2f}"

        cac_tax_category = ET.SubElement(cac_allowance_charge, "cac:TaxCategory")
        cbc_id = ET.SubElement(cac_tax_category, CBC_ID)
        if sales_invoice_doc.custom_zatca_tax_category == "Standard":
            cbc_id.text = "S"
        elif sales_invoice_doc.custom_zatca_tax_category == "Zero Rated":
            cbc_id.text = "Z"
        elif sales_invoice_doc.custom_zatca_tax_category == "Exempted":
            cbc_id.text = "E"
        elif (
            sales_invoice_doc.custom_zatca_tax_category
            == "Services outside scope of tax / Not subject to VAT"
        ):
            cbc_id.text = "O"

        cbc_percent = ET.SubElement(cac_tax_category, "cbc:Percent")
        cbc_percent.text = f"{float(sales_invoice_doc.taxes[0].rate):.2f}"

        cac_tax_scheme = ET.SubElement(cac_tax_category, "cac:TaxScheme")
        cbc_tax_scheme_id = ET.SubElement(cac_tax_scheme, CBC_ID)
        cbc_tax_scheme_id.text = "VAT"

        return invoice

    except (ET.ParseError, AttributeError, ValueError) as e:
        frappe.throw(_(
            f"Error occurred while processing allowance charge data without template: {e}"
        ))
        return None


def add_document_level_discount_with_tax_template(invoice, sales_invoice_doc):
    """
    Adds document-level discount elements to the XML invoice,
    including allowance charges, reason codes, and tax details.
    """
    try:
        # Create the AllowanceCharge element
        cac_allowance_charge = ET.SubElement(invoice, "cac:AllowanceCharge")

        # ChargeIndicator
        cbc_charge_indicator = ET.SubElement(
            cac_allowance_charge, "cbc:ChargeIndicator"
        )
        cbc_charge_indicator.text = "false"  # Indicates a discount

        # AllowanceChargeReason
        cbc_allowance_charge_reason_code = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReasonCode"
        )
        cbc_allowance_charge_reason_code.text = str(
            sales_invoice_doc.custom_zatca_discount_reason_code
        )

        cbc_allowance_charge_reason = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReason"
        )
        cbc_allowance_charge_reason.text = str(
            sales_invoice_doc.custom_zatca_discount_reason
        )

        cbc_amount = ET.SubElement(
            cac_allowance_charge, "cbc:Amount", currencyID=sales_invoice_doc.currency
        )
        if sales_invoice_doc.currency == "SAR":
            base_discount_amount = abs(
                sales_invoice_doc.get("base_discount_amount", 0.0)
            )
            cbc_amount.text = f"{base_discount_amount:.2f}"
        else:
            discount_amount = abs(sales_invoice_doc.get("discount_amount", 0.0))
            cbc_amount.text = f"{discount_amount:.2f}"

        # Tax Category Section
        cac_tax_category = ET.SubElement(cac_allowance_charge, "cac:TaxCategory")
        cbc_id = ET.SubElement(cac_tax_category, CBC_ID)

        vat_category_code = "Standard"
        tax_percentage = 0.0

        for item in sales_invoice_doc.items:
            item_tax_template_doc = frappe.get_doc(
                "Item Tax Template", item.item_tax_template
            )
            vat_category_code = item_tax_template_doc.custom_zatca_tax_category
            tax_percentage = (
                item_tax_template_doc.taxes[0].tax_rate
                if item_tax_template_doc.taxes
                else 15
            )
            break  # Assuming that all items will have the same tax category and percentage

        if vat_category_code == "Standard":
            cbc_id.text = "S"
        elif vat_category_code == "Zero Rated":
            cbc_id.text = "Z"
        elif vat_category_code == "Exempted":
            cbc_id.text = "E"
        elif vat_category_code == "Services outside scope of tax / Not subject to VAT":
            cbc_id.text = "O"
        else:
            frappe.throw(
                "Invalid VAT category code. Must be one of 'Standard', 'Zero Rated', 'Exempted', "
                "or 'Services outside scope of tax / Not subject to VAT'."
            )

        cbc_percent = ET.SubElement(cac_tax_category, "cbc:Percent")
        cbc_percent.text = f"{tax_percentage:.2f}"

        cac_tax_scheme = ET.SubElement(cac_tax_category, "cac:TaxScheme")
        cbc_tax_scheme_id = ET.SubElement(cac_tax_scheme, CBC_ID)
        cbc_tax_scheme_id.text = "VAT"

        return invoice

    except (ET.ParseError, AttributeError, ValueError, frappe.DoesNotExistError) as e:
        frappe.throw(_(f"Error occurred while processing allowance charge data: {e}"))
        return None


def add_nominal_discount_tax(invoice, sales_invoice_doc):
    """
    Adds nominal discount and related tax details to the XML structure.
    """
    try:

        cac_allowance_charge = ET.SubElement(invoice, "cac:AllowanceCharge")
        cbc_charge_indicator = ET.SubElement(
            cac_allowance_charge, "cbc:ChargeIndicator"
        )
        cbc_charge_indicator.text = "false"  # Indicates a discount

        cbc_allowance_charge_reason_code = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReasonCode"
        )
        cbc_allowance_charge_reason_code.text = str(
            sales_invoice_doc.custom_zatca_discount_reason_code
        )

        cbc_allowance_charge_reason = ET.SubElement(
            cac_allowance_charge, "cbc:AllowanceChargeReason"
        )
        cbc_allowance_charge_reason.text = str(
            sales_invoice_doc.custom_zatca_discount_reason
        )

        cbc_amount = ET.SubElement(
            cac_allowance_charge, "cbc:Amount", currencyID=sales_invoice_doc.currency
        )

        total_line_extension = 0

        for single_item in sales_invoice_doc.items:
            line_extension_amount = abs(
                round(
                    single_item.amount / (1 + sales_invoice_doc.taxes[0].rate / 100), 2
                )
            )
            total_line_extension += round(line_extension_amount, 2)
        discount_amount = abs(round(sales_invoice_doc.discount_amount, 2))
        difference = abs(round(discount_amount - total_line_extension, 2))

        if (
            sales_invoice_doc.currency == "SAR"
            and sales_invoice_doc.taxes[0].included_in_print_rate == 0
        ):
            base_discount_amount = sales_invoice_doc.base_total
            cbc_amount.text = f"{base_discount_amount:.2f}"

        elif (
            sales_invoice_doc.currency == "SAR"
            and sales_invoice_doc.taxes[0].included_in_print_rate == 1
        ):
            base_discount_amount = (
                total_line_extension
                if difference == 0.01
                else sales_invoice_doc.base_discount_amount
            )
            cbc_amount.text = f"{base_discount_amount:.2f}"

        elif (
            sales_invoice_doc.currency != "SAR"
            and sales_invoice_doc.taxes[0].included_in_print_rate == 0
        ):
            discount_amount = sales_invoice_doc.total
            cbc_amount.text = f"{discount_amount:.2f}"

        elif (
            sales_invoice_doc.currency != "SAR"
            and sales_invoice_doc.taxes[0].included_in_print_rate == 1
        ):
            discount_amount = (
                total_line_extension
                if difference == 0.01
                else sales_invoice_doc.discount_amount
            )
            cbc_amount.text = f"{discount_amount:.2f}"

        cac_tax_category = ET.SubElement(cac_allowance_charge, "cac:TaxCategory")
        cbc_id = ET.SubElement(cac_tax_category, CBC_ID)
        cbc_id.text = "O"

        cbc_percent = ET.SubElement(cac_tax_category, "cbc:Percent")
        cbc_percent.text = "0.00"

        cbc_tax_exemption_reason_code = ET.SubElement(
            cac_tax_category, "cbc:TaxExemptionReasonCode"
        )
        cbc_tax_exemption_reason_code.text = "VATEX-SA-OOS"

        cbc_tax_exemption_reason = ET.SubElement(
            cac_tax_category, "cbc:TaxExemptionReason"
        )
        cbc_tax_exemption_reason.text = "Special discount offer"

        cac_tax_scheme = ET.SubElement(cac_tax_category, "cac:TaxScheme")
        cbc_tax_scheme_id = ET.SubElement(cac_tax_scheme, CBC_ID)
        cbc_tax_scheme_id.text = "VAT"

        return invoice

    except (ValueError, KeyError, AttributeError) as error:
        frappe.throw(_(f"Error occurred in nominal discount: {str(error)}"))
        return None
