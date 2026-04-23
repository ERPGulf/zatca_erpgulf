function pkcs8ToECPrivateKey(pkcs8Base64) {
    const der = Buffer.from(pkcs8Base64, 'base64');

    // PKCS#8 layout for this 144-byte secp256k1 structure:
    //   [0..3]   30 81 8d 02        → outer SEQUENCE + version tag
    //   [4..5]   01 00              → version = 0
    //   [6..21]  30 10 ... OIDs ... → AlgorithmIdentifier
    //   [22..35] 04 76 30 74 02 01 01 04 20  → wrappers
    //   [36..67] <32 bytes>         → private scalar  ← HERE
    //   [68..81] a0 07 ... mid ...  → parameters + pubkey tag
    //   [79..143] <65 bytes>        → public point    ← HERE
    const privBytes = der.slice(36, 68);
    const pubBytes  = der.slice(-65);

    // SEC1 ECPrivateKey structure:
    //   30 74       → SEQUENCE (116 bytes)
    //   02 01 01    → version = 1
    //   04 20       → OCTET STRING (32 bytes private key)
    //   a0 07 06 05 2b8104000a  → [0] secp256k1 OID
    //   a1 44 03 42 00          → [1] public key BIT STRING
    const sec1Header = Buffer.from("30740201010420", "hex");
    const mid        = Buffer.from("a00706052b8104000aa144034200", "hex");

    const sec1 = Buffer.concat([sec1Header, privBytes, mid, pubBytes]);

    const b64 = sec1.toString('base64').match(/.{1,64}/g).join('\n');
    return `-----BEGIN EC PRIVATE KEY-----\n${b64}\n-----END EC PRIVATE KEY-----`;
}

// --- Usage ---
const pkcs8 = "MIGNAgEAMBAGByqGSM49AgEGBSuBBAAKBHYwdAIBAQQg4MtBlnP5Ur9GDAF9Y3+ACdM/CFwcOL9OYxfQzkMxKJegBwYFK4EEAAqhRANCAAQluWwCuaFoYSrVP3+VxW6S0bk6nQtbAWuj4XCvjzo5RwLdaC1iDwl6I++H5941hHzQIAQX1a6I3Pisw/YhpLDB";

console.log(pkcs8ToECPrivateKey(pkcs8));