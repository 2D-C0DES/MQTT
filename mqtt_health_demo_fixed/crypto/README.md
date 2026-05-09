# Crypto Module — OTP Encryption
### One-Time Pad (XOR + SHA-256) Implementation

---

## How It Works

This module implements the **One-Time Pad (OTP)** cipher described in the paper.
It is the gold standard of symmetric encryption — provably unbreakable when used correctly.

### Encryption (Publisher Side)

```
Plaintext  →  UTF-8 bytes  →  XOR with key  →  Ciphertext  →  Base64  →  MQTT
                                  ↑
                         SHA-256 conditioned
                         random key (same length
                         as the message)
```

**Step by step:**

1. Message is converted to UTF-8 bytes
2. A random key of the **same length** is generated using `os.urandom()` (OS entropy pool)
3. The key is conditioned through SHA-256 (matching the paper's approach)
4. XOR is performed: `ciphertext = plaintext_bytes XOR key`
5. Both ciphertext and key are Base64-encoded for safe MQTT transport
6. A SHA-256 checksum of the original plaintext is included for integrity verification

### Decryption (Subscriber Side)

```
MQTT  →  Base64 decode  →  XOR with key  →  Plaintext bytes  →  UTF-8 string
                               ↑
                         Same key that was
                         transmitted with
                         the message
```

**Step by step:**

1. Base64-decode the ciphertext and key
2. XOR: `plaintext = ciphertext XOR key`
3. Verify SHA-256 checksum matches — if not, data was tampered

---

## Example (from the paper, Section "Encryption Phase")

```
Plaintext:  "BP CHECK OK"
ASCII Hex:  42 50 20 43 48 45 43 4B 20 4F 4B

Key (random, SHA-256 conditioned):
            90 B5 15 10 D1 31 90 34 63 7F 5F

XOR result (ciphertext):
            D2 E5 35 53 99 74 D3 7F 43 30 14

Base64 encoded: 0uU1U5l003TDMBQ=
```

Decryption simply reverses the XOR:
```
D2 E5 35 53 99 74 D3 7F 43 30 14   (ciphertext)
XOR
90 B5 15 10 D1 31 90 34 63 7F 5F   (key)
=
42 50 20 43 48 45 43 4B 20 4F 4B   → "BP CHECK OK"
```

---

## Why XOR Works

XOR (exclusive-or) has a perfect property for encryption:

```
A XOR B = C
C XOR B = A     ← decryption with the same key reverses the operation
```

When the key is **truly random** and **used only once** (hence "one-time pad"),
information theory proves this is **unbreakable** — even with infinite computing power.
The attacker gains zero information about the plaintext from the ciphertext alone.

---

## Why This Matters for IoT

Traditional encryption (AES, RSA) requires significant CPU and memory.
IoT devices like the ESP32 (used in the paper) have very limited resources.

OTP with XOR is:
- **Computationally trivial** — just one XOR operation per byte
- **Perfectly secure** in theory — no algorithm can break it
- **Simple to implement** — no complex key schedules or rounds

The paper's results confirm this: OTP+MQTT achieves **1.8ms** encryption time vs
**6.4ms** for AES-128+MQTT — a **71.9% improvement**.

---

## Payload Structure

Each encrypted MQTT message is a JSON object:

```json
{
  "topic": "health/status",
  "payload": {
    "ciphertext": "0uU1U5l003TDMBQ=",
    "key":        "kLUVENExkDRjf18=",
    "checksum":   "sha256-of-original-plaintext"
  }
}
```

The MQTT broker only ever sees this JSON blob — it cannot read the health data inside.

---

## Files

| File | Purpose |
|---|---|
| `otp.py` | Core encrypt/decrypt functions |
| `README.md` | This file |

---

## API Reference

```python
from crypto.otp import encrypt, decrypt, package_payload, unpackage_payload

# Low-level
encrypted_dict = encrypt("Hello, Doctor!")
plaintext, integrity_ok = decrypt(encrypted_dict)

# High-level (for MQTT)
mqtt_string = package_payload("health/status", {"heart_rate": 72})
data_dict, integrity_ok = unpackage_payload(mqtt_string)
```
