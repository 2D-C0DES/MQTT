"""
otp.py — One-Time Pad (XOR) Encryption Module
==============================================
Implements the same OTP cipher described in the paper:
  Encrypted_msg = PlainText XOR SharedKey
  Decrypted_msg = CipherText XOR SharedKey

Each message gets a freshly generated random key of the same length.
The key is transmitted alongside the ciphertext (in a real deployment,
a secure key-exchange protocol would handle this separately).
"""

import os
import base64
import hashlib
import json


def generate_key(length: int) -> bytes:
    """
    Generate a cryptographically random key of `length` bytes.
    Uses os.urandom() which is backed by the OS entropy pool
    (analogous to the ESP32 hardware RNG used in the paper).
    """
    return os.urandom(length)


def xor_bytes(data: bytes, key: bytes) -> bytes:
    """
    XOR two byte strings together.
    Key must be at least as long as data (OTP requirement).
    """
    return bytes(d ^ k for d, k in zip(data, key))


def encrypt(plaintext: str) -> dict:
    """
    Encrypt a plaintext string using OTP (XOR with random key).

    Process (mirrors the paper's encryption phase):
      1. Convert plaintext → UTF-8 bytes
      2. Generate random key same length as message
      3. Condition key with SHA-256 (as paper uses SHA-256 conditioning)
      4. XOR plaintext bytes with key → ciphertext
      5. Base64-encode for safe MQTT transmission

    Returns a dict with:
      - 'ciphertext': Base64-encoded encrypted message
      - 'key': Base64-encoded key (for decryption)
      - 'checksum': SHA-256 of original plaintext (integrity check)
    """
    msg_bytes = plaintext.encode("utf-8")
    raw_key = generate_key(len(msg_bytes))

    # SHA-256 condition the key (as described in the paper)
    conditioned_key = _condition_key(raw_key, len(msg_bytes))

    ciphertext = xor_bytes(msg_bytes, conditioned_key)

    # SHA-256 checksum of original message for integrity verification
    checksum = hashlib.sha256(msg_bytes).hexdigest()

    return {
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
        "key": base64.b64encode(conditioned_key).decode("utf-8"),
        "checksum": checksum,
    }


def decrypt(payload: dict) -> tuple[str, bool]:
    """
    Decrypt a payload produced by encrypt().

    Returns:
      - (plaintext, True)  if checksum matches (integrity OK)
      - (plaintext, False) if checksum mismatch (data tampered)
    """
    ciphertext = base64.b64decode(payload["ciphertext"])
    key = base64.b64decode(payload["key"])
    expected_checksum = payload["checksum"]

    plaintext_bytes = xor_bytes(ciphertext, key)
    plaintext = plaintext_bytes.decode("utf-8")

    actual_checksum = hashlib.sha256(plaintext_bytes).hexdigest()
    integrity_ok = actual_checksum == expected_checksum

    return plaintext, integrity_ok


def _condition_key(raw_key: bytes, target_length: int) -> bytes:
    """
    Condition raw random bytes through SHA-256 to improve uniformity,
    matching the SHA-256 conditioning described in the paper.
    Expands or truncates to exactly target_length bytes.
    """
    conditioned = b""
    chunk = raw_key
    while len(conditioned) < target_length:
        chunk = hashlib.sha256(chunk).digest()
        conditioned += chunk
    return conditioned[:target_length]


def package_payload(topic: str, data: dict) -> str:
    """
    Encrypt a data dict and package it as a JSON string ready for MQTT publish.
    """
    plaintext = json.dumps(data)
    encrypted = encrypt(plaintext)
    packet = {
        "topic": topic,
        "payload": encrypted,
    }
    return json.dumps(packet)


def unpackage_payload(raw_message: str) -> tuple[dict, bool]:
    """
    Receive a raw MQTT message string, decrypt, and return (data_dict, integrity_ok).
    """
    packet = json.loads(raw_message)
    plaintext, integrity_ok = decrypt(packet["payload"])
    data = json.loads(plaintext)
    return data, integrity_ok
