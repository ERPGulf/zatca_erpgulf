


const crypto = require('crypto');
const fs = require('fs');

function getInvoiceHash(canonicalizedXml) {
    try {
        // Step 1: SHA256 hash
        const hash = crypto.createHash('sha256');
        hash.update(canonicalizedXml, 'utf8');

        // Step 2: Hex digest
        const hashHex = hash.digest('hex');

        // Step 3: Hex → Base64
        const hashBase64 = Buffer.from(hashHex, 'hex').toString('base64');

        return [hashHex, hashBase64];

    } catch (e) {
        throw new Error(`error occurred while invoice hash ${e.message}`);
    }
}

try {
    // ✅ Read XML file (same as Python open + read + lstrip)
    const filePath = "/opt/zatca-sdk/zatca-envoice-sdk-203/Apps/canonicalis.xml";
    const xmlContent = fs.readFileSync(filePath, 'utf8').trimStart();

    // ✅ Pass XML content (NOT file path)
    const [hashHex, hashBase64] = getInvoiceHash(xmlContent);

    console.log("----- Invoice Hash Results -----");
    console.log("Hex:    ", hashHex);
    console.log("Base64: ", hashBase64);

} catch (err) {
    console.error("Error:", err.message);
}




const fs = require('fs');
const { DOMParser, XMLSerializer } = require('@xmldom/xmldom');
const crypto = require('crypto');
const { C14nCanonicalization } = require('xml-crypto');

async function getZatcaInvoiceHash(xmlContent) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlContent, 'text/xml');

    // 1. MANUAL TAG REMOVAL (Replaces XSLT)
    const removeTags = (tagName, namespaceURI) => {
        const elements = doc.getElementsByTagNameNS(namespaceURI, tagName);
        for (let i = elements.length - 1; i >= 0; i--) {
            elements[i].parentNode.removeChild(elements[i]);
        }
    };

    // Remove UBLExtensions
    removeTags('UBLExtensions', 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2');

    // Remove Signature
    removeTags('Signature', 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2');

    // Remove AdditionalDocumentReference where ID is 'QR'
    const addRefs = doc.getElementsByTagNameNS('urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2', 'AdditionalDocumentReference');
    for (let i = addRefs.length - 1; i >= 0; i--) {
        const idElem = addRefs[i].getElementsByTagNameNS('urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2', 'ID')[0];
        if (idElem && idElem.textContent.trim() === 'QR') {
            addRefs[i].parentNode.removeChild(addRefs[i]);
        }
    }

    console.log("... Tags removed manually. Starting Canonicalization.");

    // 2. Canonicalization (C14N 1.0)
    const canon = new C14nCanonicalization();
    // We pass the documentElement to ensure we start at <Invoice>
    const canonicalXml = canon.process(doc.documentElement);

    // DEBUG: Save this to verify it looks like your "supposed to get" example
    fs.writeFileSync("./debug_final_canonical.xml", canonicalXml, 'utf8');

    // 3. SHA-256 Hashing
    const hashHex = crypto.createHash('sha256').update(canonicalXml, 'utf8').digest('hex');
    const hashBase64 = Buffer.from(hashHex, 'hex').toString('base64');

    return { hashHex, hashBase64 };
}

// --- MAIN EXECUTION ---
const filePath = "/opt/zatca-sdk/zatca-envoice-sdk-203/Apps/node_modules/SI_2026_00003.xml";

(async () => {
    try {
        console.log("--- ZATCA Compliant Hash Tool ---");
        const xmlContent = fs.readFileSync(filePath, 'utf8').trim();
        const result = await getZatcaInvoiceHash(xmlContent);

        console.log("\n================ RESULTS ================");
        console.log("BASE64 HASH: ", result.hashBase64);
        console.log("=========================================\n");
    } catch (err) {
        console.error("\n❌ ERROR:", err.message);
    }
})();

