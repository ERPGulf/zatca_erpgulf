from lxml import etree
import hashlib
import base64 
import lxml.etree as MyTree
from datetime import datetime
import xml.etree.ElementTree as ET
import frappe
from zatca_erpgulf.zatca_erpgulf.createxml import xml_tags,salesinvoice_data,invoice_Typecode_Simplified,invoice_Typecode_Standard,doc_Reference,additional_Reference ,company_Data,customer_Data,delivery_And_PaymentMeans,tax_Data,item_data,xml_structuring,invoice_Typecode_Compliance,delivery_And_PaymentMeans_for_Compliance,doc_Reference_compliance,get_tax_total_from_items,tax_Data_with_template,item_data_with_template
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

def encode_customoid(custom_string):
    # Create an encoder
    encoder = asn1.Encoder()
    encoder.start()

    # Encode the string as an OCTET STRING
    encoder.write(custom_string, asn1.Numbers.UTF8String)

    # Get the encoded byte string
    return encoder.output()

def update_json_data_private_key(existing_data, company_name, private_key_pem):
                try:
                    private_key_str = private_key_pem.decode('utf-8')
                    
                    company_exists = False
                    for entry in existing_data["companies"]:
                        if entry["company"] == company_name:
                            entry["private_key_data"] = private_key_str
                            company_exists = True
                            break
                    if not company_exists:
                        existing_data["companies"].append({
                            "company": company_name,
                            "private_key_data": private_key_str
                        })
                    return existing_data
                except Exception as e:
                    frappe.throw("Error updating JSON data for private key: " + str(e))

def get_csr_data():
    try:
        settings = frappe.get_doc('Zatca ERPgulf Setting')
        csr_config = settings.csr_config
        if isinstance(csr_config, str):
            csr_config = json.loads(csr_config)
        csr_data = csr_config.get("data", [])
        if not csr_data:
            frappe.throw("No CSR data found in settings")
        csr_values = {}
        for item in csr_data:
            company = item.get("company")
            csr_values[company] = {
                "csr.common.name": item.get("csr_config", {}).get("csr.common.name"),
                "csr.serial.number": item.get("csr_config", {}).get("csr.serial.number"),
                "csr.organization.identifier": item.get("csr_config", {}).get("csr.organization.identifier"),
                "csr.organization.unit.name": item.get("csr_config", {}).get("csr.organization.unit.name"),
                "csr.organization.name": item.get("csr_config", {}).get("csr.organization.name"),
                "csr.country.name": item.get("csr_config", {}).get("csr.country.name"),
                "csr.invoice.type": item.get("csr_config", {}).get("csr.invoice.type"),
                "csr.location.address": item.get("csr_config", {}).get("csr.location.address"),
                "csr.industry.business.category": item.get("csr_config", {}).get("csr.industry.business.category"),
            }
        
        return csr_values
    except Exception as e:
        frappe.throw("Error in get csr data: " + str(e))

def create_private_keys():
            try:
                settings = frappe.get_doc('Zatca ERPgulf Setting')
                company = settings.company
                private_key = ec.generate_private_key(ec.SECP256K1(), backend=default_backend())
                private_key_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                )
                company_name = frappe.db.get_value("Company", company, "abbr")
                if not settings.private_key:
                    settings.private_key = {"companies": []}
                
                if isinstance(settings.private_key, str):
                    settings.private_key = json.loads(settings.private_key)
                
                updated_data = update_json_data_private_key(settings.private_key, company_name, private_key_pem)
                settings.private_key = json.dumps(updated_data)  
                settings.save(ignore_permissions=True)      
                return private_key_pem

            except Exception as e:
                    frappe.throw(" error in creating private key: "+ str(e) )

def update_json_data_csr(existing_data, company_name, csr_data):
            try:
                company_exists = False
                for entry in existing_data["companies"]:
                    if entry["company"] == company_name:
                        entry["csr"] = csr_data
                        company_exists = True
                        break
                if not company_exists:
                    existing_data["companies"].append({
                        "company": company_name,
                        "csr": csr_data
                    })
                return existing_data
            except Exception as e:
                frappe.throw("Error updating JSON data for CSR: " + str(e))

@frappe.whitelist(allow_guest=True)
def create_csr(portal_type):
    try:
        csr_values = get_csr_data()
        settings = frappe.get_doc('Zatca ERPgulf Setting')
        company = settings.company
        company_name = frappe.db.get_value("Company", company, "abbr")
        company_csr_data = csr_values.get(company_name, {})
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
            customoid = customoid = encode_customoid("TESTZATCA-Code-Signing")
        elif portal_type == "Simulation":
            customoid = customoid = encode_customoid("PREZATCA-Code-Signing")
        else:
            customoid = customoid = encode_customoid("ZATCA-Code-Signing")
        
        private_key_pem = create_private_keys()
        private_key = serialization.load_pem_private_key(private_key_pem, password=None, backend=default_backend())

        custom_oid_string = "1.3.6.1.4.1.311.20.2"
        custom_value = customoid 
        oid = ObjectIdentifier(custom_oid_string)
        OID_REGISTERED_ADDRESS = ObjectIdentifier("2.5.4.26")
        custom_extension = x509.extensions.UnrecognizedExtension(oid, custom_value) 
        dn = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, csr_country_name),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, csr_organization_unit_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, csr_organization_name),
            x509.NameAttribute(NameOID.COMMON_NAME, csr_common_name),
            
        ])
        alt_name = x509.SubjectAlternativeName({
            x509.DirectoryName(x509.Name([
                x509.NameAttribute(NameOID.SURNAME, csr_serial_number),
                x509.NameAttribute(NameOID.USER_ID, csr_organization_identifier),
                x509.NameAttribute(NameOID.TITLE, csr_invoice_type),
                x509.NameAttribute(OID_REGISTERED_ADDRESS, csr_location_address),
                x509.NameAttribute(NameOID.BUSINESS_CATEGORY, csr_industry_business_category)
                #+ "/registeredAddress=" + csr_location_address),
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

        settings = frappe.get_doc('Zatca ERPgulf Setting')
        company = settings.company
        company_name = frappe.db.get_value("Company", company, "abbr")
        if not settings.csr_data:
            settings.csr_data = {"companies": []}
        if isinstance(settings.csr_data, str):
            settings.csr_data = json.loads(settings.csr_data)
        updated_data = update_json_data_csr(settings.csr_data, company_name, encoded_string)
        settings.csr_data = json.dumps(updated_data)  
        settings.save(ignore_permissions=True)
        frappe.msgprint("CSR generation successful.CSR saved")
        
        return encoded_string
    
    except Exception as e:
        frappe.throw("Error in creating csr: " + str(e))

def get_API_url(base_url):
                try:
                    settings =  frappe.get_doc('Zatca ERPgulf Setting')
                    if settings.select == "Sandbox":
                        url = settings.sandbox_url + base_url
                    elif settings.select == "Simulation":
                        url = settings.simulation_url + base_url
                    else:
                        url = settings.production_url + base_url
                    return url 
                except Exception as e:
                    frappe.throw(" getting url failed"+ str(e) ) 

def update_json_data_csid(existing_data, company_name, csid):
                    try:
                        company_exists = False
                        for entry in existing_data["data"]:
                            if entry["company"] == company_name:
                                
                                entry["csid"] = csid
                                company_exists = True
                                break
                        if not company_exists:
                            existing_data["data"].append({
                                "company": company_name,
                                "csid": csid
                            })

                        return existing_data
                    except Exception as e:
                            frappe.throw("error json data of request id: " + str(e))

def update_json_data_request_id(existing_data, company_name, request_id):
                    try:
                        company_exists = False
                        for entry in existing_data["data"]:
                            if entry["company"] == company_name:
                                entry["request_id"] = request_id
                                company_exists = True
                                break
                        if not company_exists:
                            existing_data["data"].append({
                                "company": company_name,
                                "request_id": request_id
                            })

                        return existing_data
                    except Exception as e:
                                        frappe.throw("error json data of request id: " + str(e))
   
def update_json_data_production_csid(existing_data, company_name, production_csid):
                    try:
                        company_exists = False
                        for entry in existing_data["companies"]:
                            if entry["company"] == company_name:
                                entry["production_csid"] = production_csid
                                company_exists = True
                                break
                        if not company_exists:
                            existing_data["companies"].append({
                                "company": company_name,
                                "production_csid": production_csid
                            })
                        return existing_data
                    except Exception as e:
                                frappe.throw("error json data of production csid: " + str(e))

def get_csr_for_company(data, company_name):
                    try:
                        for entry in data.get("companies", []):
                            if entry.get("company") == company_name:
                                return entry.get("csr")
                        return None
                    except Exception as e:
                        frappe.throw("Error in getting CSR for company: " + str(e))

@frappe.whitelist(allow_guest=True)
def create_CSID():
            try:
                    settings = frappe.get_doc('Zatca ERPgulf Setting')
                    company = settings.company
                    company_name = frappe.db.get_value("Company", company, "abbr")
                    csr_data_str = settings.get("csr_data", "{}")
                    try:
                        csr_data = json.loads(csr_data_str)
                    except json.JSONDecodeError:
                        frappe.throw("CSR data field contains invalid JSON")
                    
                    csr_contents = get_csr_for_company(csr_data, company_name)
                    if not csr_contents:
                        frappe.throw(f"No CSR found for company {company_name}")
                    payload = json.dumps({
                    "csr": csr_contents
                    })
                    headers = {
                    'accept': 'application/json',
                    'OTP': settings.otp,
                    'Accept-Version': 'V2',
                    'Content-Type': 'application/json',
                    'Cookie': 'TS0106293e=0132a679c07382ce7821148af16b99da546c13ce1dcddbef0e19802eb470e539a4d39d5ef63d5c8280b48c529f321e8b0173890e4f'
                    }
                    
                    response = requests.request("POST", url=get_API_url(base_url="compliance"), headers=headers, data=payload)
                    # frappe.throw(response.text)
                    # frappe.throw(response.status_code)
                    if response.status_code == 400:
                        frappe.throw("Error: " + "OTP is not valid", response.text)
                    if response.status_code != 200:
                        frappe.throw("Error: " + "Error in Certificate or OTP: " + "<br> <br>" + response.text)
                    
                    frappe.msgprint(str(response.text))
                    
                    data=json.loads(response.text)
                    
                    concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
                    encoded_value = base64.b64encode(concatenated_value.encode()).decode()
                    if not settings.certificate:
                        settings.certificate = {"data": []}
                    
                    if isinstance(settings.certificate, str):
                        try:
                            settings.certificate = json.loads(settings.certificate)
                        except json.JSONDecodeError:
                            frappe.throw("certificate field contains invalid JSON")
                    
                    updated_certificate_data = update_json_data_certificate(
                        settings.certificate, 
                        company_name, 
                        base64.b64decode(data["binarySecurityToken"]).decode('utf-8')
                    )
                    settings.set("certificate", json.dumps(updated_certificate_data))
                    
                    settings.save(ignore_permissions=True)
                    basic_auth = settings.get("basic_auth", "{}")
                    # frappe.msgprint(basic_auth)
                    try:
                        basic_auth_data = json.loads(basic_auth)
                    except json.JSONDecodeError:
                        basic_auth_data = {"data": []}
                    except:
                        basic_auth_data = {"data": []}
                    updated_basic_auth_data = update_json_data_csid(basic_auth_data, company_name, encoded_value)
                    settings.set("basic_auth", json.dumps(updated_basic_auth_data))
                    compliance_request_id = settings.get("compliance_request_id", "{}")
                    try:
                        compliance_request_id_data = json.loads(compliance_request_id)
                        # Ensure that compliance_request_id_data is a dictionary with a "data" key.
                        if not isinstance(compliance_request_id_data, dict) or "data" not in compliance_request_id_data:
                            raise ValueError("Invalid format for compliance_request_id_data")
                    except (json.JSONDecodeError, ValueError):
                        compliance_request_id_data = {"data": []}
                    except:
                        compliance_request_id_data = {"data": []}
                    updated_compliance_request_id_data = update_json_data_request_id(compliance_request_id_data, company_name, data["requestID"])
                    settings.set("compliance_request_id", json.dumps(updated_compliance_request_id_data))
                    settings.save(ignore_permissions=True)
                
            except Exception as e:
                    frappe.throw(" error in creating CSID: "+ str(e) )

def update_json_data_public_key(existing_data, company_name, public_key):
                try:
                    if "data" not in existing_data:
                        existing_data["data"] = []

                    company_exists = False
                    for entry in existing_data["data"]:
                        if entry["company"] == company_name:
                            entry["public_key_data"] = public_key
                            company_exists = True
                            break
                    if not company_exists:
                        existing_data["data"].append({
                            "company": company_name,
                            "public_key_data": public_key
                        })

                    return existing_data
                except Exception as e:
                    frappe.throw("Error updating JSON data for public key: " + str(e))

def create_public_key():
                try:
                    settings = frappe.get_doc('Zatca ERPgulf Setting')
                    company = settings.company
                    company_name = frappe.db.get_value("Company", company, "abbr")
                    certificate_data_str = settings.get("certificate", "{}")
                    try:
                        certificate_data = json.loads(certificate_data_str)
                    except json.JSONDecodeError:
                        frappe.throw("Certificate field contains invalid JSON")
                    
                    base_64 = get_certificate_for_company(certificate_data, company_name)
                    if not base_64:
                        frappe.throw(f"No certificate found for company in public key creation{company_name}")
                    cert_base64 = """
                    -----BEGIN CERTIFICATE-----
                    {base_64}
                    -----END CERTIFICATE-----
                    """.format(base_64=base_64)
                    cert = x509.load_pem_x509_certificate(cert_base64.encode(), default_backend())
                    public_key = cert.public_key()
                    public_key_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()  # Convert bytes to string
                            
                    if not settings.public_key:
                        settings.public_key = {}
                    
                    if isinstance(settings.public_key, str):
                        settings.public_key = json.loads(settings.public_key)
                    
                    updated_data = update_json_data_public_key(settings.public_key, company_name, public_key_pem)
                    settings.public_key = json.dumps(updated_data)
                    settings.save(ignore_permissions=True)
                except Exception as e:
                    frappe.throw(" error in public key creation: "+ str(e))


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
    

def get_private_key_for_company(private_key_data, company_name):
                    try:     
                        for entry in private_key_data.get("companies", []):
                            if entry.get("company") == company_name:
                                return entry.get("private_key_data")
                        return None
                    except Exception as e:
                        frappe.throw("Error in getting private key for company: " + str(e))


def digital_signature(hash1):
                    try:
                        settings = frappe.get_doc('Zatca ERPgulf Setting')
                        company = settings.company
                        company_name = frappe.db.get_value("Company", company, "abbr")
                        basic_auth = settings.get("private_key", "{}")
                        private_key_data   = json.loads(basic_auth)
                        key_file = get_private_key_for_company(private_key_data, company_name)
                        private_key_bytes = key_file.encode('utf-8')
                        private_key = serialization.load_pem_private_key(private_key_bytes, password=None, backend=default_backend())
                        hash_bytes = bytes.fromhex(hash1)
                        signature = private_key.sign(hash_bytes, ec.ECDSA(hashes.SHA256()))
                        encoded_signature = base64.b64encode(signature).decode()
                        return encoded_signature
                    except Exception as e:
                             frappe.throw(" error in digital signature: "+ str(e) )

def get_certificate_for_company(certificate_content, company_name):
                    try:
                        for entry in certificate_content.get("data", []):
                            if entry.get("company") == company_name:
                                return entry.get("certificate")
                        return None
                    except Exception as e:
                        frappe.throw("Error in getting certificate for company: " + str(e))


def extract_certificate_details():
            
            try:    
                    settings = frappe.get_doc('Zatca ERPgulf Setting')  
                    company = settings.company
                    company_name = frappe.db.get_value("Company", company, "abbr")
                    certificate_data_str = settings.get("certificate", "{}")
                    try:
                        certificate_data = json.loads(certificate_data_str)
                    except json.JSONDecodeError:
                        frappe.throw("Certificate field contains invalid JSON")
                    
                    certificate_content = get_certificate_for_company(certificate_data, company_name)
                    if not certificate_content:
                        frappe.throw(f"No certificate found for company {company_name}")
                    formatted_certificate = "-----BEGIN CERTIFICATE-----\n"
                    formatted_certificate += "\n".join(certificate_content[i:i+64] for i in range(0, len(certificate_content), 64))
                    formatted_certificate += "\n-----END CERTIFICATE-----\n"
                    certificate_bytes = formatted_certificate.encode('utf-8')
                    cert = x509.load_pem_x509_certificate(certificate_bytes, default_backend())
                    formatted_issuer_name = cert.issuer.rfc4514_string()
                    issuer_name = ", ".join([x.strip() for x in formatted_issuer_name.split(',')])
                    serial_number = cert.serial_number
                    return issuer_name, serial_number
            except Exception as e:
                             frappe.throw(" error in extracting certificate details: "+ str(e) )
    

def certificate_hash():
            
            try:
                settings = frappe.get_doc('Zatca ERPgulf Setting')
                company = settings.company
                company_name = frappe.db.get_value("Company", company, "abbr")
                certificate_data_str = settings.get("certificate", "{}")
                try:
                        certificate_data = json.loads(certificate_data_str)
                except json.JSONDecodeError:
                        frappe.throw("Certificate field contains invalid JSON")   
                certificate_data = get_certificate_for_company(certificate_data, company_name)
                if not certificate_data:
                        frappe.throw(f"No certificate found for company in certificate hash {company_name}")
                certificate_data_bytes = certificate_data.encode('utf-8')
                sha256_hash = hashlib.sha256(certificate_data_bytes).hexdigest()
                base64_encoded_hash = base64.b64encode(sha256_hash.encode('utf-8')).decode('utf-8')
                return base64_encoded_hash
            
            except Exception as e:
                    frappe.throw("error in obtaining certificate hash: "+ str(e) )


def signxml_modify():
                try:
                    encoded_certificate_hash= certificate_hash()
                    issuer_name, serial_number = extract_certificate_details()
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


def populate_The_UBL_Extensions_Output(encoded_signature,namespaces,signed_properties_base64,encoded_hash):
        try:
            
            updated_invoice_xml = etree.parse(frappe.local.site + '/private/files/after_step_4.xml')
            root3 = updated_invoice_xml.getroot()
            settings = frappe.get_doc('Zatca ERPgulf Setting')
            company = settings.company
            company_name = frappe.db.get_value("Company", company, "abbr")
            certificate_data_str = settings.get("certificate", "{}")
            try:
                certificate_data = json.loads(certificate_data_str)
            except json.JSONDecodeError:
                frappe.throw("Certificate field contains invalid JSON")
            
            content= get_certificate_for_company(certificate_data, company_name)
            if not content:
                frappe.throw(f"No certificate found for company in ubl extension output {company_name}")
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
            with open(frappe.local.site + "/private/files/final_xml_after_sign.xml", 'wb') as file:
                updated_invoice_xml.write(file,encoding='utf-8',xml_declaration=True,)
        except Exception as e:
                    frappe.throw(" error in populate ubl extension output: "+ str(e) )


def get_public_key_for_company(data, company_name):
            try:
                for entry in data.get("data", []):
                    if entry.get("company") == company_name:
                        return entry.get("public_key_data")
                return None
            except Exception as e:
                frappe.throw("Error in getting public key for company: " + str(e))


def extract_public_key_data():
            try:
                settings = frappe.get_doc('Zatca ERPgulf Setting')
                company = settings.company
                company_name = frappe.db.get_value("Company", company, "abbr")
                public_key_data_str = settings.get("public_key", "{}")
        
                try:
                    public_key_data = json.loads(public_key_data_str)
                except json.JSONDecodeError:
                    frappe.throw("Public key field contains invalid JSON")
                public_key_pem = get_public_key_for_company(public_key_data, company_name)
                if not public_key_pem:
                    frappe.throw(f"No public key found for company {company_name}")
                lines = public_key_pem.splitlines()
                key_data = ''.join(lines[1:-1])
                key_data = key_data.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '')
                key_data = key_data.replace(' ', '').replace('\n', '')
                
                return key_data
            except Exception as e:
                    frappe.throw(" error in extracting public key data: "+ str(e) )


def get_tlv_for_value(tag_num, tag_value):
                try:
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
                except Exception as e:
                    frappe.throw(" error in getting the tlv data value: "+ str(e) )


def tag8_publickey():
                    try:
                        create_public_key()
                        base64_encoded = extract_public_key_data() 
                        
                        byte_data = base64.b64decode(base64_encoded)
                        hex_data = binascii.hexlify(byte_data).decode('utf-8')
                        chunks = [hex_data[i:i + 2] for i in range(0, len(hex_data), 2)]
                        value = ''.join(chunks)
                        binary_data = bytes.fromhex(value)
                        
                        base64_encoded1 = base64.b64encode(binary_data).decode('utf-8')
                        return binary_data
                    except Exception as e: 
                        frappe.throw(" error in tag 8 from public key: "+ str(e) )


def tag9_signature_ecdsa():
            try:

                settings = frappe.get_doc('Zatca ERPgulf Setting')
                company = settings.company
                company_name = frappe.db.get_value("Company", company, "abbr")
                certificate_data_str = settings.get("certificate", "{}")
                try:
                    certificate_data = json.loads(certificate_data_str)
                except json.JSONDecodeError:
                    frappe.throw("Certificate field contains invalid JSON")
                
                # Get the certificate for the specific company
                certificate_content= get_certificate_for_company(certificate_data, company_name)
                if not certificate_content:
                    frappe.throw(f"No certificate found for company in tag9 {company_name}")
                formatted_certificate = "-----BEGIN CERTIFICATE-----\n"
                formatted_certificate += "\n".join(certificate_content[i:i+64] for i in range(0, len(certificate_content), 64))
                formatted_certificate += "\n-----END CERTIFICATE-----\n"
                # print(formatted_certificate)
                certificate_bytes = formatted_certificate.encode('utf-8')
                cert = x509.load_pem_x509_certificate(certificate_bytes, default_backend())
                signature = cert.signature
                signature_hex = "".join("{:02x}".format(byte) for byte in signature)
                signature_bytes = bytes.fromhex(signature_hex)
                signature_base64 = base64.b64encode(signature_bytes).decode()

                return signature_bytes
            except Exception as e:
                    frappe.throw(" error in tag 9 (signaturetag): "+ str(e) )



def generate_tlv_xml():
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
                    except Exception as e:
                        frappe.throw(" error in getting the entire tlv data: "+ str(e) )


def update_Qr_toXml(qrCodeB64):
                    try:
                        xml_file_path = frappe.local.site + "/private/files/final_xml_after_sign.xml"
                        xml_tree = etree.parse(xml_file_path)
                        qr_code_element = xml_tree.find('.//cac:AdditionalDocumentReference[cbc:ID="QR"]/cac:Attachment/cbc:EmbeddedDocumentBinaryObject', namespaces={'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2', 'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'})
                        if qr_code_element is not None:
                            qr_code_element.text =qrCodeB64
                        else:
                            frappe.msgprint("QR code element not found")

                        xml_tree.write(xml_file_path, encoding="UTF-8", xml_declaration=True)
                    except Exception as e:
                            frappe.throw(" error in saving tlv data to xml: "+ str(e) )

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

def get_csid_for_company(basic_auth_data, company_name):
                    try:     
                        for entry in basic_auth_data.get("data", []):
                            if entry.get("company") == company_name:
                                return entry.get("csid")
                        return None
                    except Exception as e:
                        frappe.throw("Error in getting csid for company:  " + str(e) )

def compliance_api_call(uuid1,encoded_hash,signed_xmlfile_name):
                try:
                    settings = frappe.get_doc('Zatca ERPgulf Setting')
                    payload = json.dumps({
                        "invoiceHash": encoded_hash,
                        "uuid": uuid1,
                        "invoice": xml_base64_Decode(signed_xmlfile_name) })
                    company = settings.company
                    company_name = frappe.db.get_value("Company", company, "abbr")
                    basic_auth = settings.get("basic_auth", "{}")
                    # frappe.msgprint(basic_auth)
                    basic_auth_data = json.loads(basic_auth)
                    csid = get_csid_for_company(basic_auth_data, company_name)
                    # frappe.msgprint(csid)
                    if csid:
                        headers = {
                            'accept': 'application/json',
                            'Accept-Language': 'en',
                            'Accept-Version': 'V2',
                            'Authorization': "Basic " + csid,
                            'Content-Type': 'application/json'
                        }
                    else:
                        frappe.throw("CSID for company {} not found".format(company_name))
                    try:
                        # frappe.throw("inside compliance api call2")
                        response = requests.request("POST", url=get_API_url(base_url="compliance/invoices"), headers=headers, data=payload)
                        frappe.msgprint(response.text)

                        # return response.text

                        if response.status_code != 200:
                            frappe.throw("Error in complaince: " + str(response.text))    
                    
                    except Exception as e:
                        frappe.msgprint(str(e))
                        return "error in compliance", "NOT ACCEPTED"
                except Exception as e:
                    frappe.throw("ERROR in clearance invoice ,zatca validation:  " + str(e) )
                                
def get_request_id_for_company(compliance_request_id_data, company_name):
                try:
                    for entry in compliance_request_id_data.get("data", []):
                        if entry.get("company") == company_name:
                            return str(entry.get("request_id"))
                    frappe.throw("Error while retrieving  request id of company for production:  " + str(e) )
                except Exception as e:
                        frappe.throw("Error in getting request id of company for production:  " + str(e) )

def update_json_data_certificate(existing_data, company_name, certificate):
                    try:
                        company_exists = False
                        for entry in existing_data["data"]:
                            if entry["company"] == company_name:
                                entry["certificate"] = certificate
                                company_exists = True
                                break
                        if not company_exists:
                            existing_data["data"].append({
                                "company": company_name,
                                "certificate": certificate
                            })
                        return existing_data
                    except Exception as e:
                        frappe.throw("Error updating JSON data for certificate: " + str(e))

@frappe.whitelist(allow_guest=True)                   
def production_CSID():    
                try:
                    settings = frappe.get_doc('Zatca ERPgulf Setting')
                    company = settings.company
                    company_name = frappe.db.get_value("Company", company, "abbr")
                    basic_auth = settings.get("basic_auth", "{}")
                    # frappe.msgprint(basic_auth)
                    basic_auth_data = json.loads(basic_auth)
                    csid = get_csid_for_company(basic_auth_data, company_name)
                    compliance_request_id = settings.get("compliance_request_id", "{}")
                    compliance_request_id_data = json.loads(compliance_request_id)
                    request_id = get_request_id_for_company(compliance_request_id_data, company_name)
                    payload = json.dumps({
                            "compliance_request_id": request_id
                        })
                    headers = {
                    'accept': 'application/json',
                    'Accept-Version': 'V2',
                    'Authorization': 'Basic'+ csid,
                    # 'Authorization': 'Basic'+ "VkZWc1NsRXhTalpSTUU1Q1dsaHNibEZZWkVwUmEwWnVVMVZrUWxkWWJGcFhhazAxVTJzeFFtSXdaRVJSTTBaSVZUQXdNRTlWU2tKVVZVNU9VV3hXTkZKWWNFSlZhMHB1Vkd4YVExRlZNVTVSTWpGWFUyMUtkVmR1V21oV01EVjNXVzB4YW1Rd2FHOVpNRFZPWVdzeE5GUlhjRXBsYXpGeFVWaHdVRlpGYkRaV01taHFWR3N4Y1ZvemFFNWhhMncxVkZkd1JtUXdNVVZSV0dSWVlXdEpNVlJXUm5wa01FNVNWMVZTVjFWV1JraFNXR1JMVmtaR1ZWSldiRTVSYkd4SVVWUkdWbEpWVGpOa01VSk9aV3RHTTFReFVtcGtNRGxGVVZSS1RsWkZSak5VVlZKQ1pXc3hWRm96WkV0YU1XeEZWbXhHVWxNd1VrTlBWVXBzVWpKNE5sTlZWbk5rVjAxNlVXMTRXazB4U25kWmFra3dXakZGZVU5WVZtdFRSWEJ2VjFST1UyTkhTblJaTW1SVVlrVTFSVlJXVGxwa01IQkNWMVZTVjFWV1JrVlNSVWw0VmxaVmVGVllVbEJTUjJONVZHdFNUbVZGTVZWVlZFWk5Wa1V4TTFSVlVuSk5NREZGV2pOa1QyRnJWak5VVlZKQ1pEQXhObEZzWkU1UmEwWklVVzVzZUZJeFRrNU9SR3hDV2pCV1NGRnNUakZSYTBwQ1VWVjBRazFGYkVKUmEzaFNZVWhDV1UxRlNrVmtSVVpTVDFWS05rOUhaM2ROYms1M1ZrWkdTbFZWVGpKT1YyYzBWRmhHTkdGRVVuQlRSVEYzVVcwNGRsRnRPWEJXUm1ScllsTjBVMWRYV2t0aVZYQlBaR3BrV1dSdVZUVk5NbHAyVjFjME1FNVVhRTlTTVVwdVltNW5NazVIV2xkaGJUbFdUREZDTVdGdFpHcFhXR1J1V1RBeE0xSkZSbHBTUmxwVFRVWlNRbFZWWjNaUmEwWktaREJHUlZFd1NucGFNV3hGVm14SmQxVnJTa3BTTTBaT1UxVmtkV05GYkVoaE1ERktVakpvVGxaSVRqTlVNVVphVWtaYVVsVlZWa1ZTUld3MFZFWmFVMVpHV2tsa00yeE5WbXhLVlZacmFETmxhM2hZVm0xMFRtRnJjSFJVVm1SU1RrVjRXRlpVU2xwV1JXd3dWRlpTUm1WRk9VUk5SRlphWVd4Vk1GUkdaRkpPVm14VllVY3hUbFpGV25OVWExSlNUVlp3Y1ZKWFdrNVJha0pJVVRKa2RGVXdjSFppVmxFMFlWaG9jbEZXUmtaVVZWSTJWRmhrVGxKSGMzcFVWVkp1WkRBMWNWSllaRTVTUlVZelZGaHdSbFJyTVVKak1HUkNUVlpXUmxKRlJqTlNWVEZWVWxob1RsWkZWbE5VVlVVMFVqQkZlRlpWVmtoYU0yUktWbGQ0UzFVeFNrVlRWRlpPWVcxME5GTkljRUphUlVwdVZHeGFRMUZVYUU1U2JYaExZa1pzV0dReVpHRlhSVFIzVjFab1UySkZiRWhTYlhCclVqSjNlVmxXYUZOalJuQlpWRmhrUkZveGJFcFRNamxoVTFod2NVMUZWa0prTUd4RlZURkdRbVF4U201VFYyaENWRmhHVTFOclJYSlZSRTVKVkVac2FWUXdNRFJPVldoTFRETmtUMlZ0UmxkT01XUnFXbTVKZGxkcVRqRmpWR3hMVFRCV1ZHTnNXbHBsYTBad1VsVkdkazV0YUdwUFZGSlRVMGR3YldRelRuZFpVemwzVjBaYWRWWnBPWFpWVjBaT1QxUk9hVTVzU1RKaVYyUmhWMFJDTVZGV1RYbE5WVnB1VUZFOVBRPT06eXRabHl6YklXY0wrUHlETytFd1JqWHRHSEp4SHB3cXdJYUVsaGxMQVJZQT0=",
                    # 'Authorization': 'Basic'+ "VFVsSlExSjZRME5CWlhsblFYZEpRa0ZuU1VkQldYbFpXak01U2sxQmIwZERRM0ZIVTAwME9VSkJUVU5OUWxWNFJYcEJVa0puVGxaQ1FVMU5RMjFXU21KdVduWmhWMDV3WW0xamQwaG9ZMDVOYWsxNFRXcEplazFxUVhwUFZFbDZWMmhqVGsxcVozaE5ha2w1VFdwRmQwMUVRWGRYYWtJMVRWRnpkME5SV1VSV1VWRkhSWGRLVkZGVVJWbE5RbGxIUVRGVlJVTjNkMUJOZWtGM1QxUmpkMDlFUVRKTlZFRjNUVVJCZWsxVFozZEtaMWxFVmxGUlMwUkNPVUpsUjJ4NlNVVnNkV016UW14Wk0xSndZakkwWjFFeU9YVmtTRXBvV1ROU2NHSnRZMmRUYkU1RVRWTlpkMHBCV1VSV1VWRkVSRUl4VlZVeFVYUlBSR2N5VGtSTmVFMVVVVEZNVkUxM1RVUnJNMDFFWjNkT2FrVjNUVVJCZDAxNlFsZE5Ra0ZIUW5seFIxTk5ORGxCWjBWSFFsTjFRa0pCUVV0Qk1FbEJRa3hSYUhCWU1FSkVkRUZST1VKNk9HZ3dNbk53VkZGSlVVTjJOV2c0VFhGNGFEUnBTRTF3UW04dlFtOXBWRmRrYlN0U1dXWktiVXBPZGpkWWRuVTVNMlp2V1c0ME5UaE9SMUpuYm5nMk5HWldhbTlWTDFCMWFtZGpXWGRuWTAxM1JFRlpSRlpTTUZSQlVVZ3ZRa0ZKZDBGRVEwSnpaMWxFVmxJd1VrSkpSM0ZOU1VkdWNFbEhhMDFKUjJoTlZITjNUMUZaUkZaUlVVVkVSRWw0VEZaU1ZGWklkM2xNVmxKVVZraDNla3hYVm10TmFrcHRUVmRSTkV4WFZUSlpWRWwwVFZSRmVFOURNRFZaYWxVMFRGZFJOVmxVYUcxTlZFWnNUa1JSTVZwcVJXWk5RakJIUTJkdFUwcHZiVlE0YVhoclFWRkZUVVI2VFhkTlJHc3pUVVJuZDA1cVJYZE5SRUYzVFhwRlRrMUJjMGRCTVZWRlJFRjNSVTFVUlhoTlZFVlNUVUU0UjBFeFZVVkhaM2RKVld4S1UxSkVTVFZOYW10NFNIcEJaRUpuVGxaQ1FUaE5SbXhLYkZsWGQyZGFXRTR3V1ZoU2JFbEhSbXBrUjJ3eVlWaFNjRnBZVFhkRFoxbEpTMjlhU1hwcU1FVkJkMGxFVTFGQmQxSm5TV2hCVFhGU1NrRXJVRE5JVEZsaVQwMDROVWhLTDNkT2VtRldOMWRqWm5JdldqTjFjVGxLTTBWVGNsWlpla0ZwUlVGdk5taGpPVFJTU0dwbWQzTndZUzl3V0ZadVZpOXZVV0ZOT1ROaU5sSTJiV2RhV0RCMVFWTXlNVVpuUFE9PTp5dFpseXpiSVdjTCtQeURPK0V3UmpYdEdISnhIcHdxd0lhRWxobExBUllBPQ==",
                    'Content-Type': 'application/json' }
                    response = requests.request("POST", url=get_API_url(base_url="production/csids"), headers=headers, data=payload)
                    frappe.msgprint(response.text)
                    if response.status_code != 200:
                        frappe.throw("Error in production: " + str(response.text))
                    data=json.loads(response.text)
                    concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
                    encoded_value = base64.b64encode(concatenated_value.encode()).decode()

                    # frappe.msgprint("certificate: " + str(settings.certificate))
        
                    if not settings.certificate:
                        settings.certificate = {"data": []}
                    
                    if isinstance(settings.certificate, str):
                        try:
                            settings.certificate = json.loads(settings.certificate)
                        except json.JSONDecodeError:
                            frappe.throw("certificate field contains invalid JSON")
                    
                    updated_certificate_data = update_json_data_certificate(
                        settings.certificate, 
                        company_name, 
                        base64.b64decode(data["binarySecurityToken"]).decode('utf-8')
                    )
                    settings.set("certificate", json.dumps(updated_certificate_data))
                    
                    settings.save(ignore_permissions=True)
                    basic_auth_production = settings.get("basic_auth_production", "{}")
                    try:
                        basic_auth_production_data = json.loads(basic_auth_production)
                    except json.JSONDecodeError:
                        basic_auth_production_data = {"companies": []}
                    except:
                        basic_auth_production_data = {"companies": []}
                    # frappe.msgprint(basic_auth_production_data)

                    updated_data = update_json_data_production_csid(basic_auth_production_data, company_name, encoded_value)
                    settings.set("basic_auth_production", json.dumps(updated_data))
                    settings.save(ignore_permissions=True)
                except Exception as e:
                    frappe.throw("error in  production csid formation:  " + str(e) )


def get_Reporting_Status(result):
                    try:
                        json_data = json.loads(result.text)
                        reporting_status = json_data.get("reportingStatus")
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


def get_production_csid_for_company(basic_auth_production_data, company_name):
                    try:  
                        for entry in basic_auth_production_data.get("companies", []):
                            if entry.get("company") == company_name:
                                return entry.get("production_csid")
                        return None
                    except Exception as e:
                            frappe.throw("Error in getting production csid of company for api   " + str(e)) 


def update_json_data_pih(existing_data, company_name, pih):
                    try:
                        company_exists = False
                        for entry in existing_data["data"]:
                            if entry["company"] == company_name:
                                # Update the PIH for the existing company
                                entry["pih"] = pih
                                company_exists = True
                                break
                        if not company_exists:
                            existing_data["data"].append({
                                "company": company_name,
                                "pih": pih
                            })
                        return existing_data
                    except Exception as e:
                                        frappe.throw("Error in json data of pih  " + str(e)) 

def attach_QR_Image(qrCodeB64,sales_invoice_doc):
                    try:
                        qr = pyqrcode.create(qrCodeB64)
                        temp_file_path = "qr_code.png"
                        qr_image=qr.png(temp_file_path, scale=5)
                        file = frappe.get_doc({
                            "doctype": "File",
                            "file_name": f"QR_image_{sales_invoice_doc.name}.png",
                            "attached_to_doctype": sales_invoice_doc.doctype,
                            "attached_to_name": sales_invoice_doc.name,
                            "content": open(temp_file_path, "rb").read()
                           
                        })
                        file.save(ignore_permissions=True)
                    except Exception as e:
                        frappe.throw("error in qrcode from xml:  " + str(e) )

def reporting_API(uuid1,encoded_hash,signed_xmlfile_name,invoice_number,sales_invoice_doc):
                    try:
                        settings = frappe.get_doc('Zatca ERPgulf Setting')
                        company = settings.company
                        company_name = frappe.db.get_value("Company", sales_invoice_doc.company, "abbr")
                        payload = json.dumps({
                        "invoiceHash": encoded_hash,
                        "uuid": uuid1,
                        "invoice": xml_base64_Decode(signed_xmlfile_name),
                        })
                        basic_auth_production = settings.get("basic_auth_production", "{}")
                        basic_auth_production_data = json.loads(basic_auth_production)
                        production_csid = get_production_csid_for_company(basic_auth_production_data, company_name)

                        if production_csid:
                            headers = {
                                'accept': 'application/json',
                                    'accept-language': 'en',
                                    'Clearance-Status': '0',
                                    'Accept-Version': 'V2',
                                    # 'Authorization': "Basic VFVsSlJESjZRME5CTkVOblFYZEpRa0ZuU1ZSaWQwRkJaSEZFYlVsb2NYTnFjRzAxUTNkQlFrRkJRakp2UkVGTFFtZG5jV2hyYWs5UVVWRkVRV3BDYWsxU1ZYZEZkMWxMUTFwSmJXbGFVSGxNUjFGQ1IxSlpSbUpIT1dwWlYzZDRSWHBCVWtKbmIwcHJhV0ZLYXk5SmMxcEJSVnBHWjA1dVlqTlplRVo2UVZaQ1oyOUthMmxoU21zdlNYTmFRVVZhUm1ka2JHVklVbTVaV0hBd1RWSjNkMGRuV1VSV1VWRkVSWGhPVlZVeGNFWlRWVFZYVkRCc1JGSlRNVlJrVjBwRVVWTXdlRTFDTkZoRVZFbDVUVVJOZVU5RVJURk9SRmw2VFd4dldFUlVTWGxOUkUxNlRVUkZNVTVFV1hwTmJHOTNWRlJGVEUxQmEwZEJNVlZGUW1oTlExVXdSWGhFYWtGTlFtZE9Wa0pCYjFSQ1ZYQm9ZMjFzZVUxU2IzZEhRVmxFVmxGUlRFVjRSa3RhVjFKcldWZG5aMUZ1U21oaWJVNXZUVlJKZWs1RVJWTk5Ra0ZIUVRGVlJVRjRUVXBOVkVrelRHcEJkVTFETkhoTlJsbDNSVUZaU0V0dldrbDZhakJEUVZGWlJrczBSVVZCUVc5RVVXZEJSVVF2ZDJJeWJHaENka0pKUXpoRGJtNWFkbTkxYnpaUGVsSjViWGx0VlRsT1YxSm9TWGxoVFdoSFVrVkNRMFZhUWpSRlFWWnlRblZXTW5oWWFYaFpOSEZDV1dZNVpHUmxjbnByVnpsRWQyUnZNMGxzU0dkeFQwTkJhVzkzWjJkSmJVMUpSMHhDWjA1V1NGSkZSV2RaVFhkbldVTnJabXBDT0UxU2QzZEhaMWxFVmxGUlJVUkNUWGxOYWtsNVRXcE5lVTVFVVRCTmVsRjZZVzFhYlU1RVRYbE5VamgzU0ZGWlMwTmFTVzFwV2xCNVRFZFJRa0ZSZDFCTmVrVjNUVlJqTVUxNmF6Tk9SRUYzVFVSQmVrMVJNSGREZDFsRVZsRlJUVVJCVVhoTlJFVjRUVkpGZDBSM1dVUldVVkZoUkVGb1ZGbFhNWGRpUjFWblVsUkZXazFDWTBkQk1WVkZSSGQzVVZVeVJuUmpSM2hzU1VWS01XTXpUbkJpYlZaNlkzcEJaRUpuVGxaSVVUUkZSbWRSVldoWFkzTmlZa3BvYWtRMVdsZFBhM2RDU1V4REszZE9WbVpMV1hkSWQxbEVWbEl3YWtKQ1ozZEdiMEZWWkcxRFRTdDNZV2R5UjJSWVRsb3pVRzF4ZVc1TE5Xc3hkRk00ZDFSbldVUldVakJtUWtWamQxSlVRa1J2UlVkblVEUlpPV0ZJVWpCalJHOTJURE5TZW1SSFRubGlRelUyV1ZoU2FsbFROVzVpTTFsMVl6SkZkbEV5Vm5sa1JWWjFZMjA1YzJKRE9WVlZNWEJHVTFVMVYxUXdiRVJTVXpGVVpGZEtSRkZUTUhoTWJVNTVZa1JEUW5KUldVbExkMWxDUWxGVlNFRlJSVVZuWVVGM1oxb3dkMkpuV1VsTGQxbENRbEZWU0UxQlIwZFpiV2d3WkVoQk5reDVPVEJqTTFKcVkyMTNkV1Z0UmpCWk1rVjFXakk1TWt4dVRtaE1NRTVzWTI1U1JtSnVTblppUjNkMlZrWk9ZVkpYYkhWa2JUbHdXVEpXVkZFd1JYaE1iVlkwWkVka2FHVnVVWFZhTWpreVRHMTRkbGt5Um5OWU1WSlVWMnRXU2xSc1dsQlRWVTVHVEZaT01WbHJUa0pNVkVWdlRWTnJkVmt6U2pCTlEzTkhRME56UjBGUlZVWkNla0ZDYUdnNWIyUklVbmRQYVRoMlpFaE9NRmt6U25OTWJuQm9aRWRPYUV4dFpIWmthVFY2V1ZNNWRsa3pUbmROUVRSSFFURlZaRVIzUlVJdmQxRkZRWGRKU0dkRVFXUkNaMDVXU0ZOVlJVWnFRVlZDWjJkeVFtZEZSa0pSWTBSQloxbEpTM2RaUWtKUlZVaEJkMDEzU25kWlNrdDNXVUpDUVVkRFRuaFZTMEpDYjNkSFJFRkxRbWRuY2tKblJVWkNVV05FUVdwQlMwSm5aM0pDWjBWR1FsRmpSRUY2UVV0Q1oyZHhhR3RxVDFCUlVVUkJaMDVLUVVSQ1IwRnBSVUY1VG1oNVkxRXpZazVzVEVaa1QxQnNjVmxVTmxKV1VWUlhaMjVMTVVkb01FNUlaR05UV1RSUVprTXdRMGxSUTFOQmRHaFlkblkzZEdWMFZVdzJPVmRxY0RoQ2VHNU1URTEzWlhKNFdtaENibVYzYnk5blJqTkZTa0U5UFE9PTpmOVlSaG9wTi9HN3gwVEVDT1k2bktTQ0hMTllsYjVyaUFIU0ZQSUNvNHF3PQ==" ,
                                    # 'Authorization': "Basic VFVsSlJESjZRME5CTkVOblFYZEpRa0ZuU1ZSaWQwRkJaSEZFYlVsb2NYTnFjRzAxUTNkQlFrRkJRakp2UkVGTFFtZG5jV2hyYWs5UVVWRkVRV3BDYWsxU1ZYZEZkMWxMUTFwSmJXbGFVSGxNUjFGQ1IxSlpSbUpIT1dwWlYzZDRSWHBCVWtKbmIwcHJhV0ZLYXk5SmMxcEJSVnBHWjA1dVlqTlplRVo2UVZaQ1oyOUthMmxoU21zdlNYTmFRVVZhUm1ka2JHVklVbTVaV0hBd1RWSjNkMGRuV1VSV1VWRkVSWGhPVlZVeGNFWlRWVFZYVkRCc1JGSlRNVlJrVjBwRVVWTXdlRTFDTkZoRVZFbDVUVVJOZVU5RVJURk9SRmw2VFd4dldFUlVTWGxOUkUxNlRVUkZNVTVFV1hwTmJHOTNWRlJGVEUxQmEwZEJNVlZGUW1oTlExVXdSWGhFYWtGTlFtZE9Wa0pCYjFSQ1ZYQm9ZMjFzZVUxU2IzZEhRVmxFVmxGUlRFVjRSa3RhVjFKcldWZG5aMUZ1U21oaWJVNXZUVlJKZWs1RVJWTk5Ra0ZIUVRGVlJVRjRUVXBOVkVrelRHcEJkVTFETkhoTlJsbDNSVUZaU0V0dldrbDZhakJEUVZGWlJrczBSVVZCUVc5RVVXZEJSVVF2ZDJJeWJHaENka0pKUXpoRGJtNWFkbTkxYnpaUGVsSjViWGx0VlRsT1YxSm9TWGxoVFdoSFVrVkNRMFZhUWpSRlFWWnlRblZXTW5oWWFYaFpOSEZDV1dZNVpHUmxjbnByVnpsRWQyUnZNMGxzU0dkeFQwTkJhVzkzWjJkSmJVMUpSMHhDWjA1V1NGSkZSV2RaVFhkbldVTnJabXBDT0UxU2QzZEhaMWxFVmxGUlJVUkNUWGxOYWtsNVRXcE5lVTVFVVRCTmVsRjZZVzFhYlU1RVRYbE5VamgzU0ZGWlMwTmFTVzFwV2xCNVRFZFJRa0ZSZDFCTmVrVjNUVlJqTVUxNmF6Tk9SRUYzVFVSQmVrMVJNSGREZDFsRVZsRlJUVVJCVVhoTlJFVjRUVkpGZDBSM1dVUldVVkZoUkVGb1ZGbFhNWGRpUjFWblVsUkZXazFDWTBkQk1WVkZSSGQzVVZVeVJuUmpSM2hzU1VWS01XTXpUbkJpYlZaNlkzcEJaRUpuVGxaSVVUUkZSbWRSVldoWFkzTmlZa3BvYWtRMVdsZFBhM2RDU1V4REszZE9WbVpMV1hkSWQxbEVWbEl3YWtKQ1ozZEdiMEZWWkcxRFRTdDNZV2R5UjJSWVRsb3pVRzF4ZVc1TE5Xc3hkRk00ZDFSbldVUldVakJtUWtWamQxSlVRa1J2UlVkblVEUlpPV0ZJVWpCalJHOTJURE5TZW1SSFRubGlRelUyV1ZoU2FsbFROVzVpTTFsMVl6SkZkbEV5Vm5sa1JWWjFZMjA1YzJKRE9WVlZNWEJHVTFVMVYxUXdiRVJTVXpGVVpGZEtSRkZUTUhoTWJVNTVZa1JEUW5KUldVbExkMWxDUWxGVlNFRlJSVVZuWVVGM1oxb3dkMkpuV1VsTGQxbENRbEZWU0UxQlIwZFpiV2d3WkVoQk5reDVPVEJqTTFKcVkyMTNkV1Z0UmpCWk1rVjFXakk1TWt4dVRtaE1NRTVzWTI1U1JtSnVTblppUjNkMlZrWk9ZVkpYYkhWa2JUbHdXVEpXVkZFd1JYaE1iVlkwWkVka2FHVnVVWFZhTWpreVRHMTRkbGt5Um5OWU1WSlVWMnRXU2xSc1dsQlRWVTVHVEZaT01WbHJUa0pNVkVWdlRWTnJkVmt6U2pCTlEzTkhRME56UjBGUlZVWkNla0ZDYUdnNWIyUklVbmRQYVRoMlpFaE9NRmt6U25OTWJuQm9aRWRPYUV4dFpIWmthVFY2V1ZNNWRsa3pUbmROUVRSSFFURlZaRVIzUlVJdmQxRkZRWGRKU0dkRVFXUkNaMDVXU0ZOVlJVWnFRVlZDWjJkeVFtZEZSa0pSWTBSQloxbEpTM2RaUWtKUlZVaEJkMDEzU25kWlNrdDNXVUpDUVVkRFRuaFZTMEpDYjNkSFJFRkxRbWRuY2tKblJVWkNVV05FUVdwQlMwSm5aM0pDWjBWR1FsRmpSRUY2UVV0Q1oyZHhhR3RxVDFCUlVVUkJaMDVLUVVSQ1IwRnBSVUY1VG1oNVkxRXpZazVzVEVaa1QxQnNjVmxVTmxKV1VWUlhaMjVMTVVkb01FNUlaR05UV1RSUVprTXdRMGxSUTFOQmRHaFlkblkzZEdWMFZVdzJPVmRxY0RoQ2VHNU1URTEzWlhKNFdtaENibVYzYnk5blJqTkZTa0U5UFE9PTpmOVlSaG9wTi9HN3gwVEVDT1k2bktTQ0hMTllsYjVyaUFIU0ZQSUNvNHF3PQ==",
                                    # 'Authorization': 'Basic' + settings.basic_auth_production,
                                    'Authorization': 'Basic' + production_csid,
                                    'Content-Type': 'application/json',
                                    'Cookie': 'TS0106293e=0132a679c0639d13d069bcba831384623a2ca6da47fac8d91bef610c47c7119dcdd3b817f963ec301682dae864351c67ee3a402866'
                                    }    
                        else:
                            frappe.throw("Production CSID for company {} not found".format(company_name))
                        try:
                            response = requests.request("POST", url=get_API_url(base_url="invoices/reporting/single"), headers=headers, data=payload)
                            if response.status_code  in (400,405,406,409 ):
                                invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number )
                                invoice_doc.db_set('custom_uuid' , 'Not Submitted' , commit=True  , update_modified=True)
                                invoice_doc.db_set('custom_zatca_status' , 'Not Submitted' , commit=True  , update_modified=True)

                                frappe.throw("Error: The request you are sending to Zatca is in incorrect format. Please report to system administrator . Status code:  " + str(response.status_code) + "<br><br> " + response.text )            
                            
                            
                            if response.status_code  in (401,403,407,451 ):
                                invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number  )
                                invoice_doc.db_set('custom_uuid' , 'Not Submitted' , commit=True  , update_modified=True)
                                invoice_doc.db_set('custom_zatca_status' , 'Not Submitted' , commit=True  , update_modified=True)

                              
                                frappe.throw("Error: Zatca Authentication failed. Your access token may be expired or not valid. Please contact your system administrator. Status code:  " + str(response.status_code) + "<br><br> " + response.text)            
                            
                            if response.status_code not in (200, 202):
                                invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number  )
                                invoice_doc.db_set('custom_uuid' , 'Not Submitted' , commit=True  , update_modified=True)
                                invoice_doc.db_set('custom_zatca_status' , 'Not Submitted' , commit=True  , update_modified=True)
                                
                               
                                frappe.throw("Error: Zatca server busy or not responding. Try after sometime or contact your system administrator. Status code:  " + str(response.status_code)+ "<br><br> " + response.text )
                            
                            
                            
                            if response.status_code  in (200, 202):
                                if response.status_code == 202:
                                    msg = "REPORTED WITH WARNIGS: <br> <br> Please copy the below message and send it to your system administrator to fix this warnings before next submission <br>  <br><br> "
                                
                                if response.status_code == 200:
                                    msg = "SUCCESS: <br>   <br><br> "
                                
                                msg = msg + "Status Code: " + str(response.status_code) + "<br><br> "
                                msg = msg + "Zatca Response: " + response.text + "<br><br> "
                                frappe.msgprint(msg)
                                pih_data = json.loads(settings.get("pih", "{}"))
                                updated_pih_data = update_json_data_pih(pih_data, company_name, encoded_hash)
                                settings.set("pih", json.dumps(updated_pih_data))
                                settings.save(ignore_permissions=True)
                                
                                invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number )
                                invoice_doc.db_set('custom_uuid' , uuid1 , commit=True  , update_modified=True)
                                invoice_doc.db_set('custom_zatca_status' , 'REPORTED' , commit=True  , update_modified=True)

                               
                                # frappe.msgprint(xml_cleared)
                                success_Log(response.text,uuid1, invoice_number)
                                
                            else:
                                error_Log()
                        except Exception as e:
                            frappe.throw("Error in reporting api-2:  " + str(e) )
    
                    except Exception as e:
                        frappe.throw("Error in reporting api-1:  " + str(e) )

def clearance_API(uuid1,encoded_hash,signed_xmlfile_name,invoice_number,sales_invoice_doc):
                    try:
                        # frappe.msgprint("Clearance API")
                        settings = frappe.get_doc('Zatca ERPgulf Setting')
                        company = settings.company
                        company_name = frappe.db.get_value("Company", sales_invoice_doc.company, "abbr")
                        payload = json.dumps({
                        "invoiceHash": encoded_hash,
                        "uuid": uuid1,
                        "invoice": xml_base64_Decode(signed_xmlfile_name), })
                        basic_auth_production = settings.get("basic_auth_production", "{}")
                        basic_auth_production_data = json.loads(basic_auth_production)
                        production_csid = get_production_csid_for_company(basic_auth_production_data, company_name)

                        if production_csid:
                            headers = {
                            'accept': 'application/json',
                            'accept-language': 'en',
                            'Clearance-Status': '1',
                            'Accept-Version': 'V2',
                            'Authorization': 'Basic' + production_csid,
                            # 'Authorization': 'Basic' + settings.basic_auth,
                            'Content-Type': 'application/json',
                            'Cookie': 'TS0106293e=0132a679c03c628e6c49de86c0f6bb76390abb4416868d6368d6d7c05da619c8326266f5bc262b7c0c65a6863cd3b19081d64eee99' }
                        else:
                            frappe.throw("Production CSID for company {} not found".format(company_name))
                        response = requests.request("POST", url=get_API_url(base_url="invoices/clearance/single"), headers=headers, data=payload)
                        
                        # response.status_code = 400
                        
                        if response.status_code  in (400,405,406,409 ):
                            invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number  )
                            invoice_doc.db_set('custom_uuid' , "Not Submitted" , commit=True  , update_modified=True)
                            invoice_doc.db_set('custom_zatca_status' , "Not Submitted" , commit=True  , update_modified=True)
                            
                           
                            frappe.throw("Error: The request you are sending to Zatca is in incorrect format. Please report to system administrator . Status code:  " + str(response.status_code) + "<br><br> " + response.text )            
                        
                        
                        if response.status_code  in (401,403,407,451 ):
                            invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number  )
                            invoice_doc.db_set('custom_uuid' , "Not Submitted" , commit=True  , update_modified=True)
                            invoice_doc.db_set('custom_zatca_status' , "Not Submitted" , commit=True  , update_modified=True)

                           
                            frappe.throw("Error: Zatca Authentication failed. Your access token may be expired or not valid. Please contact your system administrator. Status code:  " + str(response.status_code) + "<br><br> " + response.text)            
                        
                        if response.status_code not in (200, 202):
                            invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number  )
                            invoice_doc.db_set('custom_uuid' , "Not Submitted" , commit=True  , update_modified=True)
                            invoice_doc.db_set('custom_zatca_status' , "Not Submitted" , commit=True  , update_modified=True)

                            
                          
                          
                            
                            frappe.throw("Error: Zatca server busy or not responding. Try after sometime or contact your system administrator. Status code:  " + str(response.status_code))
                        
                        if response.status_code  in (200, 202):
                                if response.status_code == 202:
                                    msg = "CLEARED WITH WARNIGS: <br> <br> Please copy the below message and send it to your system administrator to fix this warnings before next submission <br>  <br><br> "
                                
                                if response.status_code == 200:
                                    msg = "SUCCESS: <br>   <br><br> "
                                
                                msg = msg + "Status Code: " + str(response.status_code) + "<br><br> "
                                msg = msg + "Zatca Response: " + response.text + "<br><br> "
                                frappe.msgprint(msg)
                                pih_data = json.loads(settings.get("pih", "{}"))
                                updated_pih_data = update_json_data_pih(pih_data, company_name,encoded_hash)
                                settings.set("pih", json.dumps(updated_pih_data))
                                settings.save(ignore_permissions=True)
                                
                                invoice_doc = frappe.get_doc('Sales Invoice' , invoice_number )
                                invoice_doc.db_set('custom_uuid' , uuid1 , commit=True  , update_modified=True)
                                invoice_doc.db_set('custom_zatca_status' , "CLEARED" , commit=True  , update_modified=True)
                                
                               
                                
                                data=json.loads(response.text)
                                base64_xml = data["clearedInvoice"] 
                                xml_cleared= base64.b64decode(base64_xml).decode('utf-8')
                                file = frappe.get_doc({                       #attaching the cleared xml
                                    "doctype": "File",
                                    "file_name": "Cleared xml file" + sales_invoice_doc.name,
                                    "attached_to_doctype": sales_invoice_doc.doctype,
                                    "attached_to_name": sales_invoice_doc.name,
                                    "content": xml_cleared
                                    
                                })
                                file.save(ignore_permissions=True)
                                # frappe.msgprint(xml_cleared)
                                success_Log(response.text,uuid1, invoice_number)
                                return xml_cleared
                        else:
                                error_Log()
                            
                    except Exception as e:
                        frappe.throw("error in clearance api:  " + str(e) )


@frappe.whitelist(allow_guest=True) 
def zatca_Call(invoice_number, compliance_type="0", any_item_has_tax_template= False):
        
                    compliance_type = "0"
                    try:    
                            # create_compliance_x509()
                            # frappe.throw("Created compliance x509 certificate")
                            
                            if not frappe.db.exists("Sales Invoice", invoice_number):
                                frappe.throw("Invoice Number is NOT Valid:  " + str(invoice_number))
                            invoice= xml_tags()
                            invoice,uuid1,sales_invoice_doc=salesinvoice_data(invoice,invoice_number)
                            customer_doc= frappe.get_doc("Customer",sales_invoice_doc.customer)
                            if compliance_type == "0":
                                    # frappe.throw(str("here 7 " + str(compliance_type))) 
                                    if customer_doc.custom_b2c == 1:
                                        invoice = invoice_Typecode_Simplified(invoice, sales_invoice_doc)
                                    else:
                                        invoice = invoice_Typecode_Standard(invoice, sales_invoice_doc)
                            else:  # if it a compliance test
                                # frappe.throw(str("here 8 " + str(compliance_type))) 
                                invoice = invoice_Typecode_Compliance(invoice, compliance_type)
                            
                            invoice=doc_Reference(invoice,sales_invoice_doc,invoice_number)
                            invoice=additional_Reference(invoice)
                            invoice=company_Data(invoice,sales_invoice_doc)
                            invoice=customer_Data(invoice,sales_invoice_doc)
                            invoice=delivery_And_PaymentMeans(invoice,sales_invoice_doc, sales_invoice_doc.is_return) 
                            if not any_item_has_tax_template:
                                invoice = tax_Data(invoice, sales_invoice_doc)
                            else:
                                invoice = tax_Data_with_template(invoice, sales_invoice_doc)
                            if not any_item_has_tax_template:
                                invoice=item_data(invoice,sales_invoice_doc)
                            else:
                                   item_data_with_template(invoice,sales_invoice_doc)
                            pretty_xml_string=xml_structuring(invoice,sales_invoice_doc)
                            with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'r') as file:
                                    file_content = file.read()
                            tag_removed_xml = removeTags(file_content)
                            canonicalized_xml = canonicalize_xml(tag_removed_xml)
                            hash1, encoded_hash = getInvoiceHash(canonicalized_xml)
                            encoded_signature = digital_signature(hash1)
                            issuer_name,serial_number =extract_certificate_details()
                            encoded_certificate_hash=certificate_hash()
                            namespaces,signing_time=signxml_modify()
                            signed_properties_base64=generate_Signed_Properties_Hash(signing_time,issuer_name,serial_number,encoded_certificate_hash)
                            populate_The_UBL_Extensions_Output(encoded_signature,namespaces,signed_properties_base64,encoded_hash)
                            tlv_data = generate_tlv_xml()
                            # print(tlv_data)
                            tagsBufsArray = []
                            for tag_num, tag_value in tlv_data.items():
                                tagsBufsArray.append(get_tlv_for_value(tag_num, tag_value))
                            qrCodeBuf = b"".join(tagsBufsArray)
                            # print(qrCodeBuf)
                            qrCodeB64 = base64.b64encode(qrCodeBuf).decode('utf-8')
                            # print(qrCodeB64)
                            update_Qr_toXml(qrCodeB64)
                            signed_xmlfile_name=structuring_signedxml()
                            
                            
                            if compliance_type == "0":
                                if customer_doc.custom_b2c == 1:
                                    reporting_API(uuid1, encoded_hash, signed_xmlfile_name,invoice_number,sales_invoice_doc)
                                    attach_QR_Image(qrCodeB64,sales_invoice_doc)
                                else:
                                    xml_cleared=clearance_API(uuid1, encoded_hash, signed_xmlfile_name,invoice_number,sales_invoice_doc)
                                    attach_QR_Image(qrCodeB64,sales_invoice_doc)
                            else:  # if it a compliance test
                                # frappe.msgprint("Compliance test")
                                compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name)
                                attach_QR_Image(qrCodeB64,sales_invoice_doc)
                    except:       
                            frappe.log_error(title='Zatca invoice call failed', message=frappe.get_traceback())
                            
@frappe.whitelist(allow_guest=True) 
def zatca_Call_compliance(invoice_number, compliance_type="0",any_item_has_tax_template= False):
                    # 0 is default. Not for compliance test. But normal reporting or clearance call.
                    # 1 is for compliance test. Simplified invoice
                    # 2 is for compliance test. Standard invoice
                    # 3 is for compliance test. Simplified Credit Note
                    # 4 is for compliance test. Standard Credit Note
                    # 5 is for compliance test. Simplified Debit Note
                    # 6 is for compliance test. Standard Debit Note
                    settings = frappe.get_doc('Zatca ERPgulf Setting')
                    
                    if settings.validation_type == "Simplified Invoice":
                        compliance_type="1"
                    elif settings.validation_type == "Standard Invoice":
                        compliance_type="2"
                    elif settings.validation_type == "Simplified Credit Note":
                        compliance_type="3"
                    elif settings.validation_type == "Standard Credit Note":
                        compliance_type="4"
                    elif settings.validation_type == "Simplified Debit Note":
                        compliance_type="5"
                    elif settings.validation_type == "Standard Debit Note":
                        compliance_type="6"
                    
                    # frappe.throw("Compliance Type: " + compliance_type )
                    try:    
                            # create_compliance_x509()
                            # frappe.throw("Created compliance x509 certificate")
                            
                            if not frappe.db.exists("Sales Invoice", invoice_number):
                                frappe.throw("Invoice Number is NOT Valid:  " + str(invoice_number))
                            
                            
                            invoice= xml_tags()
                            invoice,uuid1,sales_invoice_doc=salesinvoice_data(invoice,invoice_number)
                            
                            customer_doc= frappe.get_doc("Customer",sales_invoice_doc.customer)
                            
                            
                            invoice = invoice_Typecode_Compliance(invoice, compliance_type)
                            
                            invoice=doc_Reference_compliance(invoice,sales_invoice_doc,invoice_number,compliance_type)
                            invoice=additional_Reference(invoice)
                            invoice=company_Data(invoice,sales_invoice_doc)
                            invoice=customer_Data(invoice,sales_invoice_doc)
                            invoice=delivery_And_PaymentMeans_for_Compliance(invoice,sales_invoice_doc,compliance_type) 
                            if not any_item_has_tax_template:
                                invoice = tax_Data(invoice, sales_invoice_doc)
                            else:
                                invoice = tax_Data_with_template(invoice, sales_invoice_doc)
                            if not any_item_has_tax_template:
                                invoice=item_data(invoice,sales_invoice_doc)
                            else:
                                   item_data_with_template(invoice,sales_invoice_doc)
                            pretty_xml_string=xml_structuring(invoice,sales_invoice_doc)
                            with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'r') as file:
                                    file_content = file.read()
                            tag_removed_xml = removeTags(file_content)
                            canonicalized_xml = canonicalize_xml(tag_removed_xml)
                            hash1, encoded_hash = getInvoiceHash(canonicalized_xml)
                            encoded_signature = digital_signature(hash1)
                            issuer_name,serial_number =extract_certificate_details()
                            encoded_certificate_hash=certificate_hash()
                            namespaces,signing_time=signxml_modify()
                            signed_properties_base64=generate_Signed_Properties_Hash(signing_time,issuer_name,serial_number,encoded_certificate_hash)
                            populate_The_UBL_Extensions_Output(encoded_signature,namespaces,signed_properties_base64,encoded_hash)
                            tlv_data = generate_tlv_xml()
                            tagsBufsArray = []
                            for tag_num, tag_value in tlv_data.items():
                                tagsBufsArray.append(get_tlv_for_value(tag_num, tag_value))
                            qrCodeBuf = b"".join(tagsBufsArray)
                            qrCodeB64 = base64.b64encode(qrCodeBuf).decode('utf-8')
                            update_Qr_toXml(qrCodeB64)
                            signed_xmlfile_name=structuring_signedxml()
                            compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name)

                    except:       
                            frappe.log_error(title='Zatca invoice call failed', message=frappe.get_traceback())

                
@frappe.whitelist(allow_guest=True)                  
def zatca_Background(invoice_number):
                    
                    try:
                        # sales_invoice_doc = doc
                        # invoice_number = sales_invoice_doc.name
                        settings = frappe.get_doc('Zatca ERPgulf Setting')
                        sales_invoice_doc= frappe.get_doc("Sales Invoice",invoice_number )
                        any_item_has_tax_template = any(item.item_tax_template for item in sales_invoice_doc.items)

                        if any_item_has_tax_template:
                            if not all(item.item_tax_template for item in sales_invoice_doc.items):
                                frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")

                        for item in sales_invoice_doc.items:
                            if item.item_tax_template:
                                item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
                                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                                for tax in item_tax_template.taxes:
                                    tax_rate = float(tax.tax_rate)
                                    
                                    if f"{tax_rate:.2f}" not in ['5.00', '15.00'] and zatca_tax_category not in ["Zero Rated", "Exempted", "Services outside scope of tax / Not subject to VAT"]:
                                        frappe.throw("Zatca tax category should be 'Zero Rated', 'Exempted' or 'Services outside scope of tax / Not subject to VAT' for items with tax rate not equal to 5.00 or 15.00.")
                                    
                                    if f"{tax_rate:.2f}" == '15.00' and zatca_tax_category != "Standard":
                                        frappe.throw("Check the Zatca category code and enable it as standard.")
                        
                        if settings.zatca_invoice_enabled != 1:
                            frappe.throw("Zatca Invoice is not enabled in Zatca Settings, Please contact your system administrator")
                        
                        if not frappe.db.exists("Sales Invoice", invoice_number):
                                frappe.throw("Please save and submit the invoice before sending to Zatca:  " + str(invoice_number))
                                
            
                        if sales_invoice_doc.docstatus in [0,2]:
                            frappe.throw("Please submit the invoice before sending to Zatca:  " + str(invoice_number))
                            
                        if sales_invoice_doc.custom_zatca_status == "REPORTED" or sales_invoice_doc.custom_zatca_status == "CLEARED":
                            frappe.throw("Already submitted to Zakat and Tax Authority")
                        
                        zatca_Call(invoice_number,0,any_item_has_tax_template)
                        
                    except Exception as e:
                        frappe.throw("Error in background call:  " + str(e) )
                    
# #                     # frappe.enqueue(
#                     #         zatca_Call,
#                     #         queue="short",
#                     #         timeout=200,
#                     #         invoice_number=invoice_number)
#                     # frappe.msgprint("queued")



@frappe.whitelist(allow_guest=True)          
def zatca_Background_on_submit(doc, method=None):              
# def zatca_Background(invoice_number):
                    
                    try:
                        sales_invoice_doc = doc
                        invoice_number = sales_invoice_doc.name
                        sales_invoice_doc= frappe.get_doc("Sales Invoice",invoice_number )
                        settings = frappe.get_doc('Zatca ERPgulf Setting')
                        any_item_has_tax_template = False
        
                        for item in sales_invoice_doc.items:
                            if item.item_tax_template:
                                any_item_has_tax_template = True
                                break
                        
                        if any_item_has_tax_template:
                            for item in sales_invoice_doc.items:
                                if not item.item_tax_template:
                                    frappe.throw("If any one item has an Item Tax Template, all items must have an Item Tax Template.")

                        for item in sales_invoice_doc.items:
                            if item.item_tax_template:
                                item_tax_template = frappe.get_doc('Item Tax Template', item.item_tax_template)
                                zatca_tax_category = item_tax_template.custom_zatca_tax_category
                                for tax in item_tax_template.taxes:
                                    tax_rate = float(tax.tax_rate)
                                    
                                    if f"{tax_rate:.2f}" not in ['5.00', '15.00'] and zatca_tax_category not in ["Zero Rated", "Exempted", "Services outside scope of tax / Not subject to VAT"]:
                                        frappe.throw("Zatca tax category should be 'Zero Rated', 'Exempted' or 'Services outside scope of tax / Not subject to VAT' for items with tax rate not equal to 5.00 or 15.00.")
                                    
                                    if f"{tax_rate:.2f}" == '15.00' and zatca_tax_category != "Standard":
                                        frappe.throw("Check the Zatca category code and enable it as standard.")

                        if settings.zatca_invoice_enabled != 1:
                            frappe.throw("Zatca Invoice is not enabled in Zatca Settings, Please contact your system administrator")
                        
                        if not frappe.db.exists("Sales Invoice", invoice_number):
                                frappe.throw("Please save and submit the invoice before sending to Zatca:  " + str(invoice_number))
                                                
                        
            
                        if sales_invoice_doc.docstatus in [0,2]:
                            frappe.throw("Please submit the invoice before sending to Zatca:  " + str(invoice_number))
                            
                        if sales_invoice_doc.custom_zatca_status == "REPORTED" or sales_invoice_doc.custom_zatca_status == "CLEARED":
                            frappe.throw("Already submitted to Zakat and Tax Authority")
                        
                        zatca_Call(invoice_number,0,any_item_has_tax_template)
                        
                    except Exception as e:
                        frappe.throw("Error in background call:  " + str(e) )
                    
# #                     # frappe.enqueue(
#                     #         zatca_Call,
#                     #         queue="short",
#                     #         timeout=200,
#                     #         invoice_number=invoice_number)
#                     # frappe.msgprint("queued")


