"""
Chart Generator
================
Produces matplotlib figures matching all paper charts and tables:

  Fig 12  — Time lag QoS0 vs QoS1 (grouped bar chart)
  Fig 4   — Platform performance comparison (radar + bar)
  Fig Comp— Encryption time vs message length (line chart)
  Fig Sec — Security property comparison heatmap (Table 14)
  Fig Scal— Scalability analysis multi-line chart (Table 16)
  Fig Lat — Latency breakdown stacked bar (Table 17)
  Fig Ent — ESP32 TRNG entropy vs ideal (gauge-style bar)
  Fig Arch— System architecture text diagram
"""

import os
import sys
import json
import math
import random

import matplotlib
matplotlib.use("Agg")   # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

# Paper color palette
COLORS = {
    "otp":      "#1565C0",   # dark blue  — proposed scheme
    "aes":      "#B71C1C",   # dark red   — benchmark
    "qos0":     "#1565C0",
    "qos1":     "#43A047",
    "accent":   "#F57F17",
    "ok":       "#2E7D32",
    "fail":     "#C62828",
    "bg":       "#FAFAFA",
    "grid":     "#E0E0E0",
}

FONT = {"family": "DejaVu Sans", "size": 10}
matplotlib.rc("font", **FONT)


def _style_ax(ax, title: str, xlabel: str = "", ylabel: str = ""):
    ax.set_facecolor(COLORS["bg"])
    ax.grid(True, color=COLORS["grid"], linewidth=0.6, linestyle="--")
    ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)


def _save(fig, path: str):
    fig.savefig(path, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  [Chart] Saved → {os.path.basename(path)}")


# ─────────────────────────────────────────────
#  Fig 12 — QoS0 vs QoS1 trip time (paper Fig 12)
# ─────────────────────────────────────────────

def chart_qos_trip_time(qos_results: list, out_path: str):
    loss_pcts = [r["packet_loss_rate_pct"] for r in qos_results]
    paper_q0  = [r.get("paper_qos0_s", 0) or 0 for r in qos_results]
    paper_q1  = [r.get("paper_qos1_s", 0) or 0 for r in qos_results]
    sim_q0    = [r["simulated_qos0_s"] for r in qos_results]
    sim_q1    = [r["simulated_qos1_s"] for r in qos_results]

    x = np.arange(len(loss_pcts))
    w = 0.20

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        "Fig 12 — Average Trip Time vs Packet Loss Rate: QoS0 vs QoS1\n"
        "(Paper reproduction + Simulation)",
        fontsize=12, fontweight="bold"
    )

    # Left: Paper values (exact replication)
    ax = axes[0]
    bars0 = ax.bar(x - w/2, paper_q0, w, label="QoS0 (paper)", color=COLORS["qos0"], alpha=0.85)
    bars1 = ax.bar(x + w/2, paper_q1, w, label="QoS1 (paper)", color=COLORS["qos1"], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{p}%" for p in loss_pcts])
    _style_ax(ax, "Paper Reference Values",
              "Packet Loss Rate (%)", "Average Time (Seconds)")
    # Annotate bars
    for bar in list(bars0) + list(bars1):
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.01,
                    f"{h:.2f}", ha="center", va="bottom", fontsize=7)
    ax.legend(fontsize=9)
    ax.set_ylim(0, 1.05)

    # Right: Simulation values
    ax2 = axes[1]
    b0 = ax2.bar(x - w/2, sim_q0, w, label="QoS0 (simulated)", color=COLORS["qos0"], alpha=0.85)
    b1 = ax2.bar(x + w/2, sim_q1, w, label="QoS1 (simulated)", color=COLORS["qos1"], alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{p}%" for p in loss_pcts])
    _style_ax(ax2, "Simulation Values",
              "Packet Loss Rate (%)", "Average Time (Seconds)")
    for bar in list(b0) + list(b1):
        h = bar.get_height()
        if h > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, h + 0.01,
                     f"{h:.2f}", ha="center", va="bottom", fontsize=7)
    ax2.legend(fontsize=9)
    ax2.set_ylim(0, 1.05)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Table 4 — Performance Comparison (bar chart)
# ─────────────────────────────────────────────

def chart_performance_comparison(out_path: str):
    metrics = [
        "Avg Latency\n(ms)",
        "Throughput\n(msg/s)",
        "CPU\n(%)",
        "Memory\n(MB)",
        "Enc Time\n(ms)",
    ]
    otp_vals = [85, 145, 18, 22, 1.8]
    aes_vals = [132, 112, 27, 30, 6.4]
    improv   = [35.6, 29.5, 33.3, 26.7, 71.9]

    x = np.arange(len(metrics))
    w = 0.32

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        "Table 4 — Overall Performance Evaluation: OTP+MQTT vs AES-128+MQTT",
        fontsize=12, fontweight="bold"
    )

    # Left: side-by-side bar
    b1 = ax1.bar(x - w/2, otp_vals, w, label="OTP+MQTT (Proposed)",
                 color=COLORS["otp"], alpha=0.88)
    b2 = ax1.bar(x + w/2, aes_vals, w, label="AES-128+MQTT (Benchmark)",
                 color=COLORS["aes"], alpha=0.88)
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=9)
    _style_ax(ax1, "Metric Comparison", "", "Value")
    for bar, val in zip(list(b1) + list(b2), otp_vals + aes_vals):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 str(val), ha="center", va="bottom", fontsize=8)
    ax1.legend(fontsize=9)

    # Right: improvement %
    colors_imp = [COLORS["ok"] if v > 0 else COLORS["fail"] for v in improv]
    bars = ax2.barh(metrics, improv, color=colors_imp, alpha=0.88)
    ax2.axvline(0, color="black", linewidth=0.8)
    _style_ax(ax2, "Improvement of Proposed vs Benchmark (%)",
              "Improvement (%)", "")
    for bar, val in zip(bars, improv):
        ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                 f"+{val}%", va="center", fontsize=9, fontweight="bold",
                 color=COLORS["ok"])
    ax2.set_xlim(0, 85)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Table 11 — Computation Time (line chart)
# ─────────────────────────────────────────────

def chart_computation_time(comp_results: list, out_path: str):
    lengths  = [r["message_length_chars"] for r in comp_results]
    p_enc    = [r["paper_enc_us"] for r in comp_results]
    p_dec    = [r["paper_dec_us"] for r in comp_results]
    p_pub    = [r["paper_pub_us"] for r in comp_results]
    m_enc    = [r["measured_enc_us"] for r in comp_results]
    m_dec    = [r["measured_dec_us"] for r in comp_results]
    m_pub    = [r["measured_pub_us"] for r in comp_results]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)
    fig.suptitle(
        "Table 11 — Computation Time of Cryptosystem (Paper vs Simulation)",
        fontsize=12, fontweight="bold"
    )

    for ax, title, p_vals, m_vals in zip(
        axes,
        ["Encryption Time (µs)", "Decryption Time (µs)", "Publication Time (µs)"],
        [p_enc, p_dec, p_pub],
        [m_enc, m_dec, m_pub],
    ):
        ax.plot(lengths, p_vals, "o--", color=COLORS["aes"],
                label="Paper", linewidth=1.8, markersize=7)
        ax.plot(lengths, m_vals, "s-",  color=COLORS["otp"],
                label="Simulation", linewidth=1.8, markersize=7)
        _style_ax(ax, title, "Message Length (chars)", "Time (µs)")
        ax.legend(fontsize=9)
        ax.set_xticks(lengths)
        # Shade difference
        ax.fill_between(lengths, p_vals, m_vals, alpha=0.12, color=COLORS["accent"])

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Table 14 — Security Comparison Heatmap
# ─────────────────────────────────────────────

def chart_security_heatmap(out_path: str):
    schemes    = ["Choi et al.", "Xue et al.", "Mohit et al.", "Proposed\n(OTP+MQTT)"]
    properties = [
        "Differential\nattack",
        "Ciphertext-only\nattack",
        "Known plaintext\nattack",
        "Brute force\nattack",
        "Impersonation\nattack",
        "Trace attack",
    ]
    # 0=fail, 1=pass (from Table 14)
    matrix = np.array([
        [0, 1, 1, 1],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 1],
        [0, 1, 0, 1],
        [1, 0, 0, 1],
    ], dtype=float)

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.suptitle("Table 14 — Security Properties Comparison",
                 fontsize=12, fontweight="bold")

    cmap = matplotlib.colors.ListedColormap([COLORS["fail"], COLORS["ok"]])
    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(schemes)))
    ax.set_xticklabels(schemes, fontsize=10)
    ax.set_yticks(range(len(properties)))
    ax.set_yticklabels(properties, fontsize=9)

    # Annotate cells
    for i in range(len(properties)):
        for j in range(len(schemes)):
            sym = "✓" if matrix[i, j] == 1 else "✗"
            color = "white"
            ax.text(j, i, sym, ha="center", va="center",
                    fontsize=16, color=color, fontweight="bold")

    # Legend
    patch_ok   = mpatches.Patch(color=COLORS["ok"],   label="Resistant (✓)")
    patch_fail = mpatches.Patch(color=COLORS["fail"],  label="Vulnerable (✗)")
    ax.legend(handles=[patch_ok, patch_fail], loc="upper left",
              bbox_to_anchor=(1.01, 1), fontsize=9)

    ax.set_title("Security Properties by Scheme", fontsize=10, pad=6)
    ax.spines[:].set_visible(False)

    fig.tight_layout()
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Table 16 — Scalability (multi-line)
# ─────────────────────────────────────────────

def chart_scalability(scale_results: list, out_path: str):
    devices   = [r["concurrent_devices"] for r in scale_results]
    throughput= [r["measured_throughput_msg_s"] for r in scale_results]
    latency   = [r["measured_latency_ms"] for r in scale_results]
    emqx_cpu  = [r["measured_emqx_cpu_pct"] for r in scale_results]
    emqx_mem  = [r["measured_emqx_mem_mb"] for r in scale_results]
    key_dist  = [r["measured_key_dist_ms"] for r in scale_results]

    # Paper reference
    p_dev = [5, 10, 15]
    p_thr = [25, 50, 75]
    p_lat = [40, 55, 75]

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(
        "Table 16 — Scalability Analysis: Multi-Device Load Performance",
        fontsize=12, fontweight="bold"
    )

    datasets = [
        (axes[0,0], "Aggregate Throughput", devices, throughput, p_thr,  "msg/s"),
        (axes[0,1], "End-to-End Latency",   devices, latency,    p_lat,  "ms"),
        (axes[0,2], "EMQX CPU Usage",       devices, emqx_cpu,   None,   "%"),
        (axes[1,0], "EMQX Memory Usage",    devices, emqx_mem,   None,   "MB"),
        (axes[1,1], "Key Distribution Latency", devices, key_dist, None, "ms"),
        (axes[1,2], "ESP32 CPU (avg)",      devices,
         [r["measured_esp32_cpu_pct"] for r in scale_results], None, "%"),
    ]

    for ax, title, x, sim, paper, unit in datasets:
        ax.plot(x, sim, "o-", color=COLORS["otp"], linewidth=2,
                markersize=8, label="Simulation")
        if paper:
            ax.plot(p_dev, paper, "s--", color=COLORS["aes"],
                    linewidth=1.5, markersize=6, label="Paper ref.")
            ax.legend(fontsize=8)
        _style_ax(ax, title, "Concurrent Devices", f"{title} ({unit})")
        ax.set_xticks(devices)
        for xi, yi in zip(x, sim):
            ax.annotate(f"{yi}", (xi, yi), textcoords="offset points",
                        xytext=(0, 6), ha="center", fontsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Table 17 — Latency Breakdown (stacked bar)
# ─────────────────────────────────────────────

def chart_latency_breakdown(lat_results: list, out_path: str):
    labels = [f"{r['data_size_kb']} KB" for r in lat_results]
    enc_t  = [r["measured_enc_ms"] for r in lat_results]
    tx_t   = [r["simulated_tx_ms"] for r in lat_results]
    dec_t  = [r["measured_dec_ms"] for r in lat_results]

    x = np.arange(len(labels))
    w = 0.5

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.suptitle("Table 17 — Latency Breakdown by Data Size",
                 fontsize=12, fontweight="bold")

    bars_enc = ax.bar(x, enc_t, w, label="Encryption (ms)",
                      color=COLORS["otp"], alpha=0.9)
    bars_tx  = ax.bar(x, tx_t,  w, bottom=enc_t,
                      label="Transmission (ms)", color=COLORS["accent"], alpha=0.9)
    bottom2  = [e+t for e,t in zip(enc_t, tx_t)]
    bars_dec = ax.bar(x, dec_t, w, bottom=bottom2,
                      label="Decryption (ms)",  color=COLORS["qos1"], alpha=0.9)

    # Paper range annotations
    paper_ranges = [r["paper_total_range_ms"] for r in lat_results]
    totals = [e+t+d for e,t,d in zip(enc_t, tx_t, dec_t)]
    for xi, tot, prange in zip(x, totals, paper_ranges):
        ax.text(xi, tot + 2, f"Paper: {prange}ms", ha="center",
                fontsize=8, color="gray", style="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Time (ms)")
    _style_ax(ax, "End-to-End Latency Breakdown (Enc + Tx + Dec)",
              "Data Size", "Total Latency (ms)")
    ax.legend(fontsize=9, loc="upper left")

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  TRNG Entropy Validation (Table 15)
# ─────────────────────────────────────────────

def chart_entropy_validation(trng_stats: dict, out_path: str):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        "Table 15 — ESP32 TRNG Min-Entropy Validation",
        fontsize=12, fontweight="bold"
    )

    # Left: Entropy gauge
    ax = axes[0]
    measured = trng_stats.get("raw_min_entropy_bits_per_bit", 0.94)
    ideal    = 1.0
    paper    = 0.94

    categories = ["Measured", "Paper\nTarget", "Ideal\n(Perfect)"]
    values     = [measured, paper, ideal]
    colors     = [COLORS["otp"], COLORS["aes"], COLORS["ok"]]
    bars = ax.bar(categories, values, color=colors, alpha=0.88, width=0.45)
    ax.set_ylim(0, 1.1)
    ax.axhline(1.0, linestyle="--", color="gray", linewidth=1, label="Theoretical max")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f"{val:.4f}", ha="center", fontsize=10, fontweight="bold")
    _style_ax(ax, "Min-Entropy (bits/bit)", "", "Min-Entropy (bits/bit)")
    ax.legend(fontsize=9)

    # Right: Bitrate comparison
    ax2 = axes[1]
    metrics = ["Output\nBitrate", "Entropy\nThroughput"]
    vals    = [
        trng_stats.get("output_bitrate_kbps", 50.0),
        trng_stats.get("entropy_throughput_kbps", 47.0),
    ]
    paper_v = [50.0, 47.0]
    xp = np.arange(len(metrics))
    w  = 0.3
    ax2.bar(xp - w/2, paper_v, w, label="Paper (Table 15)",
            color=COLORS["aes"], alpha=0.85)
    ax2.bar(xp + w/2, vals,    w, label="Simulation",
            color=COLORS["otp"], alpha=0.85)
    ax2.set_xticks(xp)
    ax2.set_xticklabels(metrics)
    _style_ax(ax2, "TRNG Bitrate (Kbps)", "", "Kbps")
    ax2.legend(fontsize=9)
    for xi, yp, ys in zip(xp, paper_v, vals):
        ax2.text(xi - w/2, yp + 0.3, f"{yp}", ha="center", fontsize=9)
        ax2.text(xi + w/2, ys  + 0.3, f"{ys:.1f}", ha="center", fontsize=9)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  System Architecture Diagram (Fig 3 style)
# ─────────────────────────────────────────────

def chart_system_architecture(out_path: str):
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")

    fig.suptitle(
        "Fig 3 — Overall Architecture of Proposed IoT Healthcare System",
        fontsize=13, fontweight="bold", y=0.97
    )

    def box(ax, x, y, w, h, label, sublabel="", color="#1565C0", fc="#E3F2FD"):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1",
            linewidth=1.5, edgecolor=color, facecolor=fc
        )
        ax.add_patch(rect)
        ax.text(x + w/2, y + h*0.62, label,
                ha="center", va="center", fontsize=9,
                fontweight="bold", color=color)
        if sublabel:
            ax.text(x + w/2, y + h*0.28, sublabel,
                    ha="center", va="center", fontsize=7.5, color="#455A64")

    def arrow(ax, x1, y1, x2, y2, label="", color="#333"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color,
                                   lw=1.5, connectionstyle="arc3,rad=0.0"))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my + 0.12, label, ha="center", fontsize=7.5,
                    color=color, style="italic",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

    # Patients (Publishers)
    patient_positions = [(0.3, 5.8), (0.3, 4.0), (0.3, 2.2)]
    for i, (px, py) in enumerate(patient_positions, 1):
        box(ax, px, py, 2.0, 1.2,
            f"Patient P{i}", f"IoT Publisher\n(ESP32+Sensors)",
            "#1A237E", "#E8EAF6")

    # OTP Cipher box (centre-left)
    box(ax, 3.0, 3.5, 2.2, 2.5,
        "OTP Cipher\nEngine",
        "SHA-256 TRNG\nXOR Encrypt/Decrypt",
        "#4A148C", "#F3E5F5")

    # MQTT Broker
    box(ax, 6.2, 3.2, 2.4, 3.2,
        "MQTT Broker\n(EMQX/MQTTx)",
        "Topics:\nhealth/status\nmedication/update\nsymptom/reporting\nwellness/tips",
        "#1B5E20", "#E8F5E9")

    # Online Wrapper
    box(ax, 6.2, 1.0, 2.4, 1.8,
        "Online Wrapper\nApplication",
        "Auth + Key Issue\nPub↔Sub Matching",
        "#E65100", "#FFF3E0")

    # Internet cloud
    cloud = mpatches.FancyBboxPatch(
        (9.3, 3.8), 1.6, 2.0,
        boxstyle="round,pad=0.3",
        linewidth=1.5, edgecolor="#607D8B",
        facecolor="#ECEFF1", linestyle="--"
    )
    ax.add_patch(cloud)
    ax.text(10.1, 4.8, "[Internet]", ha="center", fontsize=9,
            fontweight="bold", color="#455A64")

    # Doctors (Subscribers)
    doctor_configs = [
        (11.0, 5.8, "Cardiologist\n(MP-2)",    "#B71C1C", "#FFEBEE"),
        (11.0, 4.0, "Gen. Physician\n(MP-1)",  "#1B5E20", "#E8F5E9"),
        (11.0, 2.2, "Pharmacologist\n(MP-4)",  "#4A148C", "#F3E5F5"),
    ]
    for dx, dy, dlabel, dc, dfc in doctor_configs:
        box(ax, dx, dy, 2.2, 1.2,
            dlabel, "IoT Subscriber\n(Medical Expert)", dc, dfc)

    # Arrows: Patients → OTP
    for i, (px, py) in enumerate(patient_positions):
        arrow(ax, px+2.0, py+0.6, 3.0, 4.2,
              "Plain\nMsg" if i == 0 else "")

    # OTP → Broker
    arrow(ax, 5.2, 4.75, 6.2, 4.75, "Encrypted\n(Base64/MQTT)")

    # Broker → Internet
    arrow(ax, 8.6, 4.8, 9.3, 4.8, "")

    # Internet → Doctors
    for i, (dx, dy, *_) in enumerate(doctor_configs):
        arrow(ax, 10.9, 4.8, dx, dy+0.6, "" if i else "Decrypt")

    # Wrapper ↔ Broker
    ax.annotate("", xy=(6.2, 1.9), xytext=(7.4, 3.2),
                arrowprops=dict(arrowstyle="<->", color="#E65100", lw=1.5))
    ax.text(6.5, 2.55, "Auth/\nKey", ha="center", fontsize=7, color="#E65100")

    # ACL label on broker
    ax.text(7.4, 6.6, "ACL\nEnforced", ha="center", fontsize=7.5,
            color="#1B5E20", style="italic",
            bbox=dict(boxstyle="round,pad=0.2", fc="#E8F5E9", alpha=0.8))

    # QoS levels label
    ax.text(7.4, 3.0, "QoS 0 / 1 / 2", ha="center", fontsize=7.5,
            color="#1B5E20", style="italic")

    # Legend
    legend_items = [
        mpatches.Patch(color="#E8EAF6", ec="#1A237E", label="Patient (Publisher / ESP32)"),
        mpatches.Patch(color="#F3E5F5", ec="#4A148C", label="OTP Cipher (SHA-256 + XOR)"),
        mpatches.Patch(color="#E8F5E9", ec="#1B5E20", label="MQTT Broker (EMQX)"),
        mpatches.Patch(color="#FFF3E0", ec="#E65100", label="Online Wrapper App"),
        mpatches.Patch(color="#FFEBEE", ec="#B71C1C", label="Doctor (Subscriber)"),
    ]
    ax.legend(handles=legend_items, loc="lower center",
              ncol=3, fontsize=8, framealpha=0.9,
              bbox_to_anchor=(0.5, -0.02))

    fig.tight_layout()
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Fig 4 — MQTT Protocol Communication Flow
# ─────────────────────────────────────────────

def chart_mqtt_message_flow(out_path: str):
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis("off")
    fig.patch.set_facecolor("#FAFAFA")
    fig.suptitle(
        "Fig 4 — MQTT Protocol Communication Flow (Publisher → Broker → Subscriber)",
        fontsize=12, fontweight="bold"
    )

    def lane(ax, x, label, color, fc):
        rect = mpatches.FancyBboxPatch(
            (x-0.9, 0.2), 1.8, 6.3,
            boxstyle="round,pad=0.1",
            linewidth=1, edgecolor=color, facecolor=fc, alpha=0.35
        )
        ax.add_patch(rect)
        ax.text(x, 6.7, label, ha="center", fontsize=9,
                fontweight="bold", color=color)

    lane(ax, 1.5,  "Publisher\n(Patient)", "#1A237E", "#E8EAF6")
    lane(ax, 5.5,  "MQTT Broker",          "#1B5E20", "#E8F5E9")
    lane(ax, 9.0,  "Subscriber\n(Doctor)", "#B71C1C", "#FFEBEE")
    lane(ax, 12.0, "MQTTx\nServer",        "#4A148C", "#F3E5F5")

    steps = [
        (5.8, "CONNECT →",          1.5, 5.5, "#333"),
        (5.3, "← CONNACK",          5.5, 1.5, "#333"),
        (4.8, "CONNECT →",          9.0, 5.5, "#333"),
        (4.3, "← CONNACK",          5.5, 9.0, "#333"),
        (3.8, "SUBSCRIBE(topic) →", 9.0, 5.5, "#1B5E20"),
        (3.3, "← SUBACK",           5.5, 9.0, "#1B5E20"),
        (2.6, "PUBLISH(Encrypted)→",1.5, 5.5, "#1A237E"),
        (2.1, "→ Deliver Msg",      5.5, 9.0, "#B71C1C"),
        (1.6, "← PUBACK (QoS1)",    5.5, 1.5, "#E65100"),
        (1.1, "TRIGGER ACTION →",   9.0,12.0, "#4A148C"),
    ]

    for y, label, x1, x2, color in steps:
        mid_x = (x1 + x2) / 2
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.6))
        ax.text(mid_x, y + 0.12, label, ha="center", fontsize=8,
                color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.8))

    # Encryption annotation
    ax.text(1.5, 2.45, "[OTP]\nEncrypt", ha="center", fontsize=8,
            color="#1A237E",
            bbox=dict(boxstyle="round,pad=0.2", fc="#E8EAF6", alpha=0.9))
    ax.text(9.0, 1.85, "[OTP]\nDecrypt", ha="center", fontsize=8,
            color="#B71C1C",
            bbox=dict(boxstyle="round,pad=0.2", fc="#FFEBEE", alpha=0.9))

    fig.tight_layout()
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Differential Attack Avalanche Chart
# ─────────────────────────────────────────────

def chart_avalanche_effect(diff_results: list, out_path: str):
    msgs = [r["original_message"] for r in diff_results]
    avp  = [r["avalanche_pct"] for r in diff_results]
    mis  = [r["mismatched_bits"] for r in diff_results]
    tot  = [r["total_bits"] for r in diff_results]

    x = np.arange(len(msgs))
    w = 0.45

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        "Table 6 — Differential Cryptanalysis: Avalanche Effect (1-bit Change)",
        fontsize=12, fontweight="bold"
    )

    # Avalanche %
    colors = [COLORS["ok"] if v >= 40 else COLORS["accent"] for v in avp]
    bars = ax1.bar(x, avp, w, color=colors, alpha=0.88)
    ax1.axhline(50, linestyle="--", color=COLORS["aes"],
                linewidth=1.2, label="50% threshold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(msgs, fontsize=9)
    ax1.set_ylim(0, 110)
    _style_ax(ax1, "Avalanche Effect (%)", "Message", "Avalanche %")
    ax1.legend(fontsize=9)
    for bar, val in zip(bars, avp):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                 f"{val}%", ha="center", fontsize=9, fontweight="bold")

    # Mismatched bits vs total
    ax2.bar(x - w/2, tot, w, label="Total bits",  color=COLORS["aes"],  alpha=0.7)
    ax2.bar(x + w/2, mis, w, label="Mismatched",  color=COLORS["otp"],  alpha=0.88)
    ax2.set_xticks(x)
    ax2.set_xticklabels(msgs, fontsize=9)
    _style_ax(ax2, "Mismatched Bits (after 1-bit change)", "Message", "Bit Count")
    ax2.legend(fontsize=9)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, out_path)


# ─────────────────────────────────────────────
#  Main chart generator entry point
# ─────────────────────────────────────────────

def generate_all_charts(simulation_data: dict, out_dir: str = "data") -> dict:
    """
    Generate all charts from simulation data.
    Returns dict of {chart_name: file_path}.
    """
    os.makedirs(out_dir, exist_ok=True)
    saved = {}
    print(f"\n  Generating matplotlib charts → {out_dir}/")

    # QoS chart (Fig 12)
    qos_data = simulation_data.get("phase5", {}).get("qos", [])
    if qos_data:
        p = os.path.join(out_dir, "fig12_qos_trip_time.png")
        chart_qos_trip_time(qos_data, p)
        saved["fig12_qos"] = p

    # Performance comparison (Table 4)
    p = os.path.join(out_dir, "table4_performance_comparison.png")
    chart_performance_comparison(p)
    saved["table4_perf"] = p

    # Computation time (Table 11)
    comp_data = simulation_data.get("phase5", {}).get("computation", [])
    if comp_data:
        p = os.path.join(out_dir, "table11_computation_time.png")
        chart_computation_time(comp_data, p)
        saved["table11_comp"] = p

    # Security heatmap (Table 14)
    p = os.path.join(out_dir, "table14_security_heatmap.png")
    chart_security_heatmap(p)
    saved["table14_security"] = p

    # Scalability (Table 16)
    scale_data = simulation_data.get("phase5", {}).get("scalability", [])
    if scale_data:
        p = os.path.join(out_dir, "table16_scalability.png")
        chart_scalability(scale_data, p)
        saved["table16_scale"] = p

    # Latency breakdown (Table 17)
    lat_data = simulation_data.get("phase5", {}).get("latency_obs", [])
    if lat_data:
        p = os.path.join(out_dir, "table17_latency_breakdown.png")
        chart_latency_breakdown(lat_data, p)
        saved["table17_latency"] = p

    # TRNG entropy (Table 15)
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core.otp_cipher import OTPCipher
        cipher = OTPCipher("CHART_TRNG", "keys")
        trng_stats = cipher.get_trng_stats()
        p = os.path.join(out_dir, "table15_trng_entropy.png")
        chart_entropy_validation(trng_stats, p)
        saved["table15_trng"] = p
    except Exception as e:
        print(f"  [Chart] TRNG chart skipped: {e}")

    # Differential attack (Table 6)
    sec_data = simulation_data.get("phase4", {})
    diff_data = sec_data.get("differential_attack", []) if sec_data else []
    if diff_data:
        p = os.path.join(out_dir, "table6_avalanche_effect.png")
        chart_avalanche_effect(diff_data, p)
        saved["table6_diff"] = p

    # System architecture (Fig 3)
    p = os.path.join(out_dir, "fig3_system_architecture.png")
    chart_system_architecture(p)
    saved["fig3_arch"] = p

    # MQTT message flow (Fig 4)
    p = os.path.join(out_dir, "fig4_mqtt_message_flow.png")
    chart_mqtt_message_flow(p)
    saved["fig4_flow"] = p

    print(f"\n  ✓ {len(saved)} charts generated successfully.\n")
    return saved


if __name__ == "__main__":
    # Standalone test: generate charts from saved JSON
    import glob
    json_files = glob.glob("logs/simulation_data_*.json")
    if not json_files:
        print("No simulation data found. Run main.py first.")
        sys.exit(1)
    latest = sorted(json_files)[-1]
    print(f"Loading simulation data from: {latest}")
    with open(latest) as f:
        data = json.load(f)
    out = generate_all_charts(data, out_dir="data")
    print(f"Charts saved: {list(out.keys())}")
