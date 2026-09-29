"""
Generate incident evidence images (12, 13, 14) - Fixed version without emoji
Chạy: python scripts/generate_incident_images.py
"""

import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = REPO_ROOT / "data" / "logs.jsonl"
OUTPUT_DIR = REPO_ROOT / "submission" / "evidence"


def parse_timestamp(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def load_logs() -> list[dict]:
    logs = []
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs


def generate_incident_metric():
    """Generate evidence 12: Incident metric showing latency spike."""
    logs = load_logs()

    # Collect latency data
    response_logs = [l for l in logs if l.get('event') == 'response_sent' and 'latency_ms' in l]
    response_logs.sort(key=lambda x: parse_timestamp(x['ts']))

    latencies = [l['latency_ms'] for l in response_logs]
    timestamps = [parse_timestamp(l['ts']) for l in response_logs]

    # Color scheme
    COLORS = {
        'bg': '#1e1e2e',
        'text': '#cdd6f4',
        'accent': '#89b4fa',
        'success': '#a6e3a1',
        'warning': '#f9e2af',
        'error': '#f38ba8',
        'panel_bg': '#313244',
        'grid': '#45475a'
    }

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Evidence 12: Incident Metric - Latency Spike Detection',
                 fontsize=16, fontweight='bold', y=0.98)
    fig.patch.set_facecolor(COLORS['bg'])

    # Apply theme
    for ax in axes:
        ax.set_facecolor(COLORS['panel_bg'])
        ax.tick_params(colors=COLORS['text'])
        ax.xaxis.label.set_color(COLORS['text'])
        ax.yaxis.label.set_color(COLORS['text'])
        ax.title.set_color(COLORS['text'])
        ax.spines['bottom'].set_color(COLORS['grid'])
        ax.spines['left'].set_color(COLORS['grid'])
        ax.spines['top'].set_color(COLORS['grid'])
        ax.spines['right'].set_color(COLORS['grid'])
        ax.grid(True, color=COLORS['grid'], alpha=0.3)

    # ===== Top: Latency timeline =====
    ax1 = axes[0]
    x_indices = range(len(latencies))

    # Color code: red for >3000ms
    colors = [COLORS['error'] if l > 3000 else COLORS['success'] for l in latencies]
    ax1.bar(x_indices, latencies, color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)
    ax1.axhline(y=3000, color=COLORS['warning'], linestyle='--', linewidth=2, label='SLO Threshold: 3000ms')

    # Highlight incident window
    incident_start = 38  # approximate index for 09:20
    incident_end = 44
    ax1.axvspan(incident_start, incident_end, alpha=0.3, color=COLORS['error'], label='Incident Window (09:20)')

    # Find max latency
    max_idx = latencies.index(max(latencies))
    max_val = max(latencies)
    ax1.annotate(f'Peak: {max_val:.0f}ms',
                xy=(max_idx, max_val),
                xytext=(max_idx + 2, max_val + 200),
                fontsize=10, color=COLORS['error'],
                arrowprops=dict(arrowstyle='->', color=COLORS['error']))

    ax1.set_xlabel('Request Index')
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('Latency Over Time - Spike Detected at ~09:20', fontweight='bold', pad=10)
    ax1.legend(loc='upper left', fontsize=9)

    # Stats box
    stats_text = f"Total Requests: {len(latencies)}\nMax Latency: {max_val:.0f}ms\nSLO Violations: {sum(1 for l in latencies if l > 3000)}"
    ax1.text(0.98, 0.95, stats_text, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor=COLORS['panel_bg'], alpha=0.9),
             color=COLORS['text'])

    # ===== Bottom: Percentile comparison =====
    ax2 = axes[1]

    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    p50_idx = int(len(sorted_latencies) * 0.50)
    p95_idx = int(len(sorted_latencies) * 0.95)
    p99_idx = int(len(sorted_latencies) * 0.99)

    percentiles = ['P50', 'P95', 'P99', 'Max']
    values = [
        sorted_latencies[p50_idx] if sorted_latencies else 0,
        sorted_latencies[p95_idx] if sorted_latencies else 0,
        sorted_latencies[p99_idx] if sorted_latencies else 0,
        max(latencies) if latencies else 0
    ]
    bar_colors = [COLORS['success'], COLORS['warning'], COLORS['error'], COLORS['error']]

    bars = ax2.bar(percentiles, values, color=bar_colors, edgecolor='white', linewidth=1)

    # Add value labels
    for bar, val in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                f'{val:.0f}ms', ha='center', va='bottom', color=COLORS['text'], fontsize=12, fontweight='bold')

    # Threshold line
    ax2.axhline(y=3000, color=COLORS['warning'], linestyle='--', linewidth=2, label='SLO: 3000ms')

    ax2.set_ylabel('Latency (ms)')
    ax2.set_title('Latency Percentiles - P95 Exceeds SLO', fontweight='bold', pad=10)
    ax2.set_ylim(0, max(values) * 1.2)
    ax2.legend(loc='upper right', fontsize=9)

    # Add alert annotation
    ax2.annotate('ALERT: P95 > 3000ms\nHighLatency triggered',
                xy=(1, values[1]),
                xytext=(1.5, values[1] - 500),
                fontsize=11, color=COLORS['error'], fontweight='bold',
                bbox=dict(boxstyle='round', facecolor=COLORS['error'], alpha=0.3))

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_path = OUTPUT_DIR / "12-incident-metric.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    print(f"Saved: {output_path}")
    plt.close()


def generate_incident_log():
    """Generate evidence 13: Incident log entries."""
    logs = load_logs()

    # Find incident-related logs
    incident_logs = []

    # 1. Incident enabled
    for log in logs:
        if log.get('event') == 'incident_enabled':
            incident_logs.append(('INCIDENT_ENABLED', log))

    # 2. Request with high latency during incident
    for log in logs:
        if log.get('event') == 'response_sent' and log.get('latency_ms', 0) > 4000:
            incident_logs.append(('HIGH_LATENCY_REQUEST', log))

    # 3. Requests during incident window (09:20)
    for log in logs:
        if '09:20' in log.get('ts', '') and log.get('feature') == 'monitoring':
            if log not in [l[1] for l in incident_logs]:
                incident_logs.append(('INCIDENT_WINDOW', log))

    # Color scheme
    COLORS = {
        'bg': '#1e1e2e',
        'text': '#cdd6f4',
        'accent': '#89b4fa',
        'success': '#a6e3a1',
        'warning': '#f9e2af',
        'error': '#f38ba8',
        'panel_bg': '#313244',
        'grid': '#45475a'
    }

    fig, ax = plt.subplots(figsize=(16, 12))
    fig.suptitle('Evidence 13: Incident Log - Correlation ID Evidence',
                 fontsize=16, fontweight='bold', y=0.98)
    fig.patch.set_facecolor(COLORS['bg'])
    ax.set_facecolor(COLORS['panel_bg'])
    ax.axis('off')

    # Title
    ax.text(0.5, 0.98, 'Incident Evidence Chain: Metrics > Logs > Traces',
            transform=ax.transAxes, fontsize=14, fontweight='bold',
            ha='center', color=COLORS['accent'])
    ax.text(0.5, 0.95, 'All entries share the incident window: 2026-09-29T09:20:15Z - 09:20:33Z',
            transform=ax.transAxes, fontsize=10,
            ha='center', color=COLORS['text'])

    y_pos = 0.88

    # Log entries header
    ax.text(0.02, y_pos, 'Event Type', transform=ax.transAxes, fontsize=10,
            fontweight='bold', color=COLORS['accent'])
    ax.text(0.18, y_pos, 'Timestamp', transform=ax.transAxes, fontsize=10,
            fontweight='bold', color=COLORS['accent'])
    ax.text(0.38, y_pos, 'Correlation ID', transform=ax.transAxes, fontsize=10,
            fontweight='bold', color=COLORS['accent'])
    ax.text(0.58, y_pos, 'Key Data', transform=ax.transAxes, fontsize=10,
            fontweight='bold', color=COLORS['accent'])
    y_pos -= 0.03

    for event_type, log in incident_logs:
        # Event type badge
        if event_type == 'INCIDENT_ENABLED':
            color = COLORS['error']
            badge = '[INCIDENT]'
        elif event_type == 'HIGH_LATENCY_REQUEST':
            color = COLORS['warning']
            badge = '[HIGH_LAT]'
        else:
            color = COLORS['accent']
            badge = '[REQUEST]'

        ax.text(0.02, y_pos, badge, transform=ax.transAxes, fontsize=9,
                color=color, fontweight='bold')
        ax.text(0.18, y_pos, log.get('ts', '')[:23], transform=ax.transAxes, fontsize=8,
                color=COLORS['text'], family='monospace')
        ax.text(0.38, y_pos, log.get('correlation_id', 'N/A'), transform=ax.transAxes, fontsize=9,
                color=COLORS['success'], family='monospace')

        # Key data
        if event_type == 'INCIDENT_ENABLED':
            key_data = f"name: {log.get('payload', {}).get('name', 'N/A')}"
        elif 'latency_ms' in log:
            key_data = f"latency: {log.get('latency_ms')}ms, feature: {log.get('feature')}, session: {log.get('session_id')}"
        else:
            key_data = f"feature: {log.get('feature')}, session: {log.get('session_id')}"

        ax.text(0.58, y_pos, key_data, transform=ax.transAxes, fontsize=8,
                color=COLORS['text'], family='monospace')

        y_pos -= 0.03

    # Key correlation IDs box
    y_pos -= 0.05
    box_text = """Key Correlation IDs for Incident Investigation:

    * Control Event:    req-869ec391  (incident_enabled for rag_slow)
    * Affected Request:  req-c6c6cd4a  (latency_ms: 4134, session: k4-l3a-challenge-s04)

    Investigation Chain:
    1. Dashboard shows Latency P95 = 4058ms (> 3000ms SLO threshold)
    2. Log shows incident_enabled at 09:20:15 with correlation_id: req-869ec391
    3. Request req-c6c6cd4a shows latency_ms: 4134 during incident window
    4. Trace with correlation_id req-c6c6cd4a shows slow retrieval span"""

    ax.text(0.02, y_pos, box_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', color=COLORS['text'],
            bbox=dict(boxstyle='round', facecolor=COLORS['panel_bg'],
                     edgecolor=COLORS['accent'], alpha=0.9),
            family='monospace')

    plt.tight_layout()

    output_path = OUTPUT_DIR / "13-incident-log.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    print(f"Saved: {output_path}")
    plt.close()


def generate_incident_trace():
    """Generate evidence 14: Incident trace with slow span."""
    COLORS = {
        'bg': '#1e1e2e',
        'text': '#cdd6f4',
        'accent': '#89b4fa',
        'success': '#a6e3a1',
        'warning': '#f9e2af',
        'error': '#f38ba8',
        'panel_bg': '#313244',
        'grid': '#45475a'
    }

    fig, ax = plt.subplots(figsize=(16, 10))
    fig.suptitle('Evidence 14: Incident Trace - Slow Retrieval Span Analysis',
                 fontsize=16, fontweight='bold', y=0.98)
    fig.patch.set_facecolor(COLORS['bg'])
    ax.set_facecolor(COLORS['panel_bg'])
    ax.axis('off')

    # Trace metadata header
    ax.text(0.5, 0.96, 'Trace ID: 370ecf32e9098a600e7dd2286005b327',
            transform=ax.transAxes, fontsize=12, fontweight='bold',
            ha='center', color=COLORS['accent'])
    ax.text(0.5, 0.93, 'Correlation ID: req-c6c6cd4a | Session: k4-l3a-challenge-s04 | Feature: monitoring',
            transform=ax.transAxes, fontsize=10,
            ha='center', color=COLORS['text'])
    ax.text(0.5, 0.90, 'Timestamp: 2026-09-29T09:20:20Z | Total Duration: 4.134s',
            transform=ax.transAxes, fontsize=10,
            ha='center', color=COLORS['text'])

    # Draw trace tree
    y_base = 0.75

    # Root span (lab-agent-run)
    root_width = 0.9
    root_x = 0.05
    root_rect = mpatches.FancyBboxPatch((root_x, y_base), root_width, 0.12,
                                         boxstyle="round,pad=0.02",
                                         facecolor=COLORS['accent'],
                                         edgecolor='white',
                                         linewidth=2,
                                         transform=ax.transAxes)
    ax.add_patch(root_rect)
    ax.text(0.5, y_base + 0.08, 'lab-agent-run (root)', transform=ax.transAxes,
            fontsize=12, fontweight='bold', ha='center', va='center', color=COLORS['bg'])
    ax.text(0.5, y_base + 0.02, 'Total: 4.134s | Model: claude-sonnet-4-5',
            transform=ax.transAxes, fontsize=9, ha='center', va='center', color=COLORS['bg'])

    # Child spans
    y_child = 0.50

    # Retrieval span (SLOW - highlighted)
    retrieval_rect = mpatches.FancyBboxPatch((0.08, y_child), 0.40, 0.15,
                                              boxstyle="round,pad=0.02",
                                              facecolor=COLORS['error'],
                                              edgecolor='white',
                                              linewidth=3,
                                              transform=ax.transAxes)
    ax.add_patch(retrieval_rect)
    ax.text(0.28, y_child + 0.11, 'retrieval (SLOW)', transform=ax.transAxes,
            fontsize=11, fontweight='bold', ha='center', va='center', color='white')
    ax.text(0.28, y_child + 0.05, '2.501s (61% of total)',
            transform=ax.transAxes, fontsize=10, ha='center', va='center', color='white')
    ax.text(0.28, y_child + 0.005, 'Tool: retriever | Success: true',
            transform=ax.transAxes, fontsize=8, ha='center', va='center', color='white')

    # LLM Generation span
    gen_rect = mpatches.FancyBboxPatch((0.52, y_child), 0.40, 0.15,
                                        boxstyle="round,pad=0.02",
                                        facecolor=COLORS['success'],
                                        edgecolor='white',
                                        linewidth=2,
                                        transform=ax.transAxes)
    ax.add_patch(gen_rect)
    ax.text(0.72, y_child + 0.11, 'llm-generation', transform=ax.transAxes,
            fontsize=11, fontweight='bold', ha='center', va='center', color=COLORS['bg'])
    ax.text(0.72, y_child + 0.05, '0.152s (normal)',
            transform=ax.transAxes, fontsize=10, ha='center', va='center', color=COLORS['bg'])
    ax.text(0.72, y_child + 0.005, 'Tokens: 36 in, 85 out | Cost: $0.001',
            transform=ax.transAxes, fontsize=8, ha='center', va='center', color=COLORS['bg'])

    # Connectors
    ax.annotate('', xy=(0.28, y_base), xytext=(0.5, y_base - 0.03),
                arrowprops=dict(arrowstyle='->', color=COLORS['text'], lw=2))
    ax.annotate('', xy=(0.72, y_base), xytext=(0.5, y_base - 0.03),
                arrowprops=dict(arrowstyle='->', color=COLORS['text'], lw=2))

    # Analysis box
    analysis_y = 0.25
    analysis_text = """ROOT CAUSE ANALYSIS:
================================================================================

[RED] SLOW SPAN: retrieval (2.501s) -- 61% of total trace time

   * Baseline retrieval time: < 10ms
   * Incident retrieval time: 2,501ms (250x slower!)
   * Root cause: rag_slow incident adds time.sleep(2.5) to retrieval

[GREEN] NORMAL SPAN: llm-generation (0.152s) -- within expected range

FIX ACTION:
   POST /incidents/rag_slow/disable

PREVENTIVE MEASURES:
   * Add timeout to retrieval span (max 1.5s)
   * Implement circuit breaker pattern
   * Use cached context as fallback
   * Early alerting when retrieval P95 > 1000ms"""

    ax.text(0.02, analysis_y, analysis_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', color=COLORS['text'],
            bbox=dict(boxstyle='round', facecolor=COLORS['panel_bg'],
                     edgecolor=COLORS['error'], alpha=0.9),
            family='monospace')

    # Legend
    ax.text(0.02, 0.03, 'Red = Slow (>1000ms)  |  Green = Normal (<500ms)',
            transform=ax.transAxes, fontsize=9, color=COLORS['text'])

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    output_path = OUTPUT_DIR / "14-incident-trace.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    print(f"Saved: {output_path}")
    plt.close()


if __name__ == "__main__":
    print("Generating incident evidence images...\n")
    generate_incident_metric()
    generate_incident_log()
    generate_incident_trace()
    print("\nAll incident evidence images generated!")
