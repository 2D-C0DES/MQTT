"""
OTP Cipher Engine
=================
Implements One Time Pad (OTP) encryption/decryption exactly as described in the paper:
  - Random key generation via hardware-simulated RNG conditioned with SHA-256
  - XOR-based encryption and decryption
  - Base64 encoding for MQTT transmission
  - Shannon perfect secrecy guarantee
  - NIST SP 800-90B entropy validation simulation
  - Key index monotonic tracking (ESP32 NVS simulation)
"""

import os
import hashlib
import hmac
import base64
import struct
import time
import json
import math
from typing import Tuple, Optional


# ─────────────────────────────────────────────
#  Hardware RNG Simulation (ESP32 TRNG model)
# ─────────────────────────────────────────────

class ESP32_TRNG:
    """
    Simulates the ESP32 hardware True Random Number Generator.
    
    On real ESP32: uses RF/clock-jitter noise from Wi-Fi/Bluetooth subsystem.
    Accessible via esp_random() / esp_fill_random().
    
    Simulation model:
      - Collects entropy from OS RNG (os.urandom)
      - Mixes with timing jitter (nanosecond timestamps)
      - Conditions output with SHA-256 DRBG (ratio 1:1)
      - Min-entropy ≈ 0.94 bits/bit  (Table 15 of paper)
      - Output bitrate: 50.0 Kbps,  effective 47.0 Kbps
    """

    def __init__(self, device_id: str = "ESP32_PUB"):
        self.device_id = device_id
        self.entropy_pool = b""
        self.bytes_generated = 0
        self._seed_pool()

    def _seed_pool(self):
        """Mix OS entropy + timing noise into pool."""
        ts_bytes = struct.pack(">Q", time.time_ns())
        os_entropy = os.urandom(64)
        device_bytes = self.device_id.encode()
        raw = os_entropy + ts_bytes + device_bytes
        self.entropy_pool = hashlib.sha256(raw).digest()

    def _mix_entropy(self, n_bytes: int) -> bytes:
        """Continuously refresh entropy pool (simulates RF noise feed)."""
        result = b""
        while len(result) < n_bytes:
            # Timing jitter
            jitter = struct.pack(">Q", time.time_ns())
            # OS entropy
            fresh = os.urandom(16)
            # Mix into pool
            self.entropy_pool = hashlib.sha256(
                self.entropy_pool + fresh + jitter
            ).digest()
            result += self.entropy_pool
        return result[:n_bytes]

    def esp_fill_random(self, n_bytes: int) -> bytes:
        """
        Simulate esp_fill_random(buf, len).
        Applies SHA-256 conditioning (DRBG ratio 1:1).
        """
        raw = self._mix_entropy(n_bytes)
        # SHA-256 conditioning
        conditioned = b""
        for i in range(0, len(raw), 32):
            block = raw[i:i+32]
            conditioned += hashlib.sha256(block).digest()
        result = conditioned[:n_bytes]
        self.bytes_generated += n_bytes
        return result

    def measure_min_entropy(self, sample_size: int = 1024) -> float:
        """
        Estimate min-entropy via frequency test (NIST SP 800-90B approximation).
        Paper reports ~0.94 bits/bit.
        """
        sample = self.esp_fill_random(sample_size)
        bits = bin(int.from_bytes(sample, 'big'))[2:].zfill(sample_size * 8)
        ones = bits.count('1')
        zeros = bits.count('0')
        total = len(bits)
        p_max = max(ones, zeros) / total
        min_entropy = -math.log2(p_max) if p_max > 0 else 8.0
        return min(min_entropy, 8.0)  # Cap at 8 bits/bit

    def get_stats(self) -> dict:
        min_ent = self.measure_min_entropy()
        return {
            "device_id": self.device_id,
            "entropy_source": "On-chip TRNG (RF/clock-jitter)",
            "environment": "Wi-Fi active",
            "raw_min_entropy_bits_per_bit": round(min_ent, 4),
            "conditioner": "SHA-256 DRBG, 1:1",
            "post_conditioning_entropy": round(min_ent, 4),
            "output_bitrate_kbps": 50.0,
            "entropy_throughput_kbps": round(50.0 * min_ent / 1.0, 1),
            "bytes_generated": self.bytes_generated
        }


# ─────────────────────────────────────────────
#  Key Index Manager (ESP32 NVS Simulation)
# ─────────────────────────────────────────────

class KeyIndexManager:
    """
    Simulates ESP32 Non-Volatile Storage (NVS) for monotonic key index tracking.
    
    Ensures:
      - Each pad byte is used EXACTLY ONCE
      - Key index persists across reboots (simulated with JSON file)
      - QoS retransmissions reuse same ciphertext, NOT same key
      - OTP correctness maintained (paper Section: MQTT QoS retransmission prevention)
    """

    def __init__(self, device_id: str, keys_dir: str = "keys"):
        self.device_id = device_id
        self.keys_dir = keys_dir
        self.nvs_file = os.path.join(keys_dir, f"{device_id}_nvs.json")
        os.makedirs(keys_dir, exist_ok=True)
        self._load_nvs()

    def _load_nvs(self):
        if os.path.exists(self.nvs_file):
            with open(self.nvs_file, 'r') as f:
                self.nvs = json.load(f)
        else:
            self.nvs = {
                "key_index": 0,
                "total_keys_consumed": 0,
                "pending_messages": {}   # msg_id -> {ciphertext, key_index}
            }
            self._save_nvs()

    def _save_nvs(self):
        with open(self.nvs_file, 'w') as f:
            json.dump(self.nvs, f, indent=2)

    def get_next_index(self, n_bytes: int) -> int:
        """Reserve n_bytes worth of key material. Returns starting index."""
        idx = self.nvs["key_index"]
        self.nvs["key_index"] += n_bytes
        self.nvs["total_keys_consumed"] += n_bytes
        self._save_nvs()
        return idx

    def store_pending(self, msg_id: str, ciphertext_b64: str, key_index: int):
        """Atomically write pending message record (NVS write simulation)."""
        self.nvs["pending_messages"][msg_id] = {
            "ciphertext_b64": ciphertext_b64,
            "key_index": key_index,
            "timestamp": time.time()
        }
        self._save_nvs()

    def get_pending(self, msg_id: str) -> Optional[dict]:
        return self.nvs["pending_messages"].get(msg_id)

    def clear_pending(self, msg_id: str):
        """Called after broker ACK received."""
        if msg_id in self.nvs["pending_messages"]:
            del self.nvs["pending_messages"][msg_id]
            self._save_nvs()

    def get_stats(self) -> dict:
        return {
            "device_id": self.device_id,
            "current_key_index": self.nvs["key_index"],
            "total_keys_consumed_bytes": self.nvs["total_keys_consumed"],
            "pending_messages": len(self.nvs["pending_messages"])
        }


# ─────────────────────────────────────────────
#  One Time Pad Cipher Core
# ─────────────────────────────────────────────

class OTPCipher:
    """
    One Time Pad cipher implementation following the paper exactly.

    Encryption (Eq. 2):
        Encrypted_msgp = E(secretmsgp ⊕ sk)

    Decryption (Eq. 3):
        Decrypted_msgd = D(Ciphertext ⊕ sk)

    Key generation (Eq. 1):
        Xn+1 = L(Secretmsg)
        If session1 == X0 → Sk = X0
        If session2      → Sk = X1 ... Sk = Xn

    SHA-256 integrity hash appended for data integrity check.
    Base64 encoding for MQTT wire transmission.
    """

    def __init__(self, device_id: str = "DEVICE", keys_dir: str = "keys"):
        self.trng = ESP32_TRNG(device_id)
        self.key_mgr = KeyIndexManager(device_id, keys_dir)
        self.session_count = 0
        self._session_keys = {}     # session_id -> key_bytes
        self.device_id = device_id

    # ── Key generation ──────────────────────────────────────

    def generate_session_key(self, message_length: int, session_id: str = None) -> Tuple[bytes, str, int]:
        """
        Generate a random key of exactly message_length bytes.
        Keys are produced by the ESP32 hardware RNG conditioned with SHA-256.
        
        Returns: (key_bytes, session_id, key_index)
        """
        if session_id is None:
            session_id = f"session{self.session_count}"
        
        key_bytes = self.trng.esp_fill_random(message_length)
        key_index = self.key_mgr.get_next_index(message_length)
        self._session_keys[session_id] = key_bytes
        self.session_count += 1
        return key_bytes, session_id, key_index

    def get_session_key(self, session_id: str) -> Optional[bytes]:
        return self._session_keys.get(session_id)

    # ── Encryption ──────────────────────────────────────────

    def encrypt(self, plaintext: str, session_id: str = None) -> dict:
        """
        Full encryption pipeline:
          1. Convert plaintext to bytes (UTF-8)
          2. Compute message length L
          3. Generate random key Xn of length L via TRNG+SHA256
          4. Convert plaintext and key to binary
          5. XOR: Ciphertext = Plaintext ⊕ Key
          6. Compute SHA-256 integrity hash
          7. Base64 encode for MQTT transmission

        Returns rich dict with all intermediate values (for audit/display).
        """
        t_start = time.perf_counter()

        # Step 1: ASCII/UTF-8 encoding
        plaintext_bytes = plaintext.encode('utf-8')
        L = len(plaintext_bytes)

        # Step 2: Hex representation
        plaintext_hex = plaintext_bytes.hex().upper()

        # Step 3: Generate random key
        session_id = session_id or f"session{self.session_count}"
        key_bytes, sid, key_index = self.generate_session_key(L, session_id)
        key_hex = key_bytes.hex().upper()

        # Step 4: XOR operation  (Equation 2)
        cipher_bytes = bytes(p ^ k for p, k in zip(plaintext_bytes, key_bytes))
        cipher_hex = cipher_bytes.hex().upper()

        # Step 5: SHA-256 integrity hash
        integrity_hash = hashlib.sha256(cipher_bytes).hexdigest().upper()

        # Step 6: Base64 encode for MQTT
        cipher_b64 = base64.b64encode(cipher_bytes).decode('ascii')

        t_enc = (time.perf_counter() - t_start) * 1_000_000  # µs

        result = {
            # Paper fields
            "plaintext": plaintext,
            "plaintext_ascii": [b for b in plaintext_bytes],
            "plaintext_hex": plaintext_hex,
            "plaintext_concat": plaintext_hex,
            "message_length_L": L,
            "session_id": sid,
            "key_index": key_index,
            "key_bytes": key_bytes,
            "key_hex": key_hex,
            "key_concat": key_hex,
            "cipher_bytes": cipher_bytes,
            "cipher_hex": cipher_hex,
            "cipher_concat": cipher_hex,
            "cipher_b64": cipher_b64,           # For MQTT wire transmission
            "integrity_hash_sha256": integrity_hash,
            # Timing
            "encryption_time_us": round(t_enc, 2),
            "encryption_time_ms": round(t_enc / 1000, 4),
        }
        return result

    def decrypt(self, cipher_b64: str, key_bytes: bytes, 
                expected_hash: str = None) -> dict:
        """
        Full decryption pipeline:
          1. Base64 decode received MQTT payload
          2. XOR with shared OTP key: Plaintext = Ciphertext ⊕ Key
          3. Verify SHA-256 integrity hash
          4. Convert bytes to ASCII/UTF-8

        Returns rich dict with all intermediate values.
        """
        t_start = time.perf_counter()

        # Step 1: Base64 → hex ciphertext
        cipher_bytes = base64.b64decode(cipher_b64)
        cipher_hex = cipher_bytes.hex().upper()

        # Step 2: XOR (Equation 3)
        if len(key_bytes) != len(cipher_bytes):
            raise ValueError(
                f"Key length ({len(key_bytes)}) != Ciphertext length ({len(cipher_bytes)}). "
                "OTP requires equal lengths."
            )
        plain_bytes = bytes(c ^ k for c, k in zip(cipher_bytes, key_bytes))
        plain_hex = plain_bytes.hex().upper()

        # Step 3: Integrity verification
        computed_hash = hashlib.sha256(cipher_bytes).hexdigest().upper()
        integrity_ok = True
        if expected_hash:
            integrity_ok = hmac.compare_digest(
                computed_hash, expected_hash.upper()
            )

        # Step 4: Bytes → ASCII
        try:
            plaintext = plain_bytes.decode('utf-8')
        except UnicodeDecodeError:
            plaintext = plain_bytes.decode('latin-1')

        t_dec = (time.perf_counter() - t_start) * 1_000_000  # µs

        result = {
            "cipher_b64_received": cipher_b64,
            "cipher_hex": cipher_hex,
            "key_hex": key_bytes.hex().upper(),
            "plain_hex": plain_hex,
            "plaintext": plaintext,
            "integrity_hash_computed": computed_hash,
            "integrity_ok": integrity_ok,
            "decryption_time_us": round(t_dec, 2),
            "decryption_time_ms": round(t_dec / 1000, 4),
        }
        return result

    def get_trng_stats(self) -> dict:
        return self.trng.get_stats()

    def get_key_stats(self) -> dict:
        return self.key_mgr.get_stats()
