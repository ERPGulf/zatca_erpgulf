"""
This module facilitates the generation, validation, and submission of
 ZATCA-compliant e-invoices for companies 
using ERPNext
"""

import hashlib
import base64
import json
import binascii
from datetime import datetime
from lxml import etree
import lxml.etree as MyTree
import frappe
from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.bindings._rust import ObjectIdentifier
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
import requests
import asn1


def encode_customoid(custom_string):
    """Encoding of a custom string"""
    # Create an encoder
    encoder = asn1.Encoder()
    encoder.start()
    encoder.write(custom_string, asn1.Numbers.UTF8String)
    return encoder.output()


def parse_csr_config(csr_config_string):
    """Parse the csr config data"""
    csr_config = {}
    lines = csr_config_string.splitlines()
    for line in lines:
        key, value = line.split("=", 1)
        csr_config[key.strip()] = value.strip()
    return csr_config


def get_csr_data_multiple(zatca_doc):
    """Getting csr data from the config for multiple"""
    try:
        csr_config_string = zatca_doc.custom_csr_config

        if not csr_config_string:
            frappe.throw("No CSR config found in company settings")

        csr_config = parse_csr_config(csr_config_string)

        csr_values = {
            "csr.common.name": csr_config.get("csr.common.name"),
            "csr.serial.number": csr_config.get("csr.serial.number"),
            "csr.organization.identifier": csr_config.get(
                "csr.organization.identifier"
            ),
            "csr.organization.unit.name": csr_config.get("csr.organization.unit.name"),
            "csr.organization.name": csr_config.get("csr.organization.name"),
            "csr.country.name": csr_config.get("csr.country.name"),
            "csr.invoice.type": csr_config.get("csr.invoice.type"),
            "csr.location.address": csr_config.get("csr.location.address"),
            "csr.industry.business.category": csr_config.get(
                "csr.industry.business.category"
            ),
        }

        return csr_values

    except (frappe.ValidationError, frappe.DoesNotExistError) as e:
        frappe.throw(f"Error in fetching CSR data: {e}")
        return None


def get_csr_data(company_abbr):
    """Getting csr data from the config"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)
        csr_config_string = company_doc.custom_csr_config

        if not csr_config_string:
            frappe.throw("No CSR config found in company settings")

        csr_config = parse_csr_config(csr_config_string)

        csr_values = {
            "csr.common.name": csr_config.get("csr.common.name"),
            "csr.serial.number": csr_config.get("csr.serial.number"),
            "csr.organization.identifier": csr_config.get(
                "csr.organization.identifier"
            ),
            "csr.organization.unit.name": csr_config.get("csr.organization.unit.name"),
            "csr.organization.name": csr_config.get("csr.organization.name"),
            "csr.country.name": csr_config.get("csr.country.name"),
            "csr.invoice.type": csr_config.get("csr.invoice.type"),
            "csr.location.address": csr_config.get("csr.location.address"),
            "csr.industry.business.category": csr_config.get(
                "csr.industry.business.category"
            ),
        }

        return csr_values

    except (frappe.ValidationError, frappe.DoesNotExistError) as e:
        frappe.throw(f"Error in fetching CSR data: {e}")
        return None


def create_private_keys(company_abbr, zatca_doc):
    """the function is for creating the private key"""
    try:
        if isinstance(zatca_doc, str):
            zatca_doc = json.loads(zatca_doc)
        # frappe.msgprint(f"Using OTP (Company): {zatca_doc}")
        # Validate zatca_doc structure
        if (
            not isinstance(zatca_doc, dict)
            or "doctype" not in zatca_doc
            or "name" not in zatca_doc
        ):
            frappe.throw(
                "Invalid 'zatca_doc' format. Must include 'doctype' and 'name'."
            )

        # Fetch the document based on doctype and name
        doc = frappe.get_doc(zatca_doc.get("doctype"), zatca_doc.get("name"))
        if doc.doctype == "Zatca Multiple Setting":
            multiple_setting_doc = frappe.get_doc("Zatca Multiple Setting", doc.name)
        elif doc.doctype == "Company":
            company_name = frappe.db.get_value(
                "Company", {"abbr": company_abbr}, "name"
            )
            company_doc = frappe.get_doc("Company", company_name)
        # company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        # if not company_name:
        #     frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        # company_doc = frappe.get_doc("Company", company_name)
        private_key = ec.generate_private_key(ec.SECP256K1(), backend=default_backend())
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        if doc.doctype == "Zatca Multiple Setting":
            multiple_setting_doc.custom_private_key = private_key_pem.decode("utf-8")
            multiple_setting_doc.save(ignore_permissions=True)
        elif doc.doctype == "Company":
            company_doc.custom_private_key = private_key_pem.decode("utf-8")
            company_doc.save(ignore_permissions=True)

        return private_key_pem
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(
            "error while creating the private key for company {company_abbr} " + str(e)
        )
        return None


@frappe.whitelist(allow_guest=False)
def create_csr(zatca_doc, portal_type, company_abbr):
    """
    Function defining the create csr method with the config csr data
    """
    try:
        # frappe.throw("hi")

        if isinstance(zatca_doc, str):
            zatca_doc = json.loads(zatca_doc)
        # frappe.msgprint(f"Using OTP (Company): {zatca_doc}")
        # Validate zatca_doc structure
        if (
            not isinstance(zatca_doc, dict)
            or "doctype" not in zatca_doc
            or "name" not in zatca_doc
        ):
            frappe.throw(
                "Invalid 'zatca_doc' format. Must include 'doctype' and 'name'."
            )

        # Fetch the document based on doctype and name
        doc = frappe.get_doc(zatca_doc.get("doctype"), zatca_doc.get("name"))
        # frappe.throw(doc)
        # Fetch CSR data based on document type
        if doc.doctype == "Zatca Multiple Setting":
            csr_values = get_csr_data_multiple(doc)
            # frappe.msgprint(f"Using OTP (Multiple Setting): {csr_values}")
        elif doc.doctype == "Company":
            csr_values = get_csr_data(company_abbr)
            # frappe.msgprint(f"Using OTP (Company): {csr_values}")
        else:
            frappe.throw("Unsupported document type for CSR creation.")

        company_csr_data = csr_values

        csr_common_name = company_csr_data.get("csr.common.name")
        csr_serial_number = company_csr_data.get("csr.serial.number")
        csr_organization_identifier = company_csr_data.get(
            "csr.organization.identifier"
        )
        csr_organization_unit_name = company_csr_data.get("csr.organization.unit.name")
        csr_organization_name = company_csr_data.get("csr.organization.name")
        csr_country_name = company_csr_data.get("csr.country.name")
        csr_invoice_type = company_csr_data.get("csr.invoice.type")
        csr_location_address = company_csr_data.get("csr.location.address")
        csr_industry_business_category = company_csr_data.get(
            "csr.industry.business.category"
        )

        if portal_type == "Sandbox":
            customoid = encode_customoid("TESTZATCA-Code-Signing")
        elif portal_type == "Simulation":
            customoid = encode_customoid("PREZATCA-Code-Signing")
        else:
            customoid = encode_customoid("ZATCA-Code-Signing")
        if doc.doctype == "Zatca Multiple Setting":
            private_key_pem = create_private_keys(doc, zatca_doc)
            # frappe.msgprint(f"Using OTP (Multiple Setting): {csr_values}")
        elif doc.doctype == "Company":
            private_key_pem = create_private_keys(company_abbr, zatca_doc)
            # frappe.msgprint(f"Using OTP (Company): {csr_values}")
        else:
            frappe.throw("no private key.")

        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None, backend=default_backend()
        )

        custom_oid_string = "1.3.6.1.4.1.311.20.2"
        oid = ObjectIdentifier(custom_oid_string)
        custom_extension = x509.extensions.UnrecognizedExtension(oid, customoid)

        dn = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, csr_country_name),
                x509.NameAttribute(
                    NameOID.ORGANIZATIONAL_UNIT_NAME, csr_organization_unit_name
                ),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, csr_organization_name),
                x509.NameAttribute(NameOID.COMMON_NAME, csr_common_name),
            ]
        )
        alt_name = x509.SubjectAlternativeName(
            [
                x509.DirectoryName(
                    x509.Name(
                        [
                            x509.NameAttribute(NameOID.SURNAME, csr_serial_number),
                            x509.NameAttribute(
                                NameOID.USER_ID, csr_organization_identifier
                            ),
                            x509.NameAttribute(NameOID.TITLE, csr_invoice_type),
                            x509.NameAttribute(
                                ObjectIdentifier("2.5.4.26"), csr_location_address
                            ),
                            x509.NameAttribute(
                                NameOID.BUSINESS_CATEGORY,
                                csr_industry_business_category,
                            ),
                        ]
                    )
                ),
            ]
        )

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(dn)
            .add_extension(custom_extension, critical=False)
            .add_extension(alt_name, critical=False)
            .sign(private_key, hashes.SHA256(), backend=default_backend())
        )
        mycsr = csr.public_bytes(serialization.Encoding.PEM)
        base64csr = base64.b64encode(mycsr)
        encoded_string = base64csr.decode("utf-8")
        if doc.doctype == "Zatca Multiple Setting":
            multiple_setting_doc = frappe.get_doc("Zatca Multiple Setting", doc.name)
            multiple_setting_doc.custom_csr_data = encoded_string.strip()
            multiple_setting_doc.save(ignore_permissions=True)
        elif doc.doctype == "Company":
            company_doc = frappe.get_doc("Company", {"abbr": company_abbr})
            company_doc.custom_csr_data = encoded_string.strip()
            # Save the updated company document
            company_doc.save(ignore_permissions=True)
        return encoded_string
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(
            "error occurred while creating csr for company {company_abbr} " + str(e)
        )
        return None


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
def create_csid(zatca_doc, company_abbr):
    """creating csid"""
    try:
        if isinstance(zatca_doc, str):
            zatca_doc = json.loads(zatca_doc)
        # frappe.msgprint(f"Using OTP (Company): {zatca_doc}")
        # Validate zatca_doc structure
        if (
            not isinstance(zatca_doc, dict)
            or "doctype" not in zatca_doc
            or "name" not in zatca_doc
        ):
            frappe.throw(
                "Invalid 'zatca_doc' format. Must include 'doctype' and 'name'."
            )
        # Fetch the document based on doctype and name
        doc = frappe.get_doc(zatca_doc.get("doctype"), zatca_doc.get("name"))
        if doc.doctype == "Zatca Multiple Setting":
            multiple_setting_doc = frappe.get_doc("Zatca Multiple Setting", doc.name)
            csr_data_str = multiple_setting_doc.get("custom_csr_data", "")
        elif doc.doctype == "Company":
            company_name = frappe.db.get_value(
                "Company", {"abbr": company_abbr}, "name"
            )

            company_doc = frappe.get_doc("Company", company_name)
            csr_data_str = company_doc.get("custom_csr_data", "")

            # frappe.msgprint(f"Using OTP (Company): {csr_values}")
        else:
            frappe.throw("Unsupported document type for CSR creation.")
        # company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        # if not company_name:
        #     frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        # # company_doc = frappe.get_doc("Company", company_name)
        # # csr_data_str = company_doc.get("custom_csr_data", "")

        # if not csr_data_str:
        #     frappe.throw("No CSR data found for the company.")
        csr_contents = csr_data_str.strip()

        if not csr_contents:
            frappe.throw(f"No valid CSR data found for company {company_name}")

        payload = json.dumps({"csr": csr_contents})
        # frappe.msgprint(f"Using OTP: {company_doc.custom_otp}")
        if doc.doctype == "Zatca Multiple Setting":
            otp = multiple_setting_doc.get("custom_otp", "")
            # frappe.msgprint(f"Using OTP (Multiple Setting): {csr_values}")
        elif doc.doctype == "Company":
            otp = company_doc.get("custom_otp", "")

            # frappe.msgprint(f"Using OTP (Company): {csr_values}")
        else:
            frappe.throw("no otp.")
        headers = {
            "accept": "application/json",
            "OTP": otp,
            "Accept-Version": "V2",
            "Content-Type": "application/json",
            "Cookie": "TS0106293e=0132a679c07382ce7821148af16b99da546c13ce1dcddbef0e19802eb470e539a4d39d5ef63d5c8280b48c529f321e8b0173890e4f",
        }

        frappe.publish_realtime(
            "show_gif", {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"}
        )

        response = requests.post(
            url=get_api_url(company_abbr, base_url="compliance"),
            headers=headers,
            data=payload,
            timeout=30,
        )
        frappe.publish_realtime("hide_gif")

        if response.status_code == 400:
            frappe.throw("Error: OTP is not valid. " + response.text)
        if response.status_code != 200:
            frappe.throw("Error: Issue with Certificate or OTP. " + response.text)
        frappe.msgprint(str(response.text))
        data = json.loads(response.text)

        concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
        encoded_value = base64.b64encode(concatenated_value.encode()).decode()
        if doc.doctype == "Zatca Multiple Setting":
            multiple_setting_doc.custom_certficate = base64.b64decode(
                data["binarySecurityToken"]
            ).decode("utf-8")
            multiple_setting_doc.custom_basic_auth_from_csid = encoded_value
            multiple_setting_doc.custom_compliance_request_id_ = data["requestID"]
            multiple_setting_doc.save(ignore_permissions=True)
        elif doc.doctype == "Company":
            company_doc.custom_certificate = base64.b64decode(
                data["binarySecurityToken"]
            ).decode("utf-8")
            company_doc.custom_basic_auth_from_csid = encoded_value
            company_doc.custom_compliance_request_id_ = data["requestID"]
            company_doc.save(ignore_permissions=True)
        return response.text

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in creating CSID: " + str(e))
        return None


# def create_public_key(company_abbr):
#     """Creating public key"""
#     try:
#         company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
#         if not company_name:
#             frappe.throw(f"Company with abbreviation {company_abbr} not found.")

#         company_doc = frappe.get_doc("Company", company_name)
#         certificate_data_str = company_doc.get("custom_certificate", "")

#         if not certificate_data_str:
#             frappe.throw("No certificate data found for the company.")
#         cert_base64 = f"""
#         -----BEGIN CERTIFICATE-----
#         {certificate_data_str.strip()}
#         -----END CERTIFICATE-----
#         """
#         cert = x509.load_pem_x509_certificate(cert_base64.encode(), default_backend())
#         public_key = cert.public_key()
#         public_key_pem = public_key.public_bytes(
#             encoding=serialization.Encoding.PEM,
#             format=serialization.PublicFormat.SubjectPublicKeyInfo,
#         ).decode()
#         company_doc.custom_public_key = public_key_pem
#         company_doc.save(ignore_permissions=True)

#     except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
#         frappe.throw("error occurred while creating public key for company " + str(e))
def create_public_key(company_abbr, source_doc=None):
    """Create a public key based on the company abbreviation and source document."""
    try:
        # Get the company name using the provided abbreviation
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        # Fetch the company document
        company_doc = frappe.get_doc("Company", company_name)

        # Initialize certificate_data_str based on the document type
        certificate_data_str = ""
        frappe.throw(source_doc)

        if source_doc:
            if source_doc.doctype == "Sales Invoice":
                # Use certificate from the company document for Sales Invoice
                certificate_data_str = company_doc.get("custom_certificate", "")
            elif source_doc.doctype == "POS Invoice":
                # Check if custom_zatca_pos_name exists in POS Invoice
                if source_doc.custom_zatca_pos_name:
                    # Fetch Zatca settings and use its certificate
                    zatca_settings = frappe.get_doc(
                        "Zatca Multiple Setting", source_doc.custom_zatca_pos_name
                    )
                    certificate_data_str = zatca_settings.get("custom_certficate", "")
                else:
                    # Fallback to using the company document's certificate
                    certificate_data_str = company_doc.get("custom_certificate", "")
            else:
                frappe.throw("Unsupported document type provided.")

        if not certificate_data_str:
            frappe.throw("No certificate data found.")

        # Build the PEM certificate
        cert_base64 = f"""
        -----BEGIN CERTIFICATE-----
        {certificate_data_str.strip()}
        -----END CERTIFICATE-----
        """
        # Load the certificate and extract the public key
        cert = x509.load_pem_x509_certificate(cert_base64.encode(), default_backend())
        public_key = cert.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        # Save the public key to the appropriate place
        if source_doc.doctype == "Sales Invoice":
            company_doc.custom_public_key = public_key_pem
            company_doc.save(ignore_permissions=True)
        elif source_doc.doctype == "POS Invoice":
            if source_doc.custom_zatca_pos_name:
                zatca_settings.custom_public_key = public_key_pem
                zatca_settings.save(ignore_permissions=True)
            else:
                company_doc.custom_public_key = public_key_pem
                company_doc.save(ignore_permissions=True)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error occurred while creating public key: " + str(e))


def removetags(finalzatcaxml):
    """remove the unwanted tags from created xml"""
    try:
        # Code corrected by Farook K - ERPGulf
        xml_file = MyTree.fromstring(finalzatcaxml)
        xsl_file = MyTree.fromstring(
            """<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
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
                                    </xsl:stylesheet>"""
        )
        transform = MyTree.XSLT(xsl_file.getroottree())
        transformed_xml = transform(xml_file.getroottree())
        return transformed_xml
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("error occurred win removing tags " + str(e))
        return None


def canonicalize_xml(tag_removed_xml):
    """canonicalisation of the xml"""
    try:
        canonical_xml = etree.tostring(tag_removed_xml, method="c14n").decode()
        return canonical_xml
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("error occurred in canonicalise xml " + str(e))
        return None


def getinvoicehash(canonicalized_xml):
    """Getting the invoice hash of the xml"""
    try:
        hash_object = hashlib.sha256(canonicalized_xml.encode())
        hash_hex = hash_object.hexdigest()
        # print(hash_hex)
        hash_base64 = base64.b64encode(bytes.fromhex(hash_hex)).decode("utf-8")
        return hash_hex, hash_base64
    except Exception as e:
        raise frappe.ValidationError(
            f"error occurred while invoice hash {str(e)}"
        ) from e


def digital_signature(hash1, company_abbr):
    """find digital signature of xml"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)
        private_key_data_str = company_doc.get("custom_private_key")

        if not private_key_data_str:
            frappe.throw("No private key data found for the company.")
        private_key_bytes = private_key_data_str.encode("utf-8")
        private_key = serialization.load_pem_private_key(
            private_key_bytes, password=None, backend=default_backend()
        )
        hash_bytes = bytes.fromhex(hash1)
        signature = private_key.sign(hash_bytes, ec.ECDSA(hashes.SHA256()))
        encoded_signature = base64.b64encode(signature).decode()

        return encoded_signature

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("eError in digital signature:" + str(e))
        return None


def extract_certificate_details(company_abbr):
    """extracting the certificate details from the certificate data"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)
        certificate_data_str = company_doc.get("custom_certificate")

        if not certificate_data_str:
            frappe.throw(f"No certificate data found for company {company_name}")

        certificate_content = certificate_data_str.strip()

        if not certificate_content:
            frappe.throw(
                f"No valid certificate content found for company {company_name}"
            )
        # Format the certificate string to PEM format if not already in correct PEM format
        formatted_certificate = "-----BEGIN CERTIFICATE-----\n"
        formatted_certificate += "\n".join(
            certificate_content[i : i + 64]
            for i in range(0, len(certificate_content), 64)
        )
        formatted_certificate += "\n-----END CERTIFICATE-----\n"
        # Load the certificate using cryptography
        certificate_bytes = formatted_certificate.encode("utf-8")
        cert = x509.load_pem_x509_certificate(certificate_bytes, default_backend())
        formatted_issuer_name = cert.issuer.rfc4514_string()
        issuer_name = ", ".join([x.strip() for x in formatted_issuer_name.split(",")])
        serial_number = cert.serial_number
        return issuer_name, serial_number

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error inextracting certificate details" + str(e))
        return None


def certificate_hash(company_abbr):
    """Find the certificate hash and returning the value"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)
        certificate_data_str = company_doc.get("custom_certificate")

        if not certificate_data_str:
            frappe.throw(f"No certificate data found for company {company_name}")
        certificate_data = certificate_data_str.strip()
        if not certificate_data:
            frappe.throw(f"No valid certificate data found for company {company_name}")

        # Calculate the SHA-256 hash of the certificate data
        certificate_data_bytes = certificate_data.encode("utf-8")
        sha256_hash = hashlib.sha256(certificate_data_bytes).hexdigest()
        # Encode the hash in base64
        base64_encoded_hash = base64.b64encode(sha256_hash.encode("utf-8")).decode(
            "utf-8"
        )
        return base64_encoded_hash

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in obtaining certificate hash: " + str(e))
        return None


def xml_base64_decode(signed_xmlfile_name):
    """xml base64 decode"""
    try:
        with open(signed_xmlfile_name, "r", encoding="utf-8") as file:
            xml = file.read().lstrip()
            base64_encoded = base64.b64encode(xml.encode("utf-8"))
            base64_decoded = base64_encoded.decode("utf-8")
            return base64_decoded
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.msgprint("Error in xml base64:  " + str(e))
        return None


def signxml_modify(company_abbr):
    """modify the signed xml by adding the values like signing time,serial number etc"""
    try:
        encoded_certificate_hash = certificate_hash(company_abbr)
        issuer_name, serial_number = extract_certificate_details(company_abbr)
        original_invoice_xml = etree.parse(
            frappe.local.site + "/private/files/finalzatcaxml.xml"
        )
        root = original_invoice_xml.getroot()
        namespaces = {
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "sig": "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2",
            "sac": "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
            "xades": "http://uri.etsi.org/01903/v1.3.2#",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }
        # ubl_extensions_xpath = (
        #     "//*[local-name()='Invoice']//*[local-name()='UBLExtensions']"
        # )
        # qr_xpath = "//*[local-name()='AdditionalDocumentReference']
        # [cbc:ID[normalize-space(text()) = 'QR']]"
        # signature_xpath = "//*[local-name()='Invoice']//*[local-name()='Signature']"
        xpath_dv = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:CertDigest/ds:DigestValue"
        xpath_signtime = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningTime"
        xpath_issuername = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties/xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:IssuerSerial/ds:X509IssuerName"
        xpath_serialnum = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:Object/xades:QualifyingProperties/xades:SignedProperties//xades:SignedSignatureProperties/xades:SigningCertificate/xades:Cert/xades:IssuerSerial/ds:X509SerialNumber"
        element_dv = root.find(xpath_dv, namespaces)
        element_st = root.find(xpath_signtime, namespaces)
        element_in = root.find(xpath_issuername, namespaces)
        element_sn = root.find(xpath_serialnum, namespaces)
        element_dv.text = encoded_certificate_hash
        element_st.text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        signing_time = element_st.text
        element_in.text = issuer_name
        element_sn.text = str(serial_number)
        with open(frappe.local.site + "/private/files/after_step_4.xml", "wb") as file:
            original_invoice_xml.write(
                file,
                encoding="utf-8",
                xml_declaration=True,
            )
        return namespaces, signing_time
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(" error in modification of xml sign part: " + str(e))
        return None


def generate_signed_properties_hash(
    signing_time, issuer_name, serial_number, encoded_certificate_hash
):
    """generate the signed property hash of the xml using a part
    of the xml"""
    try:
        xml_string = """<xades:SignedProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Id="xadesSignedProperties">
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
                                </xades:SignedProperties>"""
        xml_string_rendered = xml_string.format(
            signing_time=signing_time,
            certificate_hash=encoded_certificate_hash,
            issuer_name=issuer_name,
            serial_number=str(serial_number),
        )
        utf8_bytes = xml_string_rendered.encode("utf-8")
        hash_object = hashlib.sha256(utf8_bytes)
        hex_sha256 = hash_object.hexdigest()
        signed_properties_base64 = base64.b64encode(hex_sha256.encode("utf-8")).decode(
            "utf-8"
        )
        return signed_properties_base64
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(" error in generating signed properties hash: " + str(e))
        return None


def populate_the_ubl_extensions_output(
    encoded_signature, namespaces, signed_properties_base64, encoded_hash, company_abbr
):
    """populate the ubl extension output by giving the signature values and digest values"""
    try:
        updated_invoice_xml = etree.parse(
            frappe.local.site + "/private/files/after_step_4.xml"
        )
        root3 = updated_invoice_xml.getroot()
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)
        certificate_data_str = company_doc.get("custom_certificate")

        if not certificate_data_str:
            frappe.throw(f"No certificate data found for company {company_name}")
        content = certificate_data_str.strip()

        if not content:
            frappe.throw(
                f"No valid certificate content found for company {company_name}"
            )

        xpath_signvalue = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignatureValue"
        xpath_x509certi = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:KeyInfo/ds:X509Data/ds:X509Certificate"
        xpath_digvalue = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@URI='#xadesSignedProperties']/ds:DigestValue"
        xpath_digvalue2 = "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference[@Id='invoiceSignedData']/ds:DigestValue"

        signvalue6 = root3.find(xpath_signvalue, namespaces)
        x509certificate6 = root3.find(xpath_x509certi, namespaces)
        digestvalue6 = root3.find(xpath_digvalue, namespaces)
        digestvalue6_2 = root3.find(xpath_digvalue2, namespaces)

        signvalue6.text = encoded_signature
        x509certificate6.text = content
        digestvalue6.text = signed_properties_base64
        digestvalue6_2.text = encoded_hash

        with open(
            frappe.local.site + "/private/files/final_xml_after_sign.xml", "wb"
        ) as file:
            updated_invoice_xml.write(file, encoding="utf-8", xml_declaration=True)

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in populating UBL extension output: " + str(e))
        return


def extract_public_key_data(company_abbr):
    """extract public key"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)

        public_key_pem = company_doc.get("custom_public_key", "")
        if not public_key_pem:
            frappe.throw(f"No public key found for company {company_name}")

        lines = public_key_pem.splitlines()
        key_data = "".join(lines[1:-1])
        key_data = key_data.replace("-----BEGIN PUBLIC KEY-----", "").replace(
            "-----END PUBLIC KEY-----", ""
        )
        key_data = key_data.replace(" ", "").replace("\n", "")

        return key_data

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in extracting public key data: " + str(e))
        return None


def get_tlv_for_value(tag_num, tag_value):
    """get the tlv data value for teh qr"""
    try:
        tag_num_buf = bytes([tag_num])
        if tag_value is None:
            frappe.throw(f"Error: Tag value for tag number {tag_num} is None")
        if isinstance(tag_value, str):
            if len(tag_value) < 256:
                tag_value_len_buf = bytes([len(tag_value)])
            else:
                tag_value_len_buf = bytes(
                    [0xFF, (len(tag_value) >> 8) & 0xFF, len(tag_value) & 0xFF]
                )
            tag_value = tag_value.encode("utf-8")
        else:
            tag_value_len_buf = bytes([len(tag_value)])
        return tag_num_buf + tag_value_len_buf + tag_value
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(" error in getting the tlv data value: " + str(e))
        return None


def tag8_publickey(company_abbr):
    """tag 8 of qr from public key"""
    try:
        create_public_key(company_abbr)
        base64_encoded = extract_public_key_data(company_abbr)
        byte_data = base64.b64decode(base64_encoded)
        hex_data = binascii.hexlify(byte_data).decode("utf-8")
        chunks = [hex_data[i : i + 2] for i in range(0, len(hex_data), 2)]
        value = "".join(chunks)
        binary_data = bytes.fromhex(value)
        return binary_data
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in tag 8 from public key: " + str(e))
        return None


def tag9_signature_ecdsa(company_abbr):
    """tag 9 of signature"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)

        certificate_content = company_doc.custom_certificate or ""
        if not certificate_content:
            frappe.throw(f"No certificate found for company in tag9 {company_abbr}")

        formatted_certificate = "-----BEGIN CERTIFICATE-----\n"
        formatted_certificate += "\n".join(
            certificate_content[i : i + 64]
            for i in range(0, len(certificate_content), 64)
        )
        formatted_certificate += "\n-----END CERTIFICATE-----\n"

        certificate_bytes = formatted_certificate.encode("utf-8")
        cert = x509.load_pem_x509_certificate(certificate_bytes, default_backend())
        signature = cert.signature
        signature_hex = "".join("{:02x}".format(byte) for byte in signature)
        signature_bytes = bytes.fromhex(signature_hex)

        return signature_bytes

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in tag 9 (signaturetag): " + str(e))
        return None


def generate_tlv_xml(company_abbr):
    """generate xml by adding the tlv data"""
    try:

        with open(
            frappe.local.site + "/private/files/final_xml_after_sign.xml", "rb"
        ) as file:
            xml_data = file.read()
        root = etree.fromstring(xml_data)
        namespaces = {
            "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "sig": "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2",
            "sac": "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }
        issue_date_xpath = "/ubl:Invoice/cbc:IssueDate"
        issue_time_xpath = "/ubl:Invoice/cbc:IssueTime"
        issue_date_results = root.xpath(issue_date_xpath, namespaces=namespaces)
        issue_time_results = root.xpath(issue_time_xpath, namespaces=namespaces)
        issue_date = (
            issue_date_results[0].text.strip() if issue_date_results else "Missing Data"
        )
        issue_time = (
            issue_time_results[0].text.strip() if issue_time_results else "Missing Data"
        )
        issue_date_time = issue_date + "T" + issue_time
        tags_xpaths = [
            (
                1,
                "/ubl:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName",
            ),
            (
                2,
                "/ubl:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            ),
            (3, None),
            (4, "/ubl:Invoice/cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"),
            (5, "/ubl:Invoice/cac:TaxTotal/cbc:TaxAmount"),
            (
                6,
                "/ubl:Invoice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignedInfo/ds:Reference/ds:DigestValue",
            ),
            (
                7,
                "/ubl:Invoice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sig:UBLDocumentSignatures/sac:SignatureInformation/ds:Signature/ds:SignatureValue",
            ),
            (8, None),
            (9, None),
        ]
        result_dict = {}
        for tag, xpath in tags_xpaths:
            if isinstance(xpath, str):
                elements = root.xpath(xpath, namespaces=namespaces)
                if elements:
                    value = (
                        elements[0].text
                        if isinstance(elements[0], etree._Element)
                        else elements[0]
                    )
                    result_dict[tag] = value
                else:
                    result_dict[tag] = "Not found"
            else:
                result_dict[tag] = xpath
        result_dict[3] = issue_date_time
        result_dict[8] = tag8_publickey(company_abbr)
        result_dict[9] = tag9_signature_ecdsa(company_abbr)
        result_dict[1] = result_dict[1].encode(
            "utf-8"
        )  # Handling Arabic company name in QR Code
        return result_dict
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in getting the entire TLV data: " + str(e))
        return None


def update_qr_toxml(qrcodeb64, company_abbr):
    """updating the  alla values of qr to xml"""
    try:
        xml_file_path = frappe.local.site + "/private/files/final_xml_after_sign.xml"
        xml_tree = etree.parse(xml_file_path)
        namespaces = {
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        }
        qr_code_element = xml_tree.find(
            './/cac:AdditionalDocumentReference[cbc:ID="QR"]/cac:Attachment/cbc:EmbeddedDocumentBinaryObject',
            namespaces=namespaces,
        )
        if qr_code_element is not None:
            qr_code_element.text = qrcodeb64
        else:
            frappe.msgprint(
                f"QR code element not found in the XML for company {company_abbr}"
            )
        xml_tree.write(xml_file_path, encoding="UTF-8", xml_declaration=True)
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(
            f"Error in saving TLV data to XML for company {company_abbr}: " + str(e)
        )


def structuring_signedxml():
    """structuring the signed xml"""
    try:
        with open(
            frappe.local.site + "/private/files/final_xml_after_sign.xml",
            "r",
            encoding="utf-8",
        ) as file:
            xml_content = file.readlines()
        indentations = {
            29: [
                '<xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="signature">',
                "</xades:QualifyingProperties>",
            ],
            33: [
                '<xades:SignedProperties Id="xadesSignedProperties">',
                "</xades:SignedProperties>",
            ],
            37: [
                "<xades:SignedSignatureProperties>",
                "</xades:SignedSignatureProperties>",
            ],
            41: [
                "<xades:SigningTime>",
                "<xades:SigningCertificate>",
                "</xades:SigningCertificate>",
            ],
            45: ["<xades:Cert>", "</xades:Cert>"],
            49: [
                "<xades:CertDigest>",
                "<xades:IssuerSerial>",
                "</xades:CertDigest>",
                "</xades:IssuerSerial>",
            ],
            53: [
                '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>',
                "<ds:DigestValue>",
                "<ds:X509IssuerName>",
                "<ds:X509SerialNumber>",
            ],
        }

        def adjust_indentation(line):
            for col, tags in indentations.items():
                for tag in tags:
                    if line.strip().startswith(tag):
                        return " " * (col - 1) + line.lstrip()
            return line

        adjusted_xml_content = [adjust_indentation(line) for line in xml_content]
        with open(
            frappe.local.site + "/private/files/final_xml_after_indent.xml",
            "w",
            encoding="utf-8",
        ) as file:
            file.writelines(adjusted_xml_content)
        signed_xmlfile_name = (
            frappe.local.site + "/private/files/final_xml_after_indent.xml"
        )
        return signed_xmlfile_name
    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(" error in structuring signed xml: " + str(e))
        return None


def compliance_api_call(uuid1, encoded_hash, signed_xmlfile_name, company_abbr):
    """compliance api call for testing with sandbox"""
    try:
        company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        if not company_name:
            frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        company_doc = frappe.get_doc("Company", company_name)
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
        if response.status_code != 200:
            frappe.throw(f"Error in compliance: {response.text}")
        if response.status_code != 202:
            frappe.throw(f"Warning from zatca in compliance: {response.text}")

        return response.text
    except requests.exceptions.RequestException as e:
        frappe.msgprint(f"Request exception occurred: {str(e)}")
        return "error in compliance", "NOT ACCEPTED"

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw(f"ERROR in clearance invoice, ZATCA validation: {str(e)}")
        return None


@frappe.whitelist(allow_guest=False)
def production_csid(zatca_doc, company_abbr):
    """production csid button and api"""
    try:
        # company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        # if not company_name:
        #     frappe.throw(f"Company with abbreviation {company_abbr} not found.")

        # company_doc = frappe.get_doc("Company", company_name)
        if isinstance(zatca_doc, str):
            zatca_doc = json.loads(zatca_doc)
        # frappe.msgprint(f"Using OTP (Company): {zatca_doc}")
        # Validate zatca_doc structure
        if (
            not isinstance(zatca_doc, dict)
            or "doctype" not in zatca_doc
            or "name" not in zatca_doc
        ):
            frappe.throw(
                "Invalid 'zatca_doc' format. Must include 'doctype' and 'name'."
            )
        # Fetch the document based on doctype and name
        doc = frappe.get_doc(zatca_doc.get("doctype"), zatca_doc.get("name"))
        if doc.doctype == "Zatca Multiple Setting":
            multiple_setting_doc = frappe.get_doc("Zatca Multiple Setting", doc.name)
            csid = multiple_setting_doc.custom_basic_auth_from_csid
            request_id = multiple_setting_doc.custom_compliance_request_id_
        elif doc.doctype == "Company":
            company_name = frappe.db.get_value(
                "Company", {"abbr": company_abbr}, "name"
            )

            company_doc = frappe.get_doc("Company", company_name)
            csid = company_doc.custom_basic_auth_from_csid
            request_id = company_doc.custom_compliance_request_id_

        if not csid:
            frappe.throw(("CSID for company not found"))
        # request_id = company_doc.custom_compliance_request_id_
        if not request_id:
            frappe.throw("Compliance request ID for company  not found")
        payload = {"compliance_request_id": request_id}

        headers = {
            "accept": "application/json",
            "Accept-Version": "V2",
            "Authorization": "Basic " + csid,
            "Content-Type": "application/json",
        }
        frappe.publish_realtime(
            "show_gif", {"gif_url": "/assets/zatca_erpgulf/js/loading.gif"}
        )

        response = requests.post(
            url=get_api_url(company_abbr, base_url="production/csids"),
            headers=headers,
            json=payload,
            timeout=30,
        )
        frappe.publish_realtime("hide_gif")
        frappe.msgprint(response.text)

        if response.status_code != 200:
            frappe.throw("Error in production: " + response.text)

        data = response.json()
        concatenated_value = data["binarySecurityToken"] + ":" + data["secret"]
        encoded_value = base64.b64encode(concatenated_value.encode()).decode()
        if doc.doctype == "Zatca Multiple Setting":
            multiple_setting_doc.custom_certificate = base64.b64decode(
                data["binarySecurityToken"]
            ).decode("utf-8")
            multiple_setting_doc.custom_final_auth_csid = encoded_value

            multiple_setting_doc.save(ignore_permissions=True)
        elif doc.doctype == "Company":
            company_doc.custom_certificate = base64.b64decode(
                data["binarySecurityToken"]
            ).decode("utf-8")
            company_doc.custom_basic_auth_from_production = encoded_value

            company_doc.save(ignore_permissions=True)

        return response.text

    except (ValueError, KeyError, TypeError, frappe.ValidationError) as e:
        frappe.throw("Error in production CSID formation: " + str(e))
        return None
