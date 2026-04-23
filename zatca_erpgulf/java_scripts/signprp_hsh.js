const crypto = require("crypto");

const xml_string = `<xades:SignedProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Id="xadesSignedProperties">
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
                                </xades:SignedProperties>`;

const xml_string_rendered = xml_string
    .replace("{signing_time}", "2026-04-19T13:44:05")
    .replace("{certificate_hash}", "ZDMwMmI0MTE1NzVjOTU2NTk4YzVlODhhYmI0ODU2NDUyNTU2YTVhYjhhMDFmN2FjYjk1YTA2OWQ0NjY2MjQ4NQ==")
    .replace("{issuer_name}", "CN=PRZEINVOICESCA4-CA, DC=extgazt, DC=gov, DC=local")
    .replace("{serial_number}", "379112742831380471835263969587287663520528387");

// UTF-8 encoding
const utf8_bytes = Buffer.from(xml_string_rendered, "utf8");

// SHA256 hash (hex output)
const hex_sha256 = crypto.createHash("sha256").update(utf8_bytes).digest("hex");

// Base64 encode the HEX STRING (same as Python logic)
const signed_properties_base64 = Buffer.from(hex_sha256, "utf8").toString("base64");

console.log(signed_properties_base64);