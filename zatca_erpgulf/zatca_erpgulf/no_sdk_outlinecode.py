from lxml import etree
import hashlib
import base64 
import lxml.etree as MyTree
from datetime import datetime
import xml.etree.ElementTree as ET
import frappe
from hashlib import sha256
from base64 import b64encode
import pyqrcode
# frappe.init(site="prod.erpgulf.com")
# frappe.connect()
from zatca2024.zatca2024.createxml import xml_tags,salesinvoice_data,invoice_Typecode_Simplified,invoice_Typecode_Standard,doc_Reference,additional_Reference ,company_Data,customer_Data,delivery_And_PaymentMeans,tax_Data,item_data,xml_structuring,invoice_Typecode_Compliance,delivery_And_PaymentMeans_for_Compliance,doc_Reference_compliance,get_tax_total_from_items
from zatca2024.zatca2024.compliance import get_pwd,set_cert_path,create_compliance_x509,check_compliance
import binascii
from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.bindings._rust import ObjectIdentifier
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from zatca2024.zatca2024.createxml import xml_tags,salesinvoice_data,invoice_Typecode_Simplified,invoice_Typecode_Standard,doc_Reference,additional_Reference ,company_Data,customer_Data,delivery_And_PaymentMeans,tax_Data,item_data,xml_structuring,invoice_Typecode_Compliance,delivery_And_PaymentMeans_for_Compliance,doc_Reference_compliance,get_tax_total_from_items
import json
import requests
from cryptography.hazmat.primitives import serialization

def get_csr_data():
    # Read the properties file
            with open('sdkcsrconfig.properties', 'r') as file:
                lines = [line.strip() for line in file.readlines()]

            # Initialize variables
            csr_common_name = None
            csr_serial_number = None
            csr_organization_identifier = None
            csr_organization_unit_name = None
            csr_organization_name = None
            csr_country_name = None
            csr_invoice_type = None
            csr_location_address = None
            csr_industry_business_category = None

            # Process each line to extract key-value pairs
            for line in lines:
                parts = line.split('=')
                if len(parts) == 2:
                    key, value = parts
                    if key == 'csr.common.name':
                        csr_common_name = value
                    elif key == 'csr.serial.number':
                        csr_serial_number = value
                    elif key == 'csr.organization.identifier':
                        csr_organization_identifier = value
                    elif key == 'csr.organization.unit.name':
                        csr_organization_unit_name = value
                    elif key == 'csr.organization.name':
                        csr_organization_name = value
                    elif key == 'csr.country.name':
                        csr_country_name = value
                    elif key == 'csr.invoice.type':
                        csr_invoice_type = value
                    elif key == 'csr.location.address':
                        csr_location_address = value
                    elif key == 'csr.industry.business.category':
                        csr_industry_business_category = value

            return csr_common_name,csr_serial_number,csr_organization_identifier,csr_organization_unit_name,csr_organization_name,csr_country_name,csr_invoice_type,csr_location_address,csr_industry_business_category


def create_private_keys():
    private_key = ec.generate_private_key(ec.SECP256K1(), backend=default_backend())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    # print(private_key_pem)
    return private_key_pem

private_key_pem = create_private_keys()

def create_csr(portal_type):
    
        csr_common_name,csr_serial_number,csr_organization_identifier,csr_organization_unit_name,csr_organization_name,csr_country_name,csr_invoice_type,csr_location_address,csr_industry_business_category = get_csr_data()
        if portal_type == "sandbox":
            customoid = b"..TESTZATCA-Code-Signing"
        elif portal_type == "simulation":
            customoid = b"..PREZATCA-Code-Signing"
        else:
            customoid = b"..ZATCA-Code-Signing"

        private_key_pem = create_private_keys()
        private_key = serialization.load_pem_private_key(private_key_pem, password=None, backend=default_backend())
        
        custom_oid_string = "2.5.9.3.7.1.982.20.2"
        custom_value = customoid
        oid = ObjectIdentifier(custom_oid_string)
        custom_extension = x509.extensions.UnrecognizedExtension(oid, custom_value)
        
        dn = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, csr_common_name),  # csr.common.name
            x509.NameAttribute(NameOID.COUNTRY_NAME, csr_country_name),   # csr.country.name -  has to be two digits 
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, csr_organization_name),   # csr.organization.name
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, csr_organization_unit_name), # csr.organization.unit.name
        ])
        alt_name = x509.SubjectAlternativeName({
            x509.DirectoryName(x509.Name([
                x509.NameAttribute(NameOID.SURNAME, csr_serial_number),   # csr.serial.number-- has to be this format 
                x509.NameAttribute(NameOID.USER_ID, csr_organization_identifier),   # csr.organization.identifier - has to be 13 digit with starting and ending digit 3  
                x509.NameAttribute(NameOID.TITLE, csr_invoice_type),  # csr.invoice.type - has to be 1100
                x509.NameAttribute(NameOID.BUSINESS_CATEGORY, csr_industry_business_category + "/registeredAddress=" + csr_location_address),   # csr.location.address
            ])),
        })

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
        return encoded_string

csr_string = create_csr("sandbox")
# print(csr_string)
# get_csr_data()
# print(privatekey)
# with open('new_csr.csr', 'w') as file:
#     file.write(csr_string)
with open('new_private.pem', 'w') as file:
    file.write(private_key_pem.decode('utf-8'))
# print(csr_string)
# # with open('new_public.pem', 'w') as file:
# #     file.write(public_key_pem.decode('utf-8'))
# with open('new_public.pem', 'wb') as f:
#       f.write(public_key_pem)

def create_csid():
    url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/compliance"
    payload = json.dumps({
    "csr": csr_string
    })
    headers = {
    'accept': 'application/json',
    'OTP': '123345',
    'Accept-Version': 'V2',
    'Content-Type': 'application/json',
    'Cookie': 'TS0106293e=0132a679c07400f36242c054cc5c73a634f51486563baa5cc4d51293c0b38f68d10c82161b3074b1b2dfbe83a1ae5b78f2fd256699'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    # print(response.text)
    print("----------------------------------------------------------------------------------------------------------")
    data=json.loads(response.text)

                    # compliance_cert =get_auth_headers(data["binarySecurityToken"],data["secret"])
    concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
    # print("the val is",concatenated_value)
    encoded_value = base64.b64encode(concatenated_value.encode()).decode()
    requestid=data["requestID"]
    with open(f"certficatejavaaa.pem", 'w') as file:   
        file.write(base64.b64decode(data["binarySecurityToken"]).decode())
    return encoded_value,requestid

encoded_value_csid,requestid=create_csid()
# print("the orginal encoded csid is",encoded_value_csid)


def create_public_key():
     with open("certficatejavaaa.pem", 'r') as file:
                base_64= file.read()
                cert_base64 = """
                -----BEGIN CERTIFICATE-----
                {base_64}
                -----END CERTIFICATE-----
                """.format(base_64=base_64)
                # print(cert_base64)
                cert = x509.load_pem_x509_certificate(cert_base64.encode(), default_backend())
                public_key = cert.public_key()
                public_key_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
                # print("Public Key ",public_key_pem)  #  
                # print("            ")
                with open('new_public.pem', 'wb') as f:
                     f.write(public_key_pem)



def removeTags(finalzatcaxml):
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
        # print(transformed_xml)
        return transformed_xml
        

def canonicalize_xml (tag_removed_xml):
            #Code corrected by Farook K - ERPGulf
            canonical_xml = etree.tostring(tag_removed_xml, method="c14n").decode()
            # print(canonical_xml)
            return canonical_xml        

def getInvoiceHash(canonicalized_xml):
            #Code corrected by Farook K - ERPGulf
            hash_object = hashlib.sha256(canonicalized_xml.encode())
            hash_hex = hash_object.hexdigest()
            # print(hash_hex)
            hash_base64 = base64.b64encode(bytes.fromhex(hash_hex)).decode('utf-8')
            # base64_encoded = base64.b64encode(hash_hex.encode()).decode()
            return hash_hex,hash_base64
    
    
    
def digital_signature():
        with open("new_private.pem", "rb") as key_file:
                hash_bytes = bytes.fromhex(hash)
                print(hash)
                private_key = serialization.load_pem_private_key(key_file.read(), password=None, backend=default_backend())
                signature = private_key.sign(hash_bytes, ec.ECDSA(hashes.SHA256()))
                # print(signature)
                encoded_signature = base64.b64encode(signature).decode()
                # print(encoded_signature)
                return encoded_signature

# digital_signature()

def extract_certificate_details():
            with open("certficatejavaaa.pem", 'r') as file:
                certificate_content = file.read()
                cert_path = 'certificatejavaa2.pem'
                with open(cert_path, "w") as file:
                    file.write("-----BEGIN CERTIFICATE-----\n")
                    file.write("\n".join(certificate_content[i:i+64] for i in range(0, len(certificate_content), 64)))
                    file.write("\n-----END CERTIFICATE-----\n")
                with open("certificatejavaa2.pem", 'rb') as cert_file:
                    pem_data = cert_file.read()
                cert = x509.load_pem_x509_certificate(pem_data, default_backend())
                formatted_issuer_name = cert.issuer.rfc4514_string()
                issuer_name = ", ".join([x.strip() for x in formatted_issuer_name.split(',')])
                serial_number = cert.serial_number
                return issuer_name, serial_number


def certificate_hash():
                with open('certficatejavaaa.pem', 'rb') as f:
                    certificate_data = f.read().decode('utf-8')
                    # print(certificate_data)
                certificate_data_bytes = certificate_data.encode('utf-8')
                sha256_hash = hashlib.sha256(certificate_data_bytes).hexdigest()
                # print(sha256_hash)
                base64_encoded_hash = base64.b64encode(sha256_hash.encode('utf-8')).decode('utf-8')
                # print(base64_encoded_hash)
                return base64_encoded_hash


def signxml_modify():
            encoded_certificate_hash= certificate_hash()
            issuer_name, serial_number = extract_certificate_details()
            original_invoice_xml = etree.parse('finalzatcaxml.xml')
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
            with open("after_step_4.xml", 'wb') as file:
                original_invoice_xml.write(file,encoding='utf-8',xml_declaration=True,)
            return namespaces ,signing_time


def generate_Signed_Properties_Hash(namespaces,signing_time,issuer_name,serial_number,encoded_certificate_hash):
        
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
                # print(xml_string_rendered)
                utf8_bytes = xml_string_rendered.encode('utf-8')
                hash_object = hashlib.sha256(utf8_bytes)
                hex_sha256 = hash_object.hexdigest()
                # print(hex_sha256)
                signed_properties_base64=  base64.b64encode(hex_sha256.encode('utf-8')).decode('utf-8')
                # print(signed_properties_base64)
                return signed_properties_base64


def populate_The_UBL_Extensions_Output(encoded_signature):
            updated_invoice_xml = etree.parse('after_step_4.xml')
            root3 = updated_invoice_xml.getroot()
            with open("certficatejavaaa.pem", "r") as file:
              content = file.read()
            xpath_signvalue = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignatureValue")
            xpath_x509certi = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:KeyInfo/ds:X509Data/ds:X509Certificate")
            xpath_digvalue = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@URI='#xadesSignedProperties']/ds:DigestValue")
            xpath_digvalue2 = ("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@Id='invoiceSignedData']/ds:DigestValue")
            signValue6 = root3.find(xpath_signvalue , namespaces)
            x509Certificate6 = root3.find(xpath_x509certi , namespaces)
            digestvalue6 = root3.find(xpath_digvalue , namespaces)
            digestvalue6_2 = root3.find(xpath_digvalue2 , namespaces)
            signValue6.text = (encoded_signature)
            x509Certificate6.text = content
            digestvalue6.text = (signed_properties_base64)
            digestvalue6_2.text =(encoded_hash)
            with open("final_xml_after_sign.xml", 'wb') as file:
                updated_invoice_xml.write(file,encoding='utf-8',xml_declaration=True,)


def extract_public_key_data():
                with open("new_public.pem", 'r') as file:
                    lines = file.readlines()
                    key_data = ''.join(lines[1:-1])  
                key_data = key_data.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '')
                key_data = key_data.replace(' ', '').replace('\n', '')
                return key_data

def get_tlv_for_value(tag_num, tag_value):
                    tag_num_buf = bytes([tag_num])
                    if isinstance(tag_value, str):
                        if len(tag_value) < 256:
                            tag_value_len_buf = bytes([len(tag_value)])
                        else:
                            tag_value_len_buf = bytes([0xFF, (len(tag_value) >> 8) & 0xFF, len(tag_value) & 0xFF])
                        tag_value = tag_value.encode('utf-8')
                    else:
                        tag_value_len_buf = bytes([len(tag_value)])
                    return tag_num_buf + tag_value_len_buf + tag_value


def tag8_publickey():
                        base64_encoded = extract_public_key_data() 
                        byte_data = base64.b64decode(base64_encoded)
                        hex_data = binascii.hexlify(byte_data).decode('utf-8')
                        chunks = [hex_data[i:i + 2] for i in range(0, len(hex_data), 2)]
                        value = ''.join(chunks)
                        binary_data = bytes.fromhex(value)
                        base64_encoded1 = base64.b64encode(binary_data).decode('utf-8')
                        return binary_data

def tag9_signature_ecdsa():
                with open('certificatejavaa2.pem', 'rb') as cert_file:
                    cert_data = cert_file.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                signature = cert.signature
                signature_hex = "".join("{:02x}".format(byte) for byte in signature)
                signature_bytes = bytes.fromhex(signature_hex)
                signature_base64 = base64.b64encode(signature_bytes).decode()
                # print(f"Signature Algorithm: {cert.signature_algorithm_oid._name}")
                # print(f"Signature Value (Hex): {signature_hex}")
                # print(f"Signature Value (Base64): {signature_base64}")
                return signature_bytes



def generate_tlv_xml():
                            with open("final_xml_after_sign.xml", 'rb') as file:
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
                                (9, None) ,
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
                            result_dict[8] = tag8_publickey()
                            result_dict[9] = tag9_signature_ecdsa()

                            return result_dict


def update_Qr_toXml():
                        xml_file_path = "final_xml_after_sign.xml"
                        xml_tree = etree.parse(xml_file_path)
                        qr_code_element = xml_tree.find('.//cac:AdditionalDocumentReference[cbc:ID="QR"]/cac:Attachment/cbc:EmbeddedDocumentBinaryObject', namespaces={'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2', 'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'})
                        if qr_code_element is not None:
                            qr_code_element.text =qrCodeB64
                        else:
                            print("QR code element not found")

                        xml_tree.write(xml_file_path, encoding="UTF-8", xml_declaration=True)

def structuring_signedxml():
                    with open('final_xml_after_sign.xml', 'r') as file:
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
                    with open('final_xml_after_indent.xml', 'w') as file:
                        file.writelines(adjusted_xml_content)
                        
def xml_base64_Decode(signed_xmlfile_name):
                    try:
                        with open(signed_xmlfile_name, "r") as file:
                                        xml = file.read().lstrip()
                                        base64_encoded = base64.b64encode(xml.encode("utf-8"))
                                        base64_decoded = base64_encoded.decode("utf-8")
                                        return base64_decoded
                    except Exception as e:
                        print("Error in xml base64:  " + str(e) )


def compliance_api_call():

        url = "https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/compliance/invoices"
        payload = json.dumps({
        "invoiceHash": encoded_hash,
        "uuid": "f3f49db4-0d44-11ef-8e6c-020017019f27",
        "invoice": xml_base64_Decode('final_xml_after_indent.xml')
        })
        # print(encoded_hash)
        # print(xml_base64_Decode('final_xml_after_sign.xml'))
      
        headers = {
        'accept': 'application/json',
        'Accept-Language': 'en',
        'Accept-Version': 'V2',
        'Authorization': 'Basic' + encoded_value_csid,
        'Content-Type': 'application/json',
        'Cookie': 'TS0106293e=0132a679c0b10cf6c29a653de982233d1a963a1c3d67ad649e41021b0a7b1825208bb7e7615f60058af4ed60330ae0c3dfb7f76f29'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        
        print(response.text)
        print("----------------------------------------------------------------------------------------------------------")


# def qr_img():
#         qr_value = qrCodeB64
#         qr = pyqrcode.create(qr_value)
#         temp_file_path = "qr_codeextag.png"
#         qr_image=qr.png(temp_file_path, scale=5)

# qr_img()

def production_CSID():    
                try:
                    payload = json.dumps({
                    "compliance_request_id":requestid})
                    # print("encoded csid is",encoded_value_csid)
                    headers = {
                    'accept': 'application/json',
                    'Accept-Version': 'V2',
                    'Authorization': 'Basic'+ encoded_value_csid,
                    'Content-Type': 'application/json' }
                    response = requests.request("POST", url="https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/production/csids", headers=headers, data=payload)
                    # print(response.text)
                    if response.status_code != 200:
                        print("Error: " + str(response.text))
                    data=json.loads(response.text)
                    concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
                    encoded_value = base64.b64encode(concatenated_value.encode()).decode()
                    with open(f"certficatejavaaa.pem", 'w') as file:   #attaching X509 certificate
                        file.write(base64.b64decode(data["binarySecurityToken"]).decode('utf-8'))
                    return encoded_value
                except Exception as e:
                    print("error in  production csid formation:  " + str(e) )
                    
encoded_value=production_CSID()
with open("finalzatcaxml.xml", 'r') as file:
        file_content = file.read()
        
tag_removed_xml = removeTags(file_content)
canonicalized_xml = canonicalize_xml(tag_removed_xml)
# # print(canonicalized_xml)
hash, encoded_hash = getInvoiceHash(canonicalized_xml)

# print(hash)
# print(encoded_hash)

encoded_signature=digital_signature()
issuer_name,serial_number =extract_certificate_details()
encoded_certificate_hash=certificate_hash()
namespaces,signing_time=signxml_modify()
signed_properties_base64=generate_Signed_Properties_Hash(namespaces,signing_time,issuer_name,serial_number,encoded_certificate_hash)
populate_The_UBL_Extensions_Output(encoded_signature)
create_public_key()
tlv_data = generate_tlv_xml()
tagsBufsArray = []
for tag_num, tag_value in tlv_data.items():
    tagsBufsArray.append(get_tlv_for_value(tag_num, tag_value))
qrCodeBuf = b"".join(tagsBufsArray)
# print(qrCodeBuf)
qrCodeB64 = base64.b64encode(qrCodeBuf).decode('utf-8')
# print(qrCodeB64)
update_Qr_toXml()
structuring_signedxml()
compliance_api_call()

def reporting_API():
                        payload = json.dumps({
                        "invoiceHash": encoded_hash,
                        "uuid": "f3f49db4-0d44-11ef-8e6c-020017019f27",
                        "invoice": xml_base64_Decode('final_xml_after_indent.xml'),
                        })
                        headers = {
                                'accept': 'application/json',
                                    'accept-language': 'en',
                                    'Clearance-Status': '0',
                                    'Accept-Version': 'V2',
                                     'Authorization': 'Basic' + encoded_value,
                                    'Content-Type': 'application/json',
                                    'Cookie': 'TS0106293e=0132a679c0639d13d069bcba831384623a2ca6da47fac8d91bef610c47c7119dcdd3b817f963ec301682dae864351c67ee3a402866'
                                    }    
                        response = requests.request("POST", url="https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/invoices/reporting/single", headers=headers, data=payload)
                        print(response.text)
                        print("----------------------------------------------------------------------------------------------------------")

reporting_API()


def clearance_API():
                  
                        payload = json.dumps({
                        "invoiceHash": encoded_hash,
                        "uuid": "d16798d6-0d09-11ef-8713-020017019f27",
                        "invoice": xml_base64_Decode('final_xml_after_indent.xml'), })
                        headers = {
                        'accept': 'application/json',
                        'accept-language': 'en',
                        'Clearance-Status': '1',
                        'Accept-Version': 'V2',
                        'Authorization': 'Basic' + encoded_value,
                        # 'Authorization': 'Basic' + settings.basic_auth,
                        
                        'Content-Type': 'application/json',
                        'Cookie': 'TS0106293e=0132a679c03c628e6c49de86c0f6bb76390abb4416868d6368d6d7c05da619c8326266f5bc262b7c0c65a6863cd3b19081d64eee99' }
                        response = requests.request("POST", url="https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/invoices/clearance/single", headers=headers, data=payload)
                        print(response.text)
# clearance_API()
