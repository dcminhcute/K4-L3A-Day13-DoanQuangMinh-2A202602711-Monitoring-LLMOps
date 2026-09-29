"""
Generate dashboard image từ data/logs.jsonl
Chạy: python scripts/generate_dashboard_image.py
Output: submission/evidence/11-dashboard-overview.png
"""

import json
import math
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = REPO_ROOT / "data" / "logs.jsonl"
OUTPUT_FILE = REPO_ROOT / "submission" / "evidence" / "11-dashboard-overview.png"


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp."""
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def load_logs() -> list[dict]:
    """Load logs from JSONL file."""
    logs = []
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs


def percentile(data: list, p: float) -> float:
    """Calculate percentile."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    floor_idx = int(math.floor(idx))
    ceil_idx = int(math.ceil(idx))
    if floor_idx == ceil_idx:
        return sorted_data[floor_idx]
    d0 = sorted_data[floor_idx] * (ceil_idx - idx)
    d1 = sorted_data[ceil_idx] * (idx - floor_idx)
    return d0 + d1


def calculate_latency_stats(logs: list[dict]) -> dict:
    """Calculate latency percentiles from response_sent events."""
    latencies = []
    ttfts = []
    for log in logs:
        if log.get('event') == 'response_sent' and 'latency_ms' in log:
            latencies.append(log['latency_ms'])
        if log.get('event') == 'response_sent' and 'ttft_ms' in log:
            ttfts.append(log['ttft_ms'])

    return {
        'p50': percentile(latencies, 50),
        'p95': percentile(latencies, 95),
        'p99': percentile(latencies, 99),
        'ttft_p95': percentile(ttfts, 95) if ttfts else 0,
        'all': latencies,
        'timestamps': [parse_timestamp(l['ts']) for l in logs if l.get('event') == 'response_sent' and 'latency_ms' in l]
    }


def calculate_traffic(logs: list[dict]) -> dict:
    """Calculate request traffic."""
    requests = [l for l in logs if l.get('event') == 'request_received']
    timestamps = [parse_timestamp(l['ts']) for l in requests]

    if not timestamps:
        return {'count': 0, 'rate_per_min': 0, 'timestamps': []}

    time_range_min = (max(timestamps) - min(timestamps)).total_seconds() / 60
    rate = len(timestamps) / max(time_range_min, 1)

    return {
        'count': len(requests),
        'rate_per_min': rate,
        'timestamps': timestamps
    }


def calculate_errors(logs: list[dict]) -> dict:
    """Calculate error rate and retrieval success."""
    requests = [l for l in logs if l.get('event') == 'request_received']
    failed = [l for l in logs if l.get('event') == 'request_failed']

    total_requests = len(requests)
    total_failed = len(failed)
    error_rate = (total_failed / total_requests * 100) if total_requests > 0 else 0

    # Retrieval success
    responses = [l for l in logs if l.get('event') == 'response_sent']
    successful = [l for l in responses if l.get('tool_success') == True]
    retrieval_success = (len(successful) / len(responses) * 100) if responses else 0

    return {
        'error_rate': error_rate,
        'total_requests': total_requests,
        'total_failed': total_failed,
        'retrieval_success': retrieval_success
    }


def calculate_cost(logs: list[dict]) -> dict:
    """Calculate cost metrics."""
    responses = [l for l in logs if l.get('event') == 'response_sent']
    costs = [l.get('cost_usd', 0) for l in responses]

    total = sum(costs)
    by_minute = defaultdict(float)
    timestamps = []

    for log in responses:
        ts = parse_timestamp(log['ts'])
        minute_key = ts.strftime('%H:%M')
        by_minute[minute_key] += log.get('cost_usd', 0)
        timestamps.append((ts, log.get('cost_usd', 0)))

    return {
        'total': total,
        'by_minute': dict(by_minute),
        'timestamps': timestamps
    }


def calculate_tokens(logs: list[dict]) -> dict:
    """Calculate token metrics."""
    responses = [l for l in logs if l.get('event') == 'response_sent']
    tokens_in = sum(l.get('tokens_in', 0) for l in responses)
    tokens_out = sum(l.get('tokens_out', 0) for l in responses)

    return {
        'input': tokens_in,
        'output': tokens_out,
        'total': tokens_in + tokens_out
    }


def calculate_quality(logs: list[dict]) -> dict:
    """Calculate quality score."""
    responses = [l for l in logs if l.get('event') == 'response_sent' and 'quality_score' in l]
    scores = [l.get('quality_score', 0) for l in responses]

    return {
        'mean': sum(scores) / len(scores) if scores else 0,
        'scores': scores
    }


def create_dashboard():
    """Create the 6-panel dashboard."""
    print("Loading logs...")
    logs = load_logs()

    print("Calculating metrics...")
    latency = calculate_latency_stats(logs)
    traffic = calculate_traffic(logs)
    errors = calculate_errors(logs)
    cost = calculate_cost(logs)
    tokens = calculate_tokens(logs)
    quality = calculate_quality(logs)

    # Create figure with 6 panels
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('K4-L3A Day 13 Monitoring & LLMOps - Dashboard',
                 fontsize=16, fontweight='bold', y=0.98)

    # Time range display
    if latency['timestamps']:
        time_range = f"Time Range: {min(latency['timestamps']).strftime('%H:%M')} - {max(latency['timestamps']).strftime('%H:%M')}"
        fig.text(0.5, 0.95, time_range, ha='center', fontsize=10, color='gray')

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

    # Apply theme
    fig.patch.set_facecolor(COLORS['bg'])
    for ax in fig.axes:
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

    # ===== Panel 1: Latency =====
    ax1 = fig.add_subplot(3, 2, 1)
    if latency['all']:
        ax1.hist(latency['all'], bins=30, color=COLORS['accent'], alpha=0.7, edgecolor='white')
        ax1.axvline(latency['p95'], color=COLORS['error'], linestyle='--', linewidth=2, label=f'P95={latency["p95"]:.0f}ms')
        ax1.axvline(3000, color=COLORS['warning'], linestyle='-', linewidth=2, label='SLO: 3000ms')
    ax1.set_xlabel('Latency (ms)')
    ax1.set_ylabel('Count')
    ax1.set_title('Latency Percentiles & TTFT', fontweight='bold', pad=10)

    # Stats box
    stats_text = f"P50: {latency['p50']:.0f}ms\nP95: {latency['p95']:.0f}ms\nP99: {latency['p99']:.0f}ms\nTTFT P95: {latency['ttft_p95']:.0f}ms"
    ax1.text(0.95, 0.95, stats_text, transform=ax1.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor=COLORS['panel_bg'], alpha=0.8),
             color=COLORS['text'])
    ax1.legend(loc='upper left', fontsize=8)

    # ===== Panel 2: Traffic =====
    ax2 = fig.add_subplot(3, 2, 2)
    if traffic['timestamps']:
        timestamps = sorted(traffic['timestamps'])
        if len(timestamps) > 1:
            time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
            time_diffs = [d for d in time_diffs if d > 0]
            if time_diffs:
                rates = [60/d for d in time_diffs]
                ax2.plot(range(len(rates)), rates, color=COLORS['accent'], marker='o', markersize=3)
                ax2.axhline(y=1, color=COLORS['success'], linestyle='--', label='Min Rate: 1 req/min')
    ax2.set_xlabel('Request Index')
    ax2.set_ylabel('Rate (req/min)')
    ax2.set_title('Request Traffic', fontweight='bold', pad=10)

    stats_text2 = f"Total: {traffic['count']} requests\nRate: {traffic['rate_per_min']:.1f} req/min"
    ax2.text(0.95, 0.95, stats_text2, transform=ax2.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor=COLORS['panel_bg'], alpha=0.8),
             color=COLORS['text'])
    ax2.legend(loc='upper left', fontsize=8)

    # ===== Panel 3: Errors =====
    ax3 = fig.add_subplot(3, 2, 3)
    categories = ['Success', 'Errors']
    values = [100 - errors['error_rate'], errors['error_rate']]
    colors = [COLORS['success'], COLORS['error']]
    bars = ax3.bar(categories, values, color=colors, edgecolor='white', linewidth=1)
    ax3.axhline(y=98, color=COLORS['warning'], linestyle='--', linewidth=2, label='Target: 98%')
    ax3.set_ylabel('Percentage (%)')
    ax3.set_title('Error Rate & Retrieval Success', fontweight='bold', pad=10)
    ax3.set_ylim(0, 105)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.1f}%', ha='center', va='bottom', color=COLORS['text'], fontsize=10)

    stats_text3 = f"Error Rate: {errors['error_rate']:.1f}%\nRetrieval Success: {errors['retrieval_success']:.1f}%"
    ax3.text(0.95, 0.95, stats_text3, transform=ax3.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor=COLORS['panel_bg'], alpha=0.8),
             color=COLORS['text'])
    ax3.legend(loc='lower right', fontsize=8)

    # ===== Panel 4: Cost =====
    ax4 = fig.add_subplot(3, 2, 4)
    if cost['by_minute']:
        minutes = sorted(cost['by_minute'].keys())
        costs_values = [cost['by_minute'][m] for m in minutes]
        ax4.bar(range(len(minutes)), costs_values, color=COLORS['accent'], alpha=0.7, edgecolor='white')
        ax4.axhline(y=2.5, color=COLORS['error'], linestyle='--', linewidth=2, label='Budget: $2.50')
    ax4.set_xlabel('Time (minute)')
    ax4.set_ylabel('Cost (USD)')
    ax4.set_title('Cost Over Time', fontweight='bold', pad=10)

    stats_text4 = f"Total: ${cost['total']:.4f}\nBudget: $2.50"
    ax4.text(0.95, 0.95, stats_text4, transform=ax4.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor=COLORS['panel_bg'], alpha=0.8),
             color=COLORS['text'])
    ax4.legend(loc='upper left', fontsize=8)

    # ===== Panel 5: Tokens =====
    ax5 = fig.add_subplot(3, 2, 5)
    categories = ['Input', 'Output', 'Total']
    values = [tokens['input'], tokens['output'], tokens['total']]
    colors = [COLORS['accent'], COLORS['warning'], COLORS['success']]
    bars = ax5.bar(categories, values, color=colors, edgecolor='white', linewidth=1)
    ax5.axhline(y=50000, color=COLORS['error'], linestyle='--', linewidth=2, label='Limit: 50,000')
    ax5.set_ylabel('Tokens')
    ax5.set_title('Input & Output Tokens', fontweight='bold', pad=10)

    for bar, val in zip(bars, values):
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
                f'{val:,}', ha='center', va='bottom', color=COLORS['text'], fontsize=9)

    ax5.legend(loc='upper right', fontsize=8)

    # ===== Panel 6: Quality =====
    ax6 = fig.add_subplot(3, 2, 6)
    if quality['scores']:
        ax6.hist(quality['scores'], bins=20, color=COLORS['success'], alpha=0.7, edgecolor='white')
        ax6.axvline(quality['mean'], color=COLORS['accent'], linestyle='--', linewidth=2,
                   label=f'Mean: {quality["mean"]:.2f}')
        ax6.axvline(0.75, color=COLORS['warning'], linestyle='-', linewidth=2, label='Target: 0.75')
    ax6.set_xlabel('Quality Score')
    ax6.set_ylabel('Count')
    ax6.set_title('Quality Proxy Score', fontweight='bold', pad=10)
    ax6.set_xlim(0, 1)
    ax6.legend(loc='upper left', fontsize=8)

    # Layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    print(f"Saving to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none')
    print(f"✅ Dashboard saved to {OUTPUT_FILE}")

    # Also print summary
    print("\n" + "="*50)
    print("DASHBOARD SUMMARY")
    print("="*50)
    print(f"Latency P95: {latency['p95']:.0f}ms (SLO: 3000ms)")
    print(f"TTFT P95: {latency['ttft_p95']:.0f}ms")
    print(f"Traffic: {traffic['count']} requests")
    print(f"Error Rate: {errors['error_rate']:.1f}%")
    print(f"Retrieval Success: {errors['retrieval_success']:.1f}%")
    print(f"Total Cost: ${cost['total']:.4f}")
    print(f"Total Tokens: {tokens['total']:,}")
    print(f"Quality Mean: {quality['mean']:.2f}")
    print("="*50)


if __name__ == "__main__":
    create_dashboard()
