# IoT Remote Medical Diagnosis System
## One Time Pad Cipher over MQTT Protocol — Full Python Simulation

> **Based on:** *"An IoT based remote medical diagnosis system using one time pad cipher over MQTT protocol"*  
> **Journal:** Scientific Reports (2025) 15:42117  
> **DOI:** https://doi.org/10.1038/s41598-025-26208-5  
> **Authors:** N. Rajesh Kumar, R. Bala Krishnan, Subramaniyaswamy V., G. Manikandan, Indragandhi V., Logesh Ravi

---

## Overview

This project is an **exact Python simulation** of the complete IoT-based remote medical diagnosis system described in the paper. Every component, algorithm, protocol, security analysis, and performance benchmark from the paper has been faithfully implemented and simulated.

---

## Project Structure

```
mqtt_otp_healthcare/
│
├── main.py                        # ← Run this — full simulation orchestrator
├── requirements.txt
│
├── core/
│   └── otp_cipher.py              # OTP cipher engine: TRNG, SHA-256, XOR encrypt/decrypt
│
├── broker/
│   └── mqtt_broker.py             # Full MQTT broker: QoS 0/1/2, ACL, sessions, handover
│
├── network/
│   └── clients.py                 # Patient (Publisher) + Doctor (Subscriber) IoT clients
│
├── security/
│   └── security_analyser.py       # BAN logic, differential, brute-force, trace, impersonation
│
├── analytics/
│   └── performance.py             # All performance benchmarks (Tables 4,11,12,13,16,17)
│
├── dashboard/
│   ├── dashboard.py               # Terminal dashboard with ASCII tables and charts
│   └── chart_generator.py         # Matplotlib chart generator (all paper figures)
│
├── data/
│   └── config.py                  # MQTT topics, message types, paper data constants
│
├── keys/                          # NVS-simulated OTP key indices per device
├── logs/                          # Generated reports (TXT + JSON)
└── data/                          # Generated chart images (PNG)
```

---

## How to Run — Step-by-Step Guide

This section walks you through every step needed to get the simulation running from scratch, whether you are on Linux, macOS, or Windows.

---

### Step 1 — Verify Python Version

This project requires **Python 3.9 or higher**. Open a terminal and check:

```bash
python --version
```

You should see something like `Python 3.12.3`. If Python is not installed, download it from https://www.python.org/downloads/ and install it before continuing.

---

### Step 2 — Download and Extract the Project

If you received the project as a ZIP file, extract it first:

```bash
unzip mqtt_otp_healthcare_simulation.zip
```

Then navigate into the project folder:

```bash
cd mqtt_otp_healthcare
```

Confirm you can see the project files:

```bash
ls
# Expected output:
# main.py  requirements.txt  README.md
# core/  broker/  network/  security/  analytics/  dashboard/  data/
```

---

### Step 3 — (Recommended) Create a Virtual Environment

Using a virtual environment keeps the project's dependencies isolated from your system Python. This is optional but strongly recommended.

```bash
# Create the virtual environment
python -m venv venv

# Activate it — Linux / macOS
source venv/bin/activate

# Activate it — Windows (Command Prompt)
venv\Scripts\activate.bat

# Activate it — Windows (PowerShell)
venv\Scripts\Activate.ps1
```

Your terminal prompt will change to show `(venv)` when the environment is active.

---

### Step 4 — Install Dependencies

All required packages are listed in `requirements.txt`. Install them with a single command:

```bash
pip install -r requirements.txt
```

This installs the following four packages:

| Package | Version Used | Purpose |
|---------|-------------|---------|
| `colorama` | 0.4.6+ | Coloured terminal output for the dashboard |
| `tabulate` | 0.9.0+ | ASCII table rendering for all paper tables |
| `matplotlib` | 3.7.0+ | Chart generation for all paper figures |
| `numpy` | 1.24.0+ | Numerical arrays for chart data |

If you prefer to install them individually:

```bash
pip install colorama tabulate matplotlib numpy
```

To confirm all packages installed correctly:

```bash
python -c "import colorama, tabulate, matplotlib, numpy; print('All dependencies OK')"
# Expected output: All dependencies OK
```

---

### Step 5 — Verify the Project Structure

Before running, make sure all source files are present. Run this check:

```bash
python -c "
import os
required = [
    'main.py',
    'core/otp_cipher.py',
    'broker/mqtt_broker.py',
    'network/clients.py',
    'security/security_analyser.py',
    'analytics/performance.py',
    'dashboard/dashboard.py',
    'dashboard/chart_generator.py',
    'data/config.py',
]
missing = [f for f in required if not os.path.exists(f)]
if missing:
    print('MISSING FILES:', missing)
else:
    print('All source files present — ready to run.')
"
```

You should see: `All source files present — ready to run.`

---

### Step 6 — Run the Full Simulation

Make sure you are inside the `mqtt_otp_healthcare/` directory, then run:

```bash
python main.py
```

The simulation will run automatically through all 8 phases and takes approximately **10–30 seconds** to complete on a standard machine. You will see live output scrolling in your terminal as each phase executes.

---

### Step 7 — Understand the Terminal Output

The simulation prints each phase sequentially. Here is what to expect:

```
════════════════════════════════════════════════════════
║         IoT Remote Medical Diagnosis System          ║
════════════════════════════════════════════════════════
  One Time Pad Cipher over MQTT Protocol — Python Simulation
  Simulation run: 2025-xx-xx xx:xx:xx

  Initializing system components...
[BROKER] broker-zone-a.emqx.io @ Zone-A (Ward 1) initialized
[BROKER] broker-zone-b.emqx.io @ Zone-B (Ward 2) initialized

==============================================================
  PHASE 1 — Registration & Connection
==============================================================
  Patient MC1: ✓ CONNECTED | Role: Patient | Broker: ...
  Doctor  MP1: ✓ CONNECTED | Role: General Physician
  ...

==============================================================
  PHASE 2 — OTP Cipher Demonstration (BP CHECK OK)
==============================================================
  Plaintext         : BP CHECK OK.
  OTP Key (hex)     : F285968BA3BA...
  Ciphertext (hex)  : B0D5B6C8EBFF...
  Base64 for MQTT   : sNW2yOv/BZL/ArQa
  Recovered plaintext: BP CHECK OK.
  Integrity check   : ✓ PASS
  ...

  [Phases 3 through 8 follow...]

  [Chart] Saved → fig12_qos_trip_time.png
  [Chart] Saved → table4_performance_comparison.png
  ... (10 charts total)

  Report saved : logs/simulation_report_YYYYMMDD_HHMMSS.txt
  Data saved   : logs/simulation_data_YYYYMMDD_HHMMSS.json
  Simulation complete. All outputs saved.
```

**What each phase produces in the terminal:**

| Phase | Terminal Output |
|-------|----------------|
| Phase 1 | Connection confirmations for 5 patients and 4 doctors with roles |
| Phase 2 | Full OTP trace — ASCII → Hex → Key → XOR → Base64 → Decrypt → Verify |
| Phase 3 | MQTT broker config table, ACL topic table, publish results, decrypted messages |
| Phase 4 | BAN logic proof, differential attack table, entropy stats, security comparison |
| Phase 5 | Computation time table, QoS chart, performance comparison, scalability table, latency table |
| Phase 6 | Broker handover confirmation showing Zone-A → Zone-B transfer |
| Phase 7 | Key incident response metrics table |
| Phase 8 | Retained messages and persistent session test case results |

---

### Step 8 — Find the Generated Output Files

After a successful run, three types of output are generated automatically.

#### Text Report and JSON Data (`logs/`)

```bash
ls logs/
# simulation_report_YYYYMMDD_HHMMSS.txt   ← full terminal output as plain text
# simulation_data_YYYYMMDD_HHMMSS.json    ← all simulation data as structured JSON
```

To read the text report:

```bash
# Linux / macOS
cat logs/simulation_report_*.txt | less

# Windows
type logs\simulation_report_*.txt | more
```

To inspect the JSON data (requires Python):

```bash
python -c "
import json, glob
f = sorted(glob.glob('logs/simulation_data_*.json'))[-1]
data = json.load(open(f))
print('Phases recorded:', list(data.keys()))
"
```

#### Chart Images (`data/`)

Ten PNG charts are generated, each corresponding to a figure or table in the paper:

```bash
ls data/*.png
```

| File | Paper Reference | Content |
|------|----------------|---------|
| `fig3_system_architecture.png` | Fig 3 | Full IoT healthcare system architecture diagram |
| `fig4_mqtt_message_flow.png` | Fig 4 | MQTT publisher → broker → subscriber flow |
| `fig12_qos_trip_time.png` | Fig 12 | QoS0 vs QoS1 average trip time vs packet loss |
| `table4_performance_comparison.png` | Table 4 | OTP+MQTT vs AES-128+MQTT side-by-side comparison |
| `table6_avalanche_effect.png` | Table 6 | Differential cryptanalysis — Avalanche Effect |
| `table11_computation_time.png` | Table 11 | Encryption / decryption / publication time by message length |
| `table14_security_heatmap.png` | Table 14 | Security properties heatmap across four schemes |
| `table15_trng_entropy.png` | Table 15 | ESP32 TRNG min-entropy and bitrate validation |
| `table16_scalability.png` | Table 16 | Throughput, latency, CPU, memory at 5/10/15 devices |
| `table17_latency_breakdown.png` | Table 17 | Stacked latency breakdown for 1 KB, 10 KB, 100 KB data |

Open any chart with your system image viewer:

```bash
# Linux
xdg-open data/fig12_qos_trip_time.png

# macOS
open data/fig12_qos_trip_time.png

# Windows
start data\fig12_qos_trip_time.png
```

#### Key Store (`keys/`)

Per-device NVS state files track OTP key indices, simulating ESP32 non-volatile flash memory. These persist between runs so that the same pad byte is never used twice.

```bash
ls keys/
# MC1_nvs.json  MC2_nvs.json  MC3_nvs.json  MC4_nvs.json  MC5_nvs.json
# MP1_nvs.json  MP2_nvs.json  MP3_nvs.json  MP4_nvs.json
# DEMO_ESP32_nvs.json  BENCH_ESP32_nvs.json  SEC_ANALYSIS_nvs.json

# Inspect a device's key state
python -c "import json; print(json.dumps(json.load(open('keys/MC1_nvs.json')), indent=2))"
```

---

### Step 9 — Run Individual Modules (Optional)

Each module can be tested independently for focused inspection without running the full simulation.

**Test only the OTP cipher engine:**

```bash
python -c "
from core.otp_cipher import OTPCipher
c = OTPCipher('TEST_DEVICE', 'keys')
enc = c.encrypt('BP CHECK OK')
dec = c.decrypt(enc['cipher_b64'], enc['key_bytes'], enc['integrity_hash_sha256'])
print('Plaintext :', enc['plaintext'])
print('Key (hex) :', enc['key_hex'])
print('Cipher    :', enc['cipher_b64'])
print('Recovered :', dec['plaintext'])
print('Integrity :', dec['integrity_ok'])
print('Enc time  :', enc['encryption_time_us'], 'us')
"
```

**Test the MQTT broker and ACL in isolation:**

```bash
python -c "
from broker.mqtt_broker import MQTTBroker, QoSLevel
broker = MQTTBroker('test-broker', 'Test-Zone')
broker.connect_client('P1', 'user_P1', 'pass_P1', 'Patient', clean_session=False)
broker.connect_client('D1', 'doc_D1',  'pass_D1', 'Cardiologist')
print(broker.get_broker_summary())
"
```

**Run the complete security analysis only:**

```bash
python -c "
from core.otp_cipher import OTPCipher
from security.security_analyser import SecurityAnalyser
cipher = OTPCipher('SEC_TEST', 'keys')
sa = SecurityAnalyser(cipher)
results = sa.run_all('PatientA', 'DoctorB')
ban = results['ban_logic']
print('BAN Auth proven:', ban['authentication_proven'])
for c in ban['conclusions']:
    print(' ', c)
bfa = results['brute_force_attack']
print('Key space:', bfa['key_space_size'])
print('Expected crack time:', bfa['expected_years'], 'years')
"
```

**Regenerate all charts from an existing simulation JSON:**

```bash
python dashboard/chart_generator.py
# Automatically reads the most recent logs/simulation_data_*.json
# and writes all 10 charts to data/
```

**Run the performance benchmarks only:**

```bash
python -c "
import sys; sys.path.insert(0,'.')
from core.otp_cipher import OTPCipher
from analytics.performance import CryptosystemBenchmark
from tabulate import tabulate
cipher = OTPCipher('BENCH', 'keys')
bench  = CryptosystemBenchmark(cipher)
rows   = bench.run()
print(tabulate(
    [[r['message_length_chars'], r['paper_enc_us'], r['measured_enc_us'],
      r['paper_dec_us'], r['measured_dec_us']] for r in rows],
    headers=['Msg Len','Paper Enc(us)','Measured Enc(us)','Paper Dec(us)','Measured Dec(us)'],
    tablefmt='grid'
))
"
```

---

### Step 10 — Clean Up and Reset (Optional)

To reset the simulation state entirely — clearing all generated keys, logs, and charts — and start fresh:

```bash
# Linux / macOS
rm -f keys/*.json
rm -f logs/*.txt logs/*.json
rm -f data/*.png

# Windows (Command Prompt)
del /Q keys\*.json
del /Q logs\*.txt logs\*.json
del /Q data\*.png
```

Then re-run `python main.py` for a completely clean simulation from scratch. New keys will be generated for all devices on the first message.

---

### Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `ModuleNotFoundError: No module named 'colorama'` | Dependencies not installed | Run `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'core'` | Wrong working directory | `cd mqtt_otp_healthcare` first, then run `python main.py` |
| `ModuleNotFoundError: No module named 'core.otp_cipher'` | Missing `__init__.py` files | Re-extract the ZIP; do not rename or move individual folders |
| `SyntaxError` on startup | Python version is below 3.9 | Run `python --version` and upgrade if needed |
| Charts not saved to `data/` | matplotlib not installed | Run `pip install matplotlib` then re-run |
| All charts are blank / white | Non-interactive backend issue | This is normal — charts are saved as PNG files, not displayed on screen |
| `PermissionError` on `keys/` or `logs/` | Directory write permissions | Run `chmod -R 755 keys/ logs/ data/` on Linux/macOS |
| Simulation appears to hang after Phase 5 | Large latency test (100 KB) takes a moment | Wait 15–20 seconds; it will complete |
| `KeyError` in JSON output | Outdated JSON from a previous version | Delete `logs/*.json` and re-run |

---

## What the Simulation Covers

### 8 Simulation Phases

| Phase | Description | Paper Section |
|-------|-------------|---------------|
| 1 | Registration & MQTT Connection | Section 3.3 (Steps 1–4) |
| 2 | OTP Cipher Demo (BP CHECK OK example) | Section: Encryption/Decryption Phase |
| 3 | MQTT Publish-Subscribe Communication | Section: Secure Message Transmission |
| 4 | Comprehensive Security Analysis | Section: Security Analysis |
| 5 | Performance Benchmarking | Section: Results and Discussion |
| 6 | Patient Mobility (Broker Handover) | Section: Secure Patient Mobility |
| 7 | Key Incident Response (Table 8) | Section: Key Management |
| 8 | Retained Messages & Sessions (Table 9) | Section: Network and Protocol Efficiency |

---

## Paper Tables Reproduced

| Table | Content | Module |
|-------|---------|--------|
| Table 1 | OTP notation symbols | `data/config.py` |
| Table 2 | Medical client ↔ practitioner allocation | `network/clients.py` |
| Table 3 | MQTT broker configuration | `broker/mqtt_broker.py` |
| Table 4 | Platform performance (OTP vs AES-128) | `analytics/performance.py` |
| Table 5 | Clinician topic subscriptions (ACL) | `broker/mqtt_broker.py` |
| Table 6 | Differential cryptanalysis (Avalanche) | `security/security_analyser.py` |
| Table 7 | BAN logic notation | `security/security_analyser.py` |
| Table 8 | Key incident response metrics | `main.py` Phase 7 |
| Table 9 | Retained messages & persistent sessions | `main.py` Phase 8 |
| Table 10 | Message communication types | `data/config.py` |
| Table 11 | Computation time of cryptosystem | `analytics/performance.py` |
| Table 12 | Packet loss vs QoS trip time | `analytics/performance.py` |
| Table 13 | MQTT packet statistics | `analytics/performance.py` |
| Table 14 | Security comparison (4 schemes) | `security/security_analyser.py` |
| Table 15 | ESP32 TRNG entropy validation | `core/otp_cipher.py` |
| Table 16 | Scalability (5/10/15 devices) | `analytics/performance.py` |
| Table 17 | Latency observations (1/10/100 KB) | `analytics/performance.py` |

---

## Paper Figures Reproduced

| Figure | Content | Output File |
|--------|---------|-------------|
| Fig 1  | IoT e-health MQTT architecture | `fig3_system_architecture.png` |
| Fig 3  | Overall healthcare system architecture | `fig3_system_architecture.png` |
| Fig 4  | MQTT implementation flow | `fig4_mqtt_message_flow.png` |
| Fig 12 | QoS0 vs QoS1 time lag | `fig12_qos_trip_time.png` |
| —      | Performance comparison bar chart | `table4_performance_comparison.png` |
| —      | Computation time line chart | `table11_computation_time.png` |
| —      | Security heatmap | `table14_security_heatmap.png` |
| —      | Scalability multi-line chart | `table16_scalability.png` |
| —      | Latency breakdown stacked bar | `table17_latency_breakdown.png` |
| —      | TRNG entropy validation | `table15_trng_entropy.png` |
| —      | Avalanche effect chart | `table6_avalanche_effect.png` |

---

## Architecture Details

### OTP Cipher Engine (`core/otp_cipher.py`)

Implements the paper's cryptosystem exactly:

**Encryption (Equation 2):**
```
Encrypted_msgp = E(secretmsgp ⊕ sk)
```

**Decryption (Equation 3):**
```
Decrypted_msgd = D(Ciphertext ⊕ sk)
```

**Key Generation (Equation 1):**
```
Xn+1 = L(Secretmsg)
If session1 == X0 → Sk = X0
If session2       → Sk = X1 ... Sk = Xn
```

- **ESP32 TRNG simulation**: OS entropy + timing jitter + SHA-256 DRBG conditioning
- **Min-entropy**: ~0.94 bits/bit (Table 15)
- **Key Index Manager**: Monotonic NVS tracking, prevents OTP key reuse across reboots
- **SHA-256 integrity hash**: appended to every encrypted payload

### MQTT Broker (`broker/mqtt_broker.py`)

Full MQTT v3.1.1 broker simulation:
- CONNECT/CONNACK, SUBSCRIBE/SUBACK, PUBLISH/PUBACK handshakes
- **QoS 0** (at most once), **QoS 1** (at least once), **QoS 2** (exactly once)
- **ACL** (Access Control Lists): topic-level, payload-transparent
- **Retained messages** (TC-01, TC-02 from Table 9)
- **Persistent sessions** (TC-03, TC-04 from Table 9)
- **Broker-broker handover** for patient mobility
- Fixed header (Fig 6) + Variable header (Fig 7) packet structure

### Security Analysis (`security/security_analyser.py`)

| Attack | Method | Result |
|--------|---------|--------|
| Differential | 1-bit toggle → Avalanche Effect | RESISTANT |
| Ciphertext-only | Entropy = 8 bits/byte, chi-sq uniform | RESISTANT |
| Known-plaintext | Each key unique, lengths vary | RESISTANT |
| Brute-force | Key space 2^160, infinite time | RESISTANT |
| Impersonation | Requires credentials + OTP key | RESISTANT |
| Trace | Broker can't read OTP payload | RESISTANT |

**BAN Logic** proves mutual authentication in 4 stages (Table 7 notation).

### Patient Mobility

When a patient moves between hospital zones:
1. Native broker exports: session state + ACL + topic subscriptions + callbacks
2. Target broker imports all state atomically
3. Patient can immediately publish on new broker without re-registration
4. OTP key sequence maintained across handover (TC-04)

---

## Performance Results

| Metric | OTP+MQTT (Proposed) | AES-128+MQTT | Improvement |
|--------|--------------------:|-------------:|------------:|
| Avg Latency | 85 ms | 132 ms | **35.6%** |
| Throughput | 145 msg/s | 112 msg/s | **29.5%** |
| CPU Usage | 18% | 27% | **33.3%** |
| Memory | 22 MB | 30 MB | **26.7%** |
| Enc Time | 1.8 ms | 6.4 ms | **71.9%** |

---

## Key Security Properties (Table 14)

| Property | Choi et al. | Xue et al. | Mohit et al. | **Proposed** |
|----------|:-----------:|:----------:|:------------:|:------------:|
| Differential attack | ✗ | ✓ | ✓ | **✓** |
| Ciphertext-only | ✗ | ✗ | ✓ | **✓** |
| Known plaintext | ✗ | ✗ | ✗ | **✓** |
| Brute force | ✓ | ✓ | ✓ | **✓** |
| Impersonation | ✗ | ✓ | ✗ | **✓** |
| Trace attack | ✓ | ✗ | ✗ | **✓** |

---

## Citation

```bibtex
@article{rajeshkumar2025iot,
  title={An IoT based remote medical diagnosis system using one time pad cipher over MQTT protocol},
  author={Rajesh Kumar, N. and Bala Krishnan, R. and Vairavasundaram, Subramaniyaswamy 
          and Manikandan, G. and Indragandhi, V. and Logesh Ravi},
  journal={Scientific Reports},
  volume={15},
  pages={42117},
  year={2025},
  doi={10.1038/s41598-025-26208-5}
}
```
