const { execSync } = require('child_process');
const fs = require('fs');

const CONFIG_PATH = '/opt/zatca-sdk/zatca-envoice-sdk-203/Apps/csr-config.txt';

try {
    console.log("🚀 Restoring Original 138-byte MIGNA Structure...");

    // 1. Load Config
    const content = fs.readFileSync(CONFIG_PATH, 'utf8');
    const data = {};
    content.split('\n').forEach(line => {
        const parts = line.split('=');
        if (parts.length === 2) data[parts[0].trim()] = parts[1].trim();
    });

    const envValue = data['portal.type'] === 'Sandbox' ? 'TSTZATCA-Code-Signing' : 'ZATCA-Code-Signing';

    // 2. SSL Config
    //    - 1.3.6.1.4.1.311.20.2 must come FIRST (before subjectAltName)
    //    - Must use UTF8String, NOT PRINTABLESTRING
    const sslConfig = `
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req
[dn]
C = ${data['csr.country.name']}
OU = ${data['csr.organization.unit.name']}
O = ${data['csr.organization.name']}
CN = ${data['csr.common.name']}
[v3_req]
1.3.6.1.4.1.311.20.2 = ASN1:UTF8String:${envValue}
subjectAltName = dirName:alt_names
[alt_names]
SN = ${data['csr.serial.number']}
UID = ${data['csr.organization.identifier']}
title = ${data['csr.invoice.type']}
registeredAddress = ${data['csr.location.address']}
businessCategory = ${data['csr.industry.business.category']}
`;
    fs.writeFileSync('./temp_ssl.conf', sslConfig);

    // 3. Generate Key — secp256k1
    execSync('openssl ecparam -name secp256k1 -genkey -noout -out temp_key.pem');
    execSync('openssl ec -in temp_key.pem -outform DER -out temp_key.der', { stdio: 'ignore' });
    execSync('openssl req -new -sha256 -key temp_key.pem -config ./temp_ssl.conf -out tax_invoice.csr');

    // 4. Extract raw key bytes from DER
    const derBuffer = fs.readFileSync('./temp_key.der');
    const privBytes = derBuffer.slice(7, 39);   // 32-byte private scalar
    const pubBytes  = derBuffer.slice(-65);      // 65-byte uncompressed public point (04 xx...)

    // 5. Build PKCS#8 structure with secp256k1 OIDs (2b8104000a)
    //
    // Structure breakdown:
    //   30 81 8d          → SEQUENCE (141 bytes total)
    //     02 01 00        → INTEGER version = 0
    //     30 10           → SEQUENCE AlgorithmIdentifier (16 bytes)
    //       06 07 2a8648ce3d0201  → OID ecPublicKey
    //       06 05 2b8104000a      → OID secp256k1
    //     04 76           → OCTET STRING (118 bytes) wrapping ECPrivateKey
    //       30 74         → SEQUENCE ECPrivateKey (116 bytes)
    //         02 01 01    → INTEGER version = 1
    //         04 20       → OCTET STRING (32 bytes) ← privBytes go here
    //
    const mignaHeader = Buffer.from(
        "30818d020100301006072a8648ce3d020106052b8104000a047630740201010420",
        "hex"
    );

    //   [midSegment sits between privBytes and pubBytes]
    //     a0 07           → [0] EXPLICIT parameters (7 bytes)
    //       06 05 2b8104000a  → OID secp256k1
    //     a1 44           → [1] EXPLICIT publicKey (68 bytes)
    //       03 42 00      → BIT STRING (65 bytes uncompressed point follows)
    //
    const midSegment = Buffer.from(
        "a00706052b8104000aa144034200",
        "hex"
    );

    // Concat: header(33) + priv(32) + mid(14) + pub(65) = 144 bytes
    const finalBuffer = Buffer.concat([mignaHeader, privBytes, midSegment, pubBytes]);

    // 6. Output
    const privBase64 = finalBuffer.toString('base64');
    const csrBase64  = Buffer.from(fs.readFileSync('./tax_invoice.csr', 'utf8')).toString('base64');

    process.stdout.write("\n✅ MIGNA RESTORED\n");
    process.stdout.write("\n--- PRIVATE KEY ---\n" + privBase64 + "\n");
    process.stdout.write("\n--- CSR BASE64 ---\n"  + csrBase64  + "\n");

    // 7. Cleanup
    ['./temp_ssl.conf', './temp_key.pem', './temp_key.der', './tax_invoice.csr'].forEach(f => {
        if (fs.existsSync(f)) fs.unlinkSync(f);
    });

} catch (err) {
    console.error("\n❌ FAILED:", err.message);
}