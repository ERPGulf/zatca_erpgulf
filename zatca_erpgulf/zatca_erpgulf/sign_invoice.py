from lxml import etree
import hashlib
import base64 
import lxml.etree as MyTree
from datetime import datetime
import xml.etree.ElementTree as ET
import frappe
from zatca_erpgulf.zatca_erpgulf.createxml import xml_tags,salesinvoice_data,add_document_level_discount_with_tax_template,tax_Data_nominal,tax_Data_with_template_nominal,add_document_level_discount_with_tax,invoice_Typecode_Simplified,invoice_Typecode_Standard,doc_Reference,additional_Reference ,company_Data,customer_Data,delivery_And_PaymentMeans,tax_Data,item_data,xml_structuring,invoice_Typecode_Compliance,delivery_And_PaymentMeans_for_Compliance,doc_Reference_compliance,get_tax_total_from_items,tax_Data_with_template,item_data_with_template,add_nominal_discount_tax
import pyqrcode
from pyqrcode import create as qr_create
import io
import os
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
# frappe.init(site="prod.erpgulf.com")
# frappe.connect()
from zatca_erpgulf.zatca_erpgulf.create_qr import create_qr_code
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

def encode_customoid(custom_string):
    # Create an encoder
    encoder = asn1.Encoder()
    encoder.start()

    # Encode the string as an OCTET STRING
    encoder.write(custom_string, asn1.Numbers.UTF8String)

    # Get the encoded byte string
    return encoder.output()



def parse_csr_config(csr_config_string):
    csr_config = {}
    lines = csr_config_string.splitlines()
    for line in lines:
        key, value = line.split('=', 1)
        csr_config[key.strip()] = value.strip()
    return csr_config

def get_csr_data(company_abbr):
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        csr_config_string = company_doc.custom_csr_config 

        if not csr_config_string:
            frappe.throw("No CSR config found in company settings")

        csr_config = parse_csr_config(csr_config_string)
        
        csr_values = {
            "csr.common.name": csr_config.get("csr.common.name"),
            "csr.serial.number": csr_config.get("csr.serial.number"),
            "csr.organization.identifier": csr_config.get("csr.organization.identifier"),
            "csr.organization.unit.name": csr_config.get("csr.organization.unit.name"),
            "csr.organization.name": csr_config.get("csr.organization.name"),
            "csr.country.name": csr_config.get("csr.country.name"),
            "csr.invoice.type": csr_config.get("csr.invoice.type"),
            "csr.location.address": csr_config.get("csr.location.address"),
            "csr.industry.business.category": csr_config.get("csr.industry.business.category"),
        }
        
        return csr_values

    except Exception as e:
        frappe.throw("Error in fetching CSR data: " + str(e))

def create_private_keys(company_abbr):
    try:
    
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        
        # Generate the private key using elliptic curve cryptography (SECP256K1)
        private_key = ec.generate_private_key(ec.SECP256K1(), backend=default_backend())
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Store the private key directly in the company document
        company_doc.custom_private_key = private_key_pem.decode('utf-8')
        company_doc.save(ignore_permissions=True)
        
        return private_key_pem

    except Exception as e:
        frappe.throw(f"Error in creating private key: {str(e)}")

@frappe.whitelist(allow_guest=True)
def create_csr(portal_type, company_abbr):
    try:
        csr_values = get_csr_data(company_abbr)
        company_csr_data = csr_values

        csr_common_name = company_csr_data.get("csr.common.name")
        csr_serial_number = company_csr_data.get("csr.serial.number")
        csr_organization_identifier = company_csr_data.get("csr.organization.identifier")
        csr_organization_unit_name = company_csr_data.get("csr.organization.unit.name")
        csr_organization_name = company_csr_data.get("csr.organization.name")
        csr_country_name = company_csr_data.get("csr.country.name")
        csr_invoice_type = company_csr_data.get("csr.invoice.type")
        csr_location_address = company_csr_data.get("csr.location.address")
        csr_industry_business_category = company_csr_data.get("csr.industry.business.category")

        if portal_type == "Sandbox":
            customoid = encode_customoid("TESTZATCA-Code-Signing")
        elif portal_type == "Simulation":
            customoid = encode_customoid("PREZATCA-Code-Signing")
        else:
            customoid = encode_customoid("ZATCA-Code-Signing")
        
        private_key_pem = create_private_keys(company_abbr)
        private_key = serialization.load_pem_private_key(private_key_pem, password=None, backend=default_backend())

        custom_oid_string = "1.3.6.1.4.1.311.20.2"
        oid = ObjectIdentifier(custom_oid_string)
        custom_extension = x509.extensions.UnrecognizedExtension(oid, customoid) 
        
        dn = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, csr_country_name),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, csr_organization_unit_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, csr_organization_name),
            x509.NameAttribute(NameOID.COMMON_NAME, csr_common_name),
        ])
        
        alt_name = x509.SubjectAlternativeName([
            x509.DirectoryName(x509.Name([
                x509.NameAttribute(NameOID.SURNAME, csr_serial_number),
                x509.NameAttribute(NameOID.USER_ID, csr_organization_identifier),
                x509.NameAttribute(NameOID.TITLE, csr_invoice_type),
                x509.NameAttribute(ObjectIdentifier("2.5.4.26"), csr_location_address),
                x509.NameAttribute(NameOID.BUSINESS_CATEGORY, csr_industry_business_category),
            ])),
        ])
        
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(dn)
            .add_extension(custom_extension, critical=False)
            .add_extension(alt_name, critical=False)
            .sign(private_key, hashes.SHA256(), backend=default_backend())
        )
        mycsr = csr.public_bytes(serialization.Encoding.PEM)
        base64csr = base64.b64encode(mycsr)
        encoded_string = base64csr.decode('utf-8')

        company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
        # if not company_doc.custom_csr_data:
        #     company_doc.custom_csr_data = {}
        # updated_data = f"{company_doc.custom_csr_data}\n{encoded_string}"
        # company_doc.custom_csr_data = updated_data.strip()
        # company_doc.save(ignore_permissions=True)
        # frappe.msgprint("CSR generation successful. CSR saved")
        company_doc.custom_csr_data = encoded_string.strip()

# Save the updated company document
        company_doc.save(ignore_permissions=True)

# Notify the user that the CSR generation was successful
        # frappe.msgprint("CSR generation successful. CSR saved")
        
        return encoded_string
    
    except Exception as e:
        frappe.throw("Error in creating CSR: " + str(e))




def get_API_url(company_abbr, base_url):
    try:
        company_doc = frappe.get_doc('Company', {'abbr': company_abbr})
        if company_doc.custom_select == "Sandbox":
            url = company_doc.custom_sandbox_url + base_url
        elif company_doc.custom_select == "Simulation":
            url = company_doc.custom_simulation_url + base_url
        else:
            url = company_doc.custom_production_url + base_url
        
        return url 
    except Exception as e:
        frappe.throw("Error in getting API URL: " + str(e))


@frappe.whitelist(allow_guest=True)
def create_CSID(company_abbr):
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        csr_data_str = company_doc.get("custom_csr_data", "")

        if not csr_data_str:
            frappe.throw("No CSR data found for the company.")
        
        # Use the CSR data directly, assuming it's already in the correct format
        csr_contents = csr_data_str.strip()
        
        if not csr_contents:
            frappe.throw(f"No valid CSR data found for company {company_name}")
        
        payload = json.dumps({
            "csr": csr_contents
        })
        
        # frappe.msgprint(f"Using OTP: {company_doc.custom_otp}")
        
        headers = {
            'accept': 'application/json',
            'OTP': company_doc.custom_otp,
            'Accept-Version': 'V2',
            'Content-Type': 'application/json',
            'Cookie': 'TS0106293e=0132a679c07382ce7821148af16b99da546c13ce1dcddbef0e19802eb470e539a4d39d5ef63d5c8280b48c529f321e8b0173890e4f'
        }
        
        frappe.publish_realtime('show_gif', {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"})
        
        response = requests.post(
            url=get_API_url(company_abbr, base_url="compliance"), 
            headers=headers, 
            data=payload
        )
        frappe.publish_realtime('hide_gif')
        
        if response.status_code == 400:
            frappe.throw("Error: OTP is not valid. " + response.text)
        if response.status_code != 200:
            frappe.throw("Error: Issue with Certificate or OTP. " + response.text)
        frappe.msgprint(str(response.text))
        # Extracting data from the response
        data = json.loads(response.text)
        
        concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
        encoded_value = base64.b64encode(concatenated_value.encode()).decode()
        
        # Updating the company's certificate and CSID data directly
        company_doc.custom_certificate = base64.b64decode(data["binarySecurityToken"]).decode('utf-8')
        company_doc.custom_basic_auth_from_csid = encoded_value
        company_doc.custom_compliance_request_id_ = data["requestID"]
        
        company_doc.save(ignore_permissions=True)

        return (response.text)
    
    except Exception as e:
        frappe.throw("Error in creating CSID: " + str(e))



def create_public_key(company_abbr):
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        certificate_data_str = company_doc.get("custom_certificate", "")

        if not certificate_data_str:
            frappe.throw("No certificate data found for the company.")
        cert_base64 = """
        -----BEGIN CERTIFICATE-----
        {base_64}
        -----END CERTIFICATE-----
        """.format(base_64=certificate_data_str.strip())
        
        cert = x509.load_pem_x509_certificate(cert_base64.encode(), default_backend())
        public_key = cert.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()  
        
        company_doc.custom_public_key = public_key_pem
        company_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.throw("Error in public key creation: " + str(e))




def removeTags(finalzatcaxml):
                try:
                    #Code corrected by Farook K - ERPGulf
                    xml_file = MyTree.fromstring(finalzatcaxml)
                    xsl_file = MyTree.fromstring('''<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                                    xmlns:xs="http://www.w3.org/2001/XMLSchema"
                                    xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                                    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                                    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                                    xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
                                    exclude-result-prefixes="xs"
                                    version="2.0">
                                    <xsl:output omit-xml-declaration="yes" encoding="utf-8" indent="no"/>
                                    <xsl:template match="node() | @*">
                                        <xsl:copy>
                                            <xsl:apply-templates select="node() | @*"/>
                                        </xsl:copy>
                                    </xsl:template>
                                    <xsl:template match="//*[local-name()='Invoice']//*[local-name()='UBLExtensions']"></xsl:template>
                                    <xsl:template match="//*[local-name()='AdditionalDocumentReference'][cbc:ID[normalize-space(text()) = 'QR']]"></xsl:template>
                                        <xsl:template match="//*[local-name()='Invoice']/*[local-name()='Signature']"></xsl:template>
                                    </xsl:stylesheet>''')
                    transform = MyTree.XSLT(xsl_file.getroottree())
                    transformed_xml = transform(xml_file.getroottree())
                    return transformed_xml
                except Exception as e:
                                frappe.throw(" error in remove tags: "+ str(e) )
                    

def canonicalize_xml (tag_removed_xml):
                try:
                    #Code corrected by Farook K - ERPGulf
                    canonical_xml = etree.tostring(tag_removed_xml, method="c14n").decode()
                    return canonical_xml    
                except Exception as e:
                            frappe.throw(" error in canonicalise xml: "+ str(e) )    

def getInvoiceHash(canonicalized_xml):
        try:
            #Code corrected by Farook K - ERPGulf
            hash_object = hashlib.sha256(canonicalized_xml.encode())
            hash_hex = hash_object.hexdigest()
            # print(hash_hex)
            hash_base64 = base64.b64encode(bytes.fromhex(hash_hex)).decode('utf-8')
            # base64_encoded = base64.b64encode(hash_hex.encode()).decode()
            return hash_hex,hash_base64
        except Exception as e:
                    frappe.throw(" error in Invoice hash of xml: "+ str(e) )
    


def digital_signature(hash1, company_abbr):
    try:
        # Retrieve the company document based on the provided abbreviation
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        private_key_data_str = company_doc.get("custom_private_key")

        if not private_key_data_str:
            frappe.throw("No private key data found for the company.")
        
        # Use the private key data directly
        private_key_bytes = private_key_data_str.encode('utf-8')
        private_key = serialization.load_pem_private_key(private_key_bytes, password=None, backend=default_backend())
        hash_bytes = bytes.fromhex(hash1)
        signature = private_key.sign(hash_bytes, ec.ECDSA(hashes.SHA256()))
        encoded_signature = base64.b64encode(signature).decode()
        
        return encoded_signature

    except Exception as e:
        frappe.throw("Error in digital signature: " + str(e))


def extract_certificate_details(company_abbr):
    try:
        # Retrieve the company document based on the provided abbreviation
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        certificate_data_str = company_doc.get("custom_certificate")

        if not certificate_data_str:
            frappe.throw(f"No certificate data found for company {company_name}")
        
        # The certificate content is directly stored as a string
        certificate_content = certificate_data_str.strip()

        if not certificate_content:
            frappe.throw(f"No valid certificate content found for company {company_name}")

        # Format the certificate string to PEM format if not already in correct PEM format
        formatted_certificate = "-----BEGIN CERTIFICATE-----\n"
        formatted_certificate += "\n".join(certificate_content[i:i+64] for i in range(0, len(certificate_content), 64))
        formatted_certificate += "\n-----END CERTIFICATE-----\n"
        
        # Load the certificate using cryptography
        certificate_bytes = formatted_certificate.encode('utf-8')
        cert = x509.load_pem_x509_certificate(certificate_bytes, default_backend())
        
        # Extract the issuer name and serial number
        formatted_issuer_name = cert.issuer.rfc4514_string()
        issuer_name = ", ".join([x.strip() for x in formatted_issuer_name.split(',')])
        serial_number = cert.serial_number

        return issuer_name, serial_number

    except Exception as e:
        frappe.throw("Error in extracting certificate details: " + str(e))
    

def certificate_hash(company_abbr):
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        certificate_data_str = company_doc.get("custom_certificate")

        if not certificate_data_str:
            frappe.throw(f"No certificate data found for company {company_name}")
        
        certificate_data = certificate_data_str.strip()

        if not certificate_data:
            frappe.throw(f"No valid certificate data found for company {company_name}")
        
        # Calculate the SHA-256 hash of the certificate data
        certificate_data_bytes = certificate_data.encode('utf-8')
        sha256_hash = hashlib.sha256(certificate_data_bytes).hexdigest()
        
        # Encode the hash in base64
        base64_encoded_hash = base64.b64encode(sha256_hash.encode('utf-8')).decode('utf-8')

        return base64_encoded_hash

    except Exception as e:
        frappe.throw("Error in obtaining certificate hash: " + str(e))




def signxml_modify(company_abbr):
                try:
                    company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
                    company_doc = frappe.get_doc('Company', company_name)
                    encoded_certificate_hash= certificate_hash(company_abbr)
                    issuer_name, serial_number = extract_certificate_details(company_abbr)
                    original_invoice_xml = etree.parse(frappe.local.site + '/private/files/finalzatcaxml.xml')
                    root = original_invoice_xml.getroot()
                    namespaces = {
                    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
                    'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
                    'sac':"urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2", 
                    'xades': 'http://uri.etsi.org/01903/v1.3.2#',
                    'ds': 'http://www.w3.org/2000/09/xmldsig#'}
                    ubl_extensions_xpath = "//*[local-name()='Invoice']//*[local-name()='UBLExtensions']"
                    qr_xpath = "//*[local-name()='AdditionalDocumentReference'][cbc:ID[normalize-space(text()) = 'QR']]"
                    signature_xpath = "//*[local-name()='Invoice']//*[local-name()='Signature']"
                    xpath_dv = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:CertDigest/ds:DigestValue")
                    xpath_signTime = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningTime")
                    xpath_issuerName = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:IssuerSerial/ds:X509IssuerName")
                    xpath_serialNum = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties//xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:IssuerSerial/ds:X509SerialNumber")
                    element_dv = root.find(xpath_dv, namespaces)
                    element_st = root.find(xpath_signTime, namespaces)
                    element_in = root.find(xpath_issuerName, namespaces)
                    element_sn = root.find(xpath_serialNum, namespaces)
                    element_dv.text = (encoded_certificate_hash)
                    element_st.text =  datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
                    signing_time =element_st.text
                    element_in.text = issuer_name
                    element_sn.text = str(serial_number)
                    with open(frappe.local.site + "/private/files/after_step_4.xml", 'wb') as file:
                        original_invoice_xml.write(file,encoding='utf-8',xml_declaration=True,)
                    return namespaces ,signing_time
                except Exception as e:
                    frappe.throw(" error in modification of xml sign part: "+ str(e) )

def generate_Signed_Properties_Hash(signing_time,issuer_name,serial_number,encoded_certificate_hash):
            try:
                xml_string = '''<xades:SignedProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Id="xadesSignedProperties">
                                    <xades:SignedSignatureProperties>
                                        <xades:SigningTime>{signing_time}</xades:SigningTime>
                                        <xades:SigningCertificate>
                                            <xades:Cert>
                                                <xades:CertDigest>
                                                    <ds:DigestMethod xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                                    <ds:DigestValue xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{certificate_hash}</ds:DigestValue>
                                                </xades:CertDigest>
                                                <xades:IssuerSerial>
                                                    <ds:X509IssuerName xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{issuer_name}</ds:X509IssuerName>
                                                    <ds:X509SerialNumber xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{serial_number}</ds:X509SerialNumber>
                                                </xades:IssuerSerial>
                                            </xades:Cert>
                                        </xades:SigningCertificate>
                                    </xades:SignedSignatureProperties>
                                </xades:SignedProperties>'''
                xml_string_rendered = xml_string.format(signing_time=signing_time, certificate_hash=encoded_certificate_hash, issuer_name=issuer_name, serial_number=str(serial_number))
                utf8_bytes = xml_string_rendered.encode('utf-8')
                hash_object = hashlib.sha256(utf8_bytes)
                hex_sha256 = hash_object.hexdigest()
                # print(hex_sha256)
                signed_properties_base64=  base64.b64encode(hex_sha256.encode('utf-8')).decode('utf-8')
                # print(signed_properties_base64)
                return signed_properties_base64
            except Exception as e:
                    frappe.throw(" error in generating signed properties hash: "+ str(e) )




def populate_The_UBL_Extensions_Output(encoded_signature, namespaces, signed_properties_base64, encoded_hash, company_abbr):
    try:
        # Load the XML file
        updated_invoice_xml = etree.parse(frappe.local.site + '/private/files/after_step_4.xml')
        root3 = updated_invoice_xml.getroot()

        # Retrieve the company document based on the provided abbreviation
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        certificate_data_str = company_doc.get("custom_certificate")

        if not certificate_data_str:
            frappe.throw(f"No certificate data found for company {company_name}")
        
        # Directly use the certificate data
        content = certificate_data_str.strip()

        if not content:
            frappe.throw(f"No valid certificate content found for company {company_name}")
    
        # Define the XPaths for the elements to update
        xpath_signvalue = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignatureValue")
        xpath_x509certi = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:KeyInfo/ds:X509Data/ds:X509Certificate")
        xpath_digvalue = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@URI='#xadesSignedProperties']/ds:DigestValue")
        xpath_digvalue2 = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@Id='invoiceSignedData']/ds:DigestValue")

        # Locate elements to update in the XML
        signValue6 = root3.find(xpath_signvalue, namespaces)
        x509Certificate6 = root3.find(xpath_x509certi, namespaces)
        digestvalue6 = root3.find(xpath_digvalue, namespaces)
        digestvalue6_2 = root3.find(xpath_digvalue2, namespaces)

        
        signValue6.text = encoded_signature
        x509Certificate6.text = content
        digestvalue6.text = signed_properties_base64
        digestvalue6_2.text = encoded_hash

        
        with open(frappe.local.site + "/private/files/final_xml_after_sign.xml", 'wb') as file:
            updated_invoice_xml.write(file, encoding='utf-8', xml_declaration=True)
    
    except Exception as e:
        frappe.throw("Error in populating UBL extension output: " + str(e))


def extract_public_key_data(company_abbr):
    try:
        # Retrieve the company document based on the provided abbreviation
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)

        # Get the public key data for the company
        public_key_pem = company_doc.get("custom_public_key", "")
        if not public_key_pem:
            frappe.throw(f"No public key found for company {company_name}")
        
        # Simplify the public key extraction by directly processing PEM data
        lines = public_key_pem.splitlines()
        key_data = ''.join(lines[1:-1])
        key_data = key_data.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '')
        key_data = key_data.replace(' ', '').replace('\n', '')

        return key_data

    except Exception as e:
        frappe.throw("Error in extracting public key data: " + str(e))



def get_tlv_for_value(tag_num, tag_value):
                try:
                    tag_num_buf = bytes([tag_num])
                    if tag_value is None:
                        frappe.throw(f"Error: Tag value for tag number {tag_num} is None")
                    if isinstance(tag_value, str):
                        if len(tag_value) < 256:
                            tag_value_len_buf = bytes([len(tag_value)])
                        else:
                            tag_value_len_buf = bytes([0xFF, (len(tag_value) >> 8) & 0xFF, len(tag_value) & 0xFF])
                        tag_value = tag_value.encode('utf-8')
                    else:
                        tag_value_len_buf = bytes([len(tag_value)])
                    return tag_num_buf + tag_value_len_buf + tag_value
                except Exception as e:
                    frappe.throw(" error in getting the tlv data value: "+ str(e) )



def tag8_publickey(company_abbr):
    try:
        create_public_key(company_abbr)
        base64_encoded = extract_public_key_data(company_abbr)
        byte_data = base64.b64decode(base64_encoded)
        hex_data = binascii.hexlify(byte_data).decode('utf-8')
        chunks = [hex_data[i:i + 2] for i in range(0, len(hex_data), 2)]
        value = ''.join(chunks)
        binary_data = bytes.fromhex(value)
        base64_encoded1 = base64.b64encode(binary_data).decode('utf-8')
        return binary_data
    except Exception as e: 
        frappe.throw("Error in tag 8 from public key: " + str(e))


def tag9_signature_ecdsa(company_abbr):
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
    
        certificate_content = company_doc.custom_certificate or ""
        if not certificate_content:
            frappe.throw(f"No certificate found for company in tag9 {company_abbr}")
        
        formatted_certificate = "-----BEGIN CERTIFICATE-----\n"
        formatted_certificate += "\n".join(certificate_content[i:i+64] for i in range(0, len(certificate_content), 64))
        formatted_certificate += "\n-----END CERTIFICATE-----\n"
    
        certificate_bytes = formatted_certificate.encode('utf-8')
        cert = x509.load_pem_x509_certificate(certificate_bytes, default_backend())
        signature = cert.signature
        signature_hex = "".join("{:02x}".format(byte) for byte in signature)
        signature_bytes = bytes.fromhex(signature_hex)
        signature_base64 = base64.b64encode(signature_bytes).decode()
        return signature_bytes

    except Exception as e:
        frappe.throw("Error in tag 9 (signaturetag): " + str(e))


def generate_tlv_xml(company_abbr):
    try:
        
        with open(frappe.local.site + "/private/files/final_xml_after_sign.xml", 'rb') as file:
            xml_data = file.read()
        root = etree.fromstring(xml_data)
        namespaces = {
            'ubl': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
            'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#'
        }
        issue_date_xpath = "/ubl:Invoice/cbc:IssueDate"
        issue_time_xpath = "/ubl:Invoice/cbc:IssueTime"
        issue_date_results = root.xpath(issue_date_xpath, namespaces=namespaces)
        issue_time_results = root.xpath(issue_time_xpath, namespaces=namespaces)
        issue_date = issue_date_results[0].text.strip() if issue_date_results else 'Missing Data'
        issue_time = issue_time_results[0].text.strip() if issue_time_results else 'Missing Data'
        issue_date_time = issue_date + 'T' + issue_time 
        tags_xpaths = [
            (1, "/ubl:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName"),
            (2, "/ubl:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID"),
            (3, None),  
            (4, "/ubl:Invoice/cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"),
            (5, "/ubl:Invoice/cac:TaxTotal/cbc:TaxAmount"),
            (6, "/ubl:Invoice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference/ds:DigestValue"),
            (7, "/ubl:Invoice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignatureValue"),
            (8, None), 
            (9, None),
        ]
        result_dict = {}
        for tag, xpath in tags_xpaths:
            if isinstance(xpath, str):  
                elements = root.xpath(xpath, namespaces=namespaces)
                if elements:
                    value = elements[0].text if isinstance(elements[0], etree._Element) else elements[0]
                    result_dict[tag] = value
                else:
                    result_dict[tag] = 'Not found'
            else:
                result_dict[tag] = xpath  
        result_dict[3] = issue_date_time
        result_dict[8] = tag8_publickey(company_abbr)  
        result_dict[9] = tag9_signature_ecdsa(company_abbr)  
        result_dict[1] = result_dict[1].encode('utf-8')  # Handling Arabic company name in QR Code
        # ffrappe.throw("Error occurred while processing. Payload: " + str(result_dict))
        return result_dict
    except Exception as e:
        frappe.throw("Error in getting the entire TLV data: " + str(e))


def update_Qr_toXml(qrCodeB64, company_abbr):
    try:
        xml_file_path = frappe.local.site + "/private/files/final_xml_after_sign.xml"
        xml_tree = etree.parse(xml_file_path)
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }
        qr_code_element = xml_tree.find('.//cac:AdditionalDocumentReference[cbc:ID="QR"]/cac:Attachment/cbc:EmbeddedDocumentBinaryObject', namespaces=namespaces)
        
        if qr_code_element is not None:
            qr_code_element.text = qrCodeB64  
        else:
            frappe.msgprint(f"QR code element not found in the XML for company {company_abbr}")
        xml_tree.write(xml_file_path, encoding="UTF-8", xml_declaration=True)

    except Exception as e:
        frappe.throw(f"Error in saving TLV data to XML for company {company_abbr}: " + str(e))


def structuring_signedxml():
                try:
                    with open(frappe.local.site + '/private/files/final_xml_after_sign.xml', 'r') as file:
                        xml_content = file.readlines()
                    indentations = {
                        29: ['<xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="signature">','</xades:QualifyingProperties>'],
                        33: ['<xades:SignedProperties Id="xadesSignedProperties">', '</xades:SignedProperties>'],
                        37: ['<xades:SignedSignatureProperties>','</xades:SignedSignatureProperties>'],
                        41: ['<xades:SigningTime>', '<xades:SigningCertificate>','</xades:SigningCertificate>'],
                        45: ['<xades:Cert>','</xades:Cert>'],
                        49: ['<xades:CertDigest>', '<xades:IssuerSerial>', '</xades:CertDigest>', '</xades:IssuerSerial>'],
                        53: ['<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>', '<ds:DigestValue>', '<ds:X509IssuerName>', '<ds:X509SerialNumber>']
                    }
                    def adjust_indentation(line):
                        for col, tags in indentations.items():
                            for tag in tags:
                                if line.strip().startswith(tag):
                                    return ' ' * (col - 1) + line.lstrip()
                        return line
                    adjusted_xml_content = [adjust_indentation(line) for line in xml_content]
                    with open(frappe.local.site + '/private/files/final_xml_after_indent.xml', 'w') as file:
                        file.writelines(adjusted_xml_content)
                    signed_xmlfile_name = frappe.local.site + '/private/files/final_xml_after_indent.xml'
                    return signed_xmlfile_name
                except Exception as e:
                    frappe.throw(" error in structuring signed xml: "+ str(e) )
                        
def xml_base64_Decode(signed_xmlfile_name):
                    try:
                        with open(signed_xmlfile_name, "r") as file:
                                        xml = file.read().lstrip()
                                        base64_encoded = base64.b64encode(xml.encode("utf-8"))
                                        base64_decoded = base64_encoded.decode("utf-8")
                                        return base64_decoded
                    except Exception as e:
                        frappe.msgprint("Error in xml base64:  " + str(e) )


def compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name, company_abbr):
    
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)
        
        
        
        # Prepare the payload without JSON formatting
        payload = json.dumps({

                        "invoiceHash": encoded_hash,
                        "uuid": uuid1,
                        "invoice": xml_base64_Decode(signed_xmlfile_name) })
        # frappe.throw(f"payload used: {payload}")
        
        
        # payload_dict = json.loads(payload)
        # invoice_only = payload_dict["invoice"]
        # frappe.throw(f"Invoice content: {invoice_only}")
        # Simplify the basic auth retrieval process
        csid = company_doc.custom_basic_auth_from_csid
        if not csid:
            frappe.throw("CSID for company {} not found".format(company_abbr))
        headers = {
            'accept': 'application/json',
            'Accept-Language': 'en',
            'Accept-Version': 'V2',
            'Authorization': "Basic " + csid,
            'Content-Type': 'application/json'
        }
        # frappe.throw(f"Parameters passed to requests.request:\n"
        #      f"Method: POST\n"
        #      f"URL: {get_API_url(company_abbr, base_url='compliance/invoices')}\n"
        #      f"Headers: {headers}\n"
        #      f"Payload: {payload}")
        
        
        response = requests.request("POST", url=get_API_url(company_abbr,base_url="compliance/invoices"), headers=headers, data=payload)
        frappe.msgprint(response.text)
        if response.status_code != 200:
            frappe.throw(f"Error in compliance: {response.text}")
        return response.text    
    except requests.exceptions.RequestException as e:
        frappe.msgprint(f"Request exception occurred: {str(e)}")
        return "error in compliance", "NOT ACCEPTED"

    except Exception as e:
        frappe.throw(f"ERROR in clearance invoice, ZATCA validation: {str(e)}")   
             


@frappe.whitelist(allow_guest=True)
def production_CSID(company_abbr):
    try:
        # Retrieve the company document based on the provided abbreviation
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")
        
        company_doc = frappe.get_doc('Company', company_name)

        # Fetch CSID directly
        csid = company_doc.custom_basic_auth_from_csid
        if not csid:
            frappe.throw("CSID for company {} not found".format(company_abbr))
        
        # Fetch compliance request ID directly
        request_id = company_doc.custom_compliance_request_id_
        if not request_id:
            frappe.throw("Compliance request ID for company {} not found".format(company_abbr))
        
        # Create payload for the API request
        payload = {
            "compliance_request_id": request_id
        }
        
        headers = {
            'accept': 'application/json',
            'Accept-Version': 'V2',
            'Authorization': 'Basic ' + csid,
            'Content-Type': 'application/json'
        }
        
        # Make the API request
        
        frappe.publish_realtime('show_gif', {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"})  
        
        response = requests.post(url=get_API_url(company_abbr, base_url="production/csids"), headers=headers, json=payload)
        frappe.publish_realtime('hide_gif')
        frappe.msgprint(response.text)
        
        
        if response.status_code != 200:
            frappe.throw("Error in production: " + response.text)
        
        data = response.json()
        concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
        encoded_value = base64.b64encode(concatenated_value.encode()).decode()

        # Update certificate data directly
        company_doc.custom_certificate = base64.b64decode(data["binarySecurityToken"]).decode('utf-8')
        
        # Update basic auth production data directly
        company_doc.custom_basic_auth_from_production = encoded_value
        
        company_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.throw("Error in production CSID formation: " + str(e))



def get_Reporting_Status(result):
    try:
        # Assume the response content is plain text or some other format
        reporting_status = result.text.strip()  # Strip any leading/trailing whitespace
        print("reportingStatus: " + reporting_status)
        return reporting_status
    except Exception as e:
        print(e)




def success_Log(response,uuid1,invoice_number):
                    try:
                        current_time = frappe.utils.now()
                        frappe.get_doc({
                            "doctype": "Zatca ERPgulf Success Log",
                            "title": "Zatca invoice call done successfully",
                            "message": "This message by Zatca Compliance",
                            "uuid": uuid1,
                            "invoice_number": invoice_number,
                            "time": current_time,
                            "zatca_response": response  
                            
                        }).insert(ignore_permissions=True)
                    except Exception as e:
                        frappe.throw("Error in success log  " + str(e))

def error_Log():
                    try:
                        frappe.log_error(title='Zatca invoice call failed in clearance status',message=frappe.get_traceback())
                    except Exception as e:
                        frappe.throw("Error in error log  " + str(e))   


def attach_QR_Image(qrCodeB64, sales_invoice_doc):
    try:
        # Check if custom field exists; if not, create it
        if not hasattr(sales_invoice_doc, "ksa_einv_qr"):
            create_custom_fields(
                {
                    sales_invoice_doc.doctype: [
                        {
                            "fieldname": "ksa_einv_qr",
                            "label": "KSA E-Invoicing QR",
                            "fieldtype": "Attach Image",
                            "read_only": 1,
                            "no_copy": 1,
                            "hidden": 0,  # Set hidden to 0 for testing
                        }
                    ]
                }
            )
            frappe.log("Custom field 'ksa_einv_qr' created.")

        # Check if the QR code already exists
        qr_code = sales_invoice_doc.get("ksa_einv_qr")
        if qr_code and frappe.db.exists({"doctype": "File", "file_url": qr_code}):
            return

        # Generate QR code image and save it
        qr_image = io.BytesIO()
        qr = qr_create(qrCodeB64, error="L")
        qr.png(qr_image, scale=8, quiet_zone=1)

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"QR_image_{sales_invoice_doc.name}.png".replace(os.path.sep, "__"),
            "attached_to_doctype": sales_invoice_doc.doctype,
            "attached_to_name": sales_invoice_doc.name,
            "is_private": 1,
            "content": qr_image.getvalue(),
            "attached_to_field": "ksa_einv_qr",
        })
        file_doc.save(ignore_permissions=True)

        # Link the file to the Sales Invoice
        sales_invoice_doc.db_set("ksa_einv_qr", file_doc.file_url)
        sales_invoice_doc.notify_update()

    except Exception as e:
        frappe.throw("Error in QR code generation: " + str(e))



def reporting_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc):
    try:
        # Retrieve the company abbreviation based on the company in the sales invoice
        company_abbr = frappe.db.get_value("Company", {"name": sales_invoice_doc.company}, "abbr")
        
        if not company_abbr:
            frappe.throw(f"Company with abbreviation {sales_invoice_doc.company} not found.")
        
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
            frappe.publish_realtime('show_gif', {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"})  
            response = requests.post(
                url=get_API_url(company_abbr, base_url="invoices/reporting/single"), 
                headers=headers, 
                json=payload
            )
            frappe.publish_realtime('hide_gif')
            if response.status_code in (400, 405, 406, 409):
                invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
                invoice_doc.db_set('custom_uuid', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_full_response', 'Not Submitted', commit=True, update_modified=True)
                frappe.throw(f"Error: The request you are sending to Zatca is in incorrect format. Please report to system administrator. Status code: {response.status_code}<br><br> {response.text}")
            
            if response.status_code in (401, 403, 407, 451):
                invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
                invoice_doc.db_set('custom_uuid', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_full_response', 'Not Submitted', commit=True, update_modified=True)
                frappe.throw(f"Error: Zatca Authentication failed. Your access token may be expired or not valid. Please contact your system administrator. Status code: {response.status_code}<br><br> {response.text}")
            
            if response.status_code not in (200, 202):
                invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
                invoice_doc.db_set('custom_uuid', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'Not Submitted', commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_full_response', 'Not Submitted', commit=True, update_modified=True)
                frappe.throw(f"Error: Zatca server busy or not responding. Try after sometime or contact your system administrator. Status code: {response.status_code}<br><br> {response.text}")
            
            if response.status_code in (200, 202):
                msg = "SUCCESS: <br><br>" if response.status_code == 200 else "REPORTED WITH WARNINGS: <br><br> Please copy the below message and send it to your system administrator to fix this warnings before next submission <br><br>"
                msg += f"Status Code: {response.status_code}<br><br> Zatca Response: {response.text}<br><br>"
                frappe.msgprint(msg)
                
                # Update PIH data without JSON formatting
                company_doc.custom_pih = encoded_hash
                company_doc.save(ignore_permissions=True)
                
                invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
                invoice_doc.db_set('custom_zatca_full_response', msg , commit=True, update_modified=True)
                invoice_doc.db_set('custom_uuid', uuid1, commit=True, update_modified=True)
                invoice_doc.db_set('custom_zatca_status', 'REPORTED', commit=True, update_modified=True)


                xml_base64 = xml_base64_Decode(signed_xmlfile_name)
                
                xml_cleared_data = base64.b64decode(xml_base64).decode('utf-8')
                # signed_xmlfile_name = frappe.local.site + '/private/files/final_xml_after_indent.xml'

                # Read the content of the XML file
                # with open(signed_xmlfile_name, 'r') as file:
                #     file_content = file.read()
                file = frappe.get_doc({
                    "doctype": "File",
                    "file_name": "Reported xml file " + sales_invoice_doc.name + ".xml" ,  
                    "attached_to_doctype": sales_invoice_doc.doctype,
                     "is_private": 1,
                    "attached_to_name": sales_invoice_doc.name,
                    "content":  xml_cleared_data
                })

                file.save(ignore_permissions=True)

                success_Log(response.text, uuid1, invoice_number)
            else:
                error_Log()
        except Exception as e:
            frappe.throw(f"Error in reporting API-2: {str(e)}")
    
    except Exception as e:
        invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
        invoice_doc.db_set('custom_zatca_full_response', f"Error: {str(e)}", commit=True, update_modified=True)
        frappe.throw(f"Error in reporting API-1: {str(e)}")


def clearance_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc):
    try:
        # Retrieve the company name based on the abbreviation in the Sales Invoice
        company_abbr = frappe.db.get_value("Company", {"name": sales_invoice_doc.company}, "abbr")
        if not company_abbr:
            frappe.throw(f"There is a problem with company name in invoice  {sales_invoice_doc.company} not found.")
       
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

        frappe.publish_realtime('show_gif', {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"})        
        response = requests.post(
            url=get_API_url(company_abbr, base_url="invoices/clearance/single"), 
            headers=headers, 
            json=payload
        )
        frappe.publish_realtime('hide_gif')

        if response.status_code in (400, 405, 406, 409):
            invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
            invoice_doc.db_set('custom_uuid', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_full_response', "Not Submitted")
            frappe.throw(f"Error: The request you are sending to Zatca is in incorrect format. Status code: {response.status_code}<br><br>{response.text}")

        if response.status_code in (401, 403, 407, 451):
            invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
            invoice_doc.db_set('custom_uuid', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_full_response', "Not Submitted")
            frappe.throw(f"Error: Zatca Authentication failed. Status code: {response.status_code}<br><br>{response.text}")

        if response.status_code not in (200, 202):
            invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
            invoice_doc.db_set('custom_uuid', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "Not Submitted", commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_full_response', "Not Submitted")
            frappe.throw(f"Error: Zatca server busy or not responding. Status code: {response.status_code}")

        if response.status_code in (200, 202):
            msg = "CLEARED WITH WARNINGS: <br><br>" if response.status_code == 202 else "SUCCESS: <br><br>"
            msg += f"Status Code: {response.status_code}<br><br>Zatca Response: {response.text}<br><br>"
            frappe.msgprint(msg)

            # Update PIH in the Company doctype without JSON formatting
            company_doc.custom_pih = encoded_hash
            company_doc.save(ignore_permissions=True)

            # Update the Sales Invoice with the UUID and status
            invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
            invoice_doc.db_set('custom_zatca_full_response', msg, commit=True, update_modified=True)
            invoice_doc.db_set('custom_uuid', uuid1, commit=True, update_modified=True)
            invoice_doc.db_set('custom_zatca_status', "CLEARED", commit=True, update_modified=True)

            data = response.json()
            base64_xml = data.get("clearedInvoice")
            xml_cleared = base64.b64decode(base64_xml).decode('utf-8')

            # Attach the cleared XML to the Sales Invoice
            file = frappe.get_doc({
                "doctype": "File",
                "file_name": "Cleared xml file " + sales_invoice_doc.name + ".xml",
                "attached_to_doctype": sales_invoice_doc.doctype,
                 "is_private": 1,
                "attached_to_name": sales_invoice_doc.name,
                "content": xml_cleared
            })
            file.save(ignore_permissions=True)
            sales_invoice_doc.db_set("custom_ksa_einvoicing_xml", file.file_url)
            success_Log(response.text, uuid1, invoice_number)
            return xml_cleared
        else:
            error_Log()

    except Exception as e:
        invoice_doc = frappe.get_doc('Sales Invoice', invoice_number)
        invoice_doc.db_set('custom_zatca_full_response', f"Error: {str(e)}", commit=True, update_modified=True)
        invoice_doc.db_set('custom_zatca_status', "503 Service Unavailable", commit=True, update_modified=True)
        
        # Raise the exception after saving the error message
        frappe.throw(f"Error in clearance API: {str(e)}")





@frappe.whitelist(allow_guest=True)
def zatca_Call(invoice_number, compliance_type="0", any_item_has_tax_template=False, company_abbr=None):
    try:
        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw("Invoice Number is NOT Valid: " + str(invoice_number))

        invoice = xml_tags()
        invoice, uuid1, sales_invoice_doc = salesinvoice_data(invoice, invoice_number)

        # Get the company abbreviation
        company_abbr = frappe.db.get_value("Company", {"name": sales_invoice_doc.company}, "abbr")

        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)

        if compliance_type == "0":
            if customer_doc.custom_b2c == 1:
                invoice = invoice_Typecode_Simplified(invoice, sales_invoice_doc)
            else:
                invoice = invoice_Typecode_Standard(invoice, sales_invoice_doc)
        else:
            invoice = invoice_Typecode_Compliance(invoice, compliance_type)

        invoice = doc_Reference(invoice, sales_invoice_doc, invoice_number)
        invoice = additional_Reference(invoice, company_abbr)
        invoice = company_Data(invoice, sales_invoice_doc)
        invoice = customer_Data(invoice, sales_invoice_doc)
        invoice = delivery_And_PaymentMeans(invoice, sales_invoice_doc, sales_invoice_doc.is_return)
        # if not any_item_has_tax_template:
        #     invoice = add_document_level_discount_with_tax(invoice, sales_invoice_doc)
        # else:
        #     invoice = add_document_level_discount_with_tax_template(invoice, sales_invoice_doc)

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            # Add document-level discount with tax
            invoice = add_nominal_discount_tax(invoice, sales_invoice_doc)
            
        elif not any_item_has_tax_template:
            # Add nominal discount tax
             invoice = add_document_level_discount_with_tax(invoice, sales_invoice_doc)
        else:
            # Add document-level discount with tax template
            invoice = add_document_level_discount_with_tax_template(invoice, sales_invoice_doc)

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            if not any_item_has_tax_template:
                invoice = tax_Data_nominal(invoice, sales_invoice_doc)
            else:
                invoice = tax_Data_with_template_nominal(invoice, sales_invoice_doc)
        else:
            if not any_item_has_tax_template:
                invoice = tax_Data(invoice, sales_invoice_doc)
            else:
                invoice = tax_Data_with_template(invoice, sales_invoice_doc)


        if not any_item_has_tax_template:
            invoice = item_data(invoice, sales_invoice_doc)
            
        else:
            invoice = item_data_with_template(invoice, sales_invoice_doc)
            

        pretty_xml_string = xml_structuring(invoice, sales_invoice_doc)

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
                reporting_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc)
                attach_QR_Image(qrCodeB64, sales_invoice_doc)
            else:
                xml_cleared = clearance_API(uuid1, encoded_hash, signed_xmlfile_name, invoice_number, sales_invoice_doc)
                attach_QR_Image(qrCodeB64, sales_invoice_doc)
        else:
            compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name, company_abbr)
            attach_QR_Image(qrCodeB64, sales_invoice_doc)

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
        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw("Invoice Number is NOT Valid: " + str(invoice_number))
          
        # Fetch and process the sales invoice data
        invoice = xml_tags()
        invoice, uuid1, sales_invoice_doc = salesinvoice_data(invoice, invoice_number)
           

        # Check if any item has a tax template and validate it
        any_item_has_tax_template = any(item.item_tax_template for item in sales_invoice_doc.items)
        if any_item_has_tax_template and not all(item.item_tax_template for item in sales_invoice_doc.items):
            frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")

        # Process the invoice based on the compliance type
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
        invoice = invoice_Typecode_Compliance(invoice, compliance_type)
        invoice = doc_Reference_compliance(invoice, sales_invoice_doc, invoice_number, compliance_type)
        invoice = additional_Reference(invoice,company_abbr)
        invoice = company_Data(invoice, sales_invoice_doc)
        invoice = customer_Data(invoice, sales_invoice_doc)
        invoice = delivery_And_PaymentMeans_for_Compliance(invoice, sales_invoice_doc, compliance_type)
        # if not any_item_has_tax_template:
        #     invoice = add_document_level_discount_with_tax(invoice, sales_invoice_doc)
        # else:
        #     invoice = add_document_level_discount_with_tax_template(invoice, sales_invoice_doc)

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            # Add document-level discount with tax
            invoice = add_nominal_discount_tax(invoice, sales_invoice_doc)
            
        elif not any_item_has_tax_template:
            # Add nominal discount tax
             invoice = add_document_level_discount_with_tax(invoice, sales_invoice_doc)
        else:
            # Add document-level discount with tax template
            invoice = add_document_level_discount_with_tax_template(invoice, sales_invoice_doc)

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1:
            if not any_item_has_tax_template:
                invoice = tax_Data_nominal(invoice, sales_invoice_doc)
            else:
                invoice = tax_Data_with_template_nominal(invoice, sales_invoice_doc)
        else:
            if not any_item_has_tax_template:
                invoice = tax_Data(invoice, sales_invoice_doc)
            else:
                invoice = tax_Data_with_template(invoice, sales_invoice_doc)


        if not any_item_has_tax_template:
            invoice = item_data(invoice, sales_invoice_doc)
            
        else:
            item_data_with_template(invoice, sales_invoice_doc)
            
              

        # Generate and process the XML data
        pretty_xml_string = xml_structuring(invoice, sales_invoice_doc)
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
def zatca_Background(invoice_number):
    try:
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)
        company_name = sales_invoice_doc.company

        # Retrieve the company document to access settings
        settings = frappe.get_doc('Company', company_name)
        company_abbr = settings.abbr
        


        if sales_invoice_doc.taxes and sales_invoice_doc.taxes[0].included_in_print_rate == 1:
            if any(item.item_tax_template for item in sales_invoice_doc.items):
                frappe.throw("Item Tax Template cannot be used when taxes are included in the print rate. Please remove Item Tax Templates.")

        any_item_has_tax_template = any(item.item_tax_template for item in sales_invoice_doc.items)

        
        if any_item_has_tax_template and not all(item.item_tax_template for item in sales_invoice_doc.items):
            frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")
        tax_categories = set()
        for item in sales_invoice_doc.items:
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
        base_discount_amount = sales_invoice_doc.get('base_discount_amount', 0.0)      
        if sales_invoice_doc.custom_zatca_nominal_invoice == 1 and sales_invoice_doc.get('base_discount_amount', 0.0) < 0:
            frappe.throw("only the document level discount is possible for ZATCA nominal invoices. Please ensure the discount is applied correctly.")

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1 and sales_invoice_doc.get('additional_discount_percentage', 0.0) != 100:
            frappe.throw("Only a 100% discount is allowed for ZATCA nominal invoices. Please ensure the additional discount percentage is set to 100.")

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1 and sales_invoice_doc.get('custom_submit_line_item_discount_to_zatca'):
            frappe.throw("For nominal invoices, please disable line item discounts by unchecking 'Submit Line Item Discount to ZATCA'.")



        if len(tax_categories) > 1 and base_discount_amount>0:
            frappe.throw("ZATCA does not respond for multiple items with multiple tax categories with doc-level discount. Please ensure all items have the same tax category.")
        if base_discount_amount > 0 and sales_invoice_doc.apply_discount_on != "Net Total":
            frappe.throw("You cannot put discount on Grand total as the tax is already calculated. Please make sure your discount is in Net total field.")

        if base_discount_amount < 0 and sales_invoice_doc.is_return==0:
            frappe.throw("Additional discount cannot be negative. Please enter a positive value.")

        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw("Please save and submit the invoice before sending to Zatca: " + str(invoice_number))

        if sales_invoice_doc.docstatus in [0, 2]:
            frappe.throw("Please submit the invoice before sending to Zatca: " + str(invoice_number))

        if sales_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw("Already submitted to Zakat and Tax Authority")

        if settings.custom_zatca_invoice_enabled != 1:
            frappe.throw("Zatca Invoice is not enabled in Company Settings, Please contact your system administrator")
        if settings.custom_phase_1_or_2 == "Phase-2":
            zatca_Call(invoice_number, "0", any_item_has_tax_template, company_abbr)
        else:
            create_qr_code(sales_invoice_doc,method=None)

    except Exception as e:
        frappe.throw("Error in background call: " + str(e))




# @frappe.whitelist(allow_guest=True)
# def zatca_Background_on_submit(doc, method=None):
#     try:
#         sales_invoice_doc = doc
#         invoice_number = sales_invoice_doc.name

#         # Ensure the Sales Invoice document is correctly loaded
#         sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)

#         # Retrieve the company abbreviation using the company name from the Sales Invoice
#         company_abbr = frappe.db.get_value("Company", {"name": sales_invoice_doc.company}, "abbr")
#         if not company_abbr:
#             frappe.throw(f"Company abbreviation for {sales_invoice_doc.company} not found.")
        
#         any_item_has_tax_template = False

#         for item in sales_invoice_doc.items:
#             if item.item_tax_template:
#                 any_item_has_tax_template = True
#                 break
        
#         if any_item_has_tax_template:
#             for item in sales_invoice_doc.items:
#                 if not item.item_tax_template:
#                     frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")
#         tax_categories = set()
#         for item in sales_invoice_doc.items:
#             if item.item_tax_template:
#                 item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
#                 zatca_tax_category = item_tax_template.custom_zatca_tax_category
#                 tax_categories.add(zatca_tax_category)
#                 for tax in item_tax_template.taxes:
#                     tax_rate = float(tax.tax_rate)
                    
#                     if f"{tax_rate:.2f}" not in ['5.00', '15.00'] and zatca_tax_category not in ["Zero Rated", "Exempted", "Services outside scope of tax / Not subject to VAT"]:
#                         frappe.throw("Zatca tax category should be 'Zero Rated', 'Exempted' or 'Services outside scope of tax / Not subject to VAT' for items with tax rate not equal to 5.00 or 15.00.")
                    
#                     if f"{tax_rate:.2f}" == '15.00' and zatca_tax_category != "Standard":
#                         frappe.throw("Check the Zatca category code and enable it as standard.")
#         base_discount_amount = sales_invoice_doc.get('base_discount_amount', 0.0)                  
#         if len(tax_categories) > 1 and base_discount_amount >0:
#             frappe.throw("ZATCA does not respond for multiple items with multiple tax categories with doc level discount. Please ensure all items have the same tax category.")
    
#         if base_discount_amount > 0 and sales_invoice_doc.apply_discount_on != "Net Total":
#             frappe.throw("You cannot put discount on Grand total as the tax is already calculated. Please make sure your discount is in Net total field.")
        
        
#         if not frappe.db.exists("Sales Invoice", invoice_number):
#             frappe.throw("Please save and submit the invoice before sending to Zatca:  " + str(invoice_number))
#         if base_discount_amount < 0 and sales_invoice_doc.is_return==0:
#             frappe.throw("Additional discount cannot be negative. Please enter a positive value.")
    
#         if sales_invoice_doc.docstatus in [0, 2]:
#             frappe.throw("Please submit the invoice before sending to Zatca:  " + str(invoice_number))
            
#         if sales_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
#             frappe.throw("Already submitted to Zakat and Tax Authority")
        
    
#         zatca_Call(invoice_number, "0", any_item_has_tax_template, company_abbr)
        
#     except Exception as e:
#         frappe.throw("Error in background call: " + str(e))
@frappe.whitelist(allow_guest=True)
def zatca_Background_on_submit(doc, method=None):
    try:
        sales_invoice_doc = doc
        invoice_number = sales_invoice_doc.name

        # Ensure the Sales Invoice document is correctly loaded
        sales_invoice_doc = frappe.get_doc("Sales Invoice", invoice_number)

        # Retrieve the company abbreviation using the company name from the Sales Invoice
        company_abbr = frappe.db.get_value("Company", {"name": sales_invoice_doc.company}, "abbr")
        if not company_abbr:
            frappe.throw(f"Company abbreviation for {sales_invoice_doc.company} not found.")

        # Retrieve the company document
        company_doc = frappe.get_doc('Company', {"abbr": company_abbr})
        
        # Check if ZATCA invoicing is enabled; if not, submit the doc and exit
        if company_doc.custom_zatca_invoice_enabled != 1:
            # frappe.msgprint("Zatca Invoice is not enabled. Submitting the document.")
            return  # Exit the function without further checks




        if sales_invoice_doc.taxes and sales_invoice_doc.taxes[0].included_in_print_rate == 1:
            if any(item.item_tax_template for item in sales_invoice_doc.items):
                frappe.throw("Item Tax Template cannot be used when taxes are included in the print rate. Please remove Item Tax Templates.")
        any_item_has_tax_template = False

        # Check if any item has a tax template
        for item in sales_invoice_doc.items:
            if item.item_tax_template:
                any_item_has_tax_template = True
                break

        # If one item has a tax template, all items must have a tax template
        if any_item_has_tax_template:
            for item in sales_invoice_doc.items:
                if not item.item_tax_template:
                    frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")

        tax_categories = set()
        
        # Collect and validate tax categories from item tax templates
        for item in sales_invoice_doc.items:
            if item.item_tax_template:
                item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                tax_categories.add(zatca_tax_category)
                for tax in item_tax_template.taxes:
                    tax_rate = float(tax.tax_rate)

                    if f"{tax_rate:.2f}" not in ['5.00', '15.00'] and zatca_tax_category not in [
                        "Zero Rated", "Exempted", "Services outside scope of tax / Not subject to VAT"
                    ]:
                        frappe.throw(
                            "Zatca tax category should be 'Zero Rated', 'Exempted', or "
                            "'Services outside scope of tax / Not subject to VAT' for items with tax rate not equal to 5.00 or 15.00."
                        )

                    if f"{tax_rate:.2f}" == '15.00' and zatca_tax_category != "Standard":
                        frappe.throw("Check the Zatca category code and enable it as Standard.")

        base_discount_amount = sales_invoice_doc.get('base_discount_amount', 0.0)
        if sales_invoice_doc.custom_zatca_nominal_invoice == 1 and sales_invoice_doc.get('base_discount_amount', 0.0) < 0:
            frappe.throw("only the document level discount is possible for ZATCA nominal invoices. Please ensure the discount is applied correctly.")

        if sales_invoice_doc.custom_zatca_nominal_invoice == 1 and sales_invoice_doc.get('additional_discount_percentage', 0.0) != 100:
            frappe.throw("Only a 100% discount is allowed for ZATCA nominal invoices. Please ensure the additional discount percentage is set to 100.")
        
        if sales_invoice_doc.custom_zatca_nominal_invoice == 1 and sales_invoice_doc.get('custom_submit_line_item_discount_to_zatca'):
            frappe.throw("For nominal invoices, please disable line item discounts by unchecking 'Submit Line Item Discount to ZATCA'.")

        # Ensure ZATCA compliance for discounts and tax categories

        if len(tax_categories) > 1 and base_discount_amount > 0:
            frappe.throw(
                "ZATCA does not respond for multiple items with multiple tax categories "
                "and a document-level discount. Please ensure all items have the same tax category."
            )

        if base_discount_amount > 0 and sales_invoice_doc.apply_discount_on != "Net Total":
            frappe.throw(
                "You cannot apply a discount on the Grand Total as the tax is already calculated. "
                "Please apply your discount on the Net Total."
            )

        # Validate if the Sales Invoice exists in the database
        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.throw(f"Please save and submit the invoice before sending to ZATCA: {invoice_number}")

        # Check for negative discounts when the invoice is not a return
        if base_discount_amount < 0 and not sales_invoice_doc.is_return:
            frappe.throw("Additional discount cannot be negative. Please enter a positive value.")

        # Ensure the document is submitted before sending to ZATCA
        if sales_invoice_doc.docstatus in [0, 2]:
            frappe.throw(f"Please submit the invoice before sending to ZATCA: {invoice_number}")

        # Prevent duplicate submissions to ZATCA
        if sales_invoice_doc.custom_zatca_status in ["REPORTED", "CLEARED"]:
            frappe.throw("This invoice has already been submitted to Zakat and Tax Authority.")

        # Call the ZATCA submission function
        company_name = sales_invoice_doc.company

        # Retrieve the company document to access settings
        settings = frappe.get_doc('Company', company_name)
        if settings.custom_phase_1_or_2 == "Phase-2":
            zatca_Call(invoice_number, "0", any_item_has_tax_template, company_abbr)
        else:
            create_qr_code(sales_invoice_doc,method=None)

    except Exception as e:
        frappe.throw(f"Error in background call: {str(e)}")
