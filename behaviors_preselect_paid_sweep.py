"""
Paid Preselect adoption sweep WITH ALL AGENT BEHAVIORS ENABLED.

Same as preselect_paid_sweep.py but agents have all 5 imperfect behaviors active
(fatigue, info_restricted, proximity_bias, decision_paralysis, eating_resting),
modeling realistic-rationality visitors instead of perfectly-rational ones.

Output: figures/behaviors_preselect_paid_sweep.png and behaviors_preselect_paid_sweep_results.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec

from park_model import build_epic_universe
from simulation import Simulation


FIG_DIR = Path(__file__).parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

ADOPTION_LEVELS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
SEED = 42
NUM_BINS = 30
ALL_BEHAVIORS = ["fatigue", "info_restricted", "proximity_bias",
                 "decision_paralysis", "eating_resting"]


def run_level(pct_int: int):
    """Run one full-day sim at a given adoption level (integer 0-100)
    with all 5 agent behaviors enabled."""
    park = build_epic_universe()
    sim = Simulation(
        park, dt=1.0, seed=SEED,
        pass_strategy="preselect_paid",
        behaviors=ALL_BEHAVIORS,
        preselect_pct=pct_int / 100.0,
    )
    sim.generate_agents()
    sim.run()
    return sim.summary(), sim.agent_records()


def main():
    print(f"Running {len(ADOPTION_LEVELS)} Paid Preselect sweep simulations "
          f"with all behaviors enabled (seed={SEED})...\n")

    per_level_agents: dict[int, list[dict]] = {}
    per_level_summary: dict[int, dict] = {}

    for pct in ADOPTION_LEVELS:
        print(f"  preselect_pct={pct:>3}% ...", end=" ", flush=True)
        summary, agents = run_level(pct)
        per_level_agents[pct] = agents
        per_level_summary[pct] = summary
        print(f"avgH={summary['avg_happiness']:.2f}  totalH={summary['total_park_happiness']/1000:.0f}K")

    # ---- Build per-level subpopulation stats ----
    rows = []
    for pct in ADOPTION_LEVELS:
        agents = per_level_agents[pct]
        h_all = np.array([a["happiness"] for a in agents])
        is_holder = np.array([a["pass_holder"] for a in agents])

        n_holders = int(is_holder.sum())
        n_non = len(agents) - n_holders

        holder_mean = float(h_all[is_holder].mean()) if n_holders > 0 else float("nan")
        non_mean = float(h_all[~is_holder].mean()) if n_non > 0 else float("nan")
        system_mean = float(h_all.mean()) if len(agents) > 0 else float("nan")

        gap_ratio = holder_mean / non_mean if (n_holders > 0 and n_non > 0 and non_mean > 0) else float("nan")

        rows.append({
            "adoption_pct": pct,
            "n_holders": n_holders,
            "n_non_holders": n_non,
            "holder_mean_happiness": holder_mean,
            "non_holder_mean_happiness": non_mean,
            "system_mean_happiness": system_mean,
            "total_park_happiness": float(per_level_summary[pct]["total_park_happiness"]),
            "gap_ratio": gap_ratio,
            "avg_wait": float(per_level_summary[pct]["avg_wait"]),
            "avg_rides": float(per_level_summary[pct]["avg_rides"]),
        })

    csv_path = Path(__file__).parent / "behaviors_preselect_paid_sweep_results.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved per-level results to {csv_path.name}")

    # ---- Build heatmap matrices ----
    all_happs = np.concatenate([
        np.array([a["happiness"] for a in per_level_agents[pct]])
        for pct in ADOPTION_LEVELS
    ])
    cutoff = np.percentile(all_happs, 99)
    bin_edges = np.linspace(0, cutoff, NUM_BINS + 1)

    holder_matrix = np.zeros((len(ADOPTION_LEVELS), NUM_BINS))
    non_matrix = np.zeros((len(ADOPTION_LEVELS), NUM_BINS))

    for i, pct in enumerate(ADOPTION_LEVELS):
        agents = per_level_agents[pct]
        h = np.array([a["happiness"] for a in agents])
        ph = np.array([a["pass_holder"] for a in agents])
        keep = h <= cutoff
        if ph.any():
            counts, _ = np.histogram(h[keep & ph], bins=bin_edges)
            holder_matrix[i] = counts
        if (~ph).any():
            counts, _ = np.histogram(h[keep & ~ph], bins=bin_edges)
            non_matrix[i] = counts

    # ---- Composite figure ----
    fig = plt.figure(figsize=(14, 9))
    gs = GridSpec(2, 2, height_ratios=[1.2, 1.0], hspace=0.35, wspace=0.20)

    ax_h = fig.add_subplot(gs[0, 0])
    ax_n = fig.add_subplot(gs[0, 1])
    ax_l = fig.add_subplot(gs[1, :])

    vmax = max(holder_matrix.max(), non_matrix.max())

    im_h = ax_h.imshow(holder_matrix, aspect="auto", origin="lower",
                       cmap="magma", vmin=0, vmax=vmax,
                       extent=[bin_edges[0], bin_edges[-1], -0.5, len(ADOPTION_LEVELS) - 0.5])
    ax_h.set_yticks(range(len(ADOPTION_LEVELS)))
    ax_h.set_yticklabels([f"{p}%" for p in ADOPTION_LEVELS])
    ax_h.set_xlabel("Total Happiness")
    ax_h.set_ylabel("Paid Preselect Adoption %")
    ax_h.set_title("Pass Holders — Utility Distribution")
    fig.colorbar(im_h, ax=ax_h, label="# Park-goers", shrink=0.85)

    im_n = ax_n.imshow(non_matrix, aspect="auto", origin="lower",
                       cmap="magma", vmin=0, vmax=vmax,
                       extent=[bin_edges[0], bin_edges[-1], -0.5, len(ADOPTION_LEVELS) - 0.5])
    ax_n.set_yticks(range(len(ADOPTION_LEVELS)))
    ax_n.set_yticklabels([f"{p}%" for p in ADOPTION_LEVELS])
    ax_n.set_xlabel("Total Happiness")
    ax_n.set_ylabel("Paid Preselect Adoption %")
    ax_n.set_title("Non-Holders — Utility Distribution")
    fig.colorbar(im_n, ax=ax_n, label="# Park-goers", shrink=0.85)

    pcts = [r["adoption_pct"] for r in rows]
    holder_means = [r["holder_mean_happiness"] for r in rows]
    non_means = [r["non_holder_mean_happiness"] for r in rows]
    system_means = [r["system_mean_happiness"] for r in rows]
    gap_ratios = [r["gap_ratio"] for r in rows]

    ax_l.plot(pcts, holder_means, "o-", color="#ffe66d", label="Pass Holders (mean)",
              markersize=8, linewidth=2, markeredgecolor="black")
    ax_l.plot(pcts, non_means, "s-", color="#4ecdc4", label="Non-Holders (mean)",
              markersize=7, linewidth=2, markeredgecolor="black")
    ax_l.plot(pcts, system_means, "D-", color="#a855f7", label="System Mean",
              markersize=7, linewidth=2, markeredgecolor="black")

    valid = [(p, m) for p, m in zip(pcts, system_means) if not np.isnan(m)]
    if valid:
        peak_pct, peak_val = max(valid, key=lambda x: x[1])
        ax_l.annotate(f"System mean peaks at {peak_pct}%\n(avgH = {peak_val:.1f})",
                      xy=(peak_pct, peak_val),
                      xytext=(0.30, 0.55), textcoords="axes fraction",
                      arrowprops=dict(arrowstyle="->", color="#a855f7", lw=1.2),
                      fontsize=10, color="#a855f7")

    ax_l.set_xlabel("Paid Preselect Adoption %")
    ax_l.set_ylabel("Mean Total Happiness")
    ax_l.set_xticks(pcts)
    ax_l.grid(alpha=0.3)

    ax_r = ax_l.twinx()
    ax_r.plot(pcts, gap_ratios, "^--", color="#ef4444",
              markersize=7, linewidth=1.5, alpha=0.85, markeredgecolor="black",
              label="Gap (Holder/Non-Holder)")
    ax_r.set_ylabel("Holder / Non-Holder Mean Ratio", color="#ef4444")
    ax_r.tick_params(axis="y", labelcolor="#ef4444")
    ax_r.axhline(y=1, color="#ef4444", linestyle=":", alpha=0.4)

    # Combined legend on the bottom-left, drawing handles from both axes
    lines_l, labels_l = ax_l.get_legend_handles_labels()
    lines_r, labels_r = ax_r.get_legend_handles_labels()
    ax_l.legend(lines_l + lines_r, labels_l + labels_r, loc="lower left")

    fig.suptitle("Paid Preselect Sweep with All Agent Behaviors Enabled",
                 fontsize=14, y=0.98)

    out = FIG_DIR / "behaviors_preselect_paid_sweep.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure to {out.relative_to(Path.cwd())}")

    print("\n" + "=" * 100)
    print(f"{'%':>4} {'holder mean':>12} {'non mean':>10} {'system mean':>12} {'gap':>6} {'total H':>10}")
    print("=" * 100)
    for r in rows:
        gap_str = f"{r['gap_ratio']:.2f}×" if not np.isnan(r["gap_ratio"]) else "—"
        h_str = f"{r['holder_mean_happiness']:.2f}" if not np.isnan(r["holder_mean_happiness"]) else "—"
        n_str = f"{r['non_holder_mean_happiness']:.2f}" if not np.isnan(r["non_holder_mean_happiness"]) else "—"
        print(f"{r['adoption_pct']:>3}% {h_str:>12} {n_str:>10} "
              f"{r['system_mean_happiness']:>12.2f} {gap_str:>6} {r['total_park_happiness']/1000:>9.0f}K")
    print("=" * 100)


if __name__ == "__main__":
    main()
