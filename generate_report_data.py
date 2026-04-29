"""
Generate baseline simulation data and figures for the ORF387 final report.

Runs each pass strategy with the rational baseline (no behaviors) at 3 seeds,
saves per-run summary stats to results.csv, and produces 3 figures per strategy:
  - figures/{strategy}_histogram.png    — utility distribution
  - figures/{strategy}_queues.png       — total queue length over time
  - figures/{strategy}_population.png   — in-park population over time
plus 3 cross-strategy comparison charts:
  - figures/comparison_happiness.png    — total park happiness by strategy
  - figures/comparison_avg_metrics.png  — avg happiness/wait/rides by strategy
  - figures/comparison_distributions.png — overlaid utility distributions
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from park_model import build_epic_universe, PARK_CLOSE
from simulation import Simulation


FIG_DIR = Path(__file__).parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

PASS_STRATEGIES = ["none", "preselect", "preselect_timed", "dynamic", "express"]
PASS_LABELS = {
    "none": "Baseline (No Passes)",
    "preselect": "Preselect (Anytime)",
    "preselect_timed": "Preselect (Timed Slots)",
    "dynamic": "Dynamic (On-Demand)",
    "express": "Express Pass (30%)",
}
SEEDS = [42, 1, 7]  # 3-seed Monte Carlo
EXPRESS_PCT = 0.30


def run_strategy(strategy: str, seed: int):
    """Run a single full-day sim. Returns (summary, history, agent_records)."""
    park = build_epic_universe()
    sim = Simulation(
        park, dt=1.0, seed=seed,
        pass_strategy=strategy,
        behaviors=[],
        express_pct=EXPRESS_PCT,
    )
    sim.generate_agents()
    sim.run()
    return sim.summary(), sim.history, sim.agent_records()


def plot_histogram(strategy: str, agents: list[dict]) -> None:
    """Histogram of total happiness across agents (with pass-holder split for express)."""
    if not agents:
        return
    happs = np.array([a["happiness"] for a in agents])
    pass_holders = np.array([a["pass_holder"] for a in agents])
    cutoff = np.percentile(happs, 99)  # clip top-1% outliers from the visual range
    mask = happs <= cutoff

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(0, cutoff, 31)
    if strategy == "express":
        ax.hist(happs[mask & pass_holders], bins=bins, alpha=0.85,
                color="#ffe66d", edgecolor="black", label="Pass Holders", stacked=False)
        ax.hist(happs[mask & ~pass_holders], bins=bins, alpha=0.6,
                color="#4ecdc4", edgecolor="black", label="Non-Holders", stacked=False)
        ax.legend(loc="upper right")
    else:
        ax.hist(happs[mask], bins=bins, color="#4ecdc4", edgecolor="black")
    ax.set_xlabel("Total Happiness")
    ax.set_ylabel("Number of Park-goers")
    ax.set_title(f"{PASS_LABELS[strategy]} — Utility Distribution")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{strategy}_histogram.png", dpi=140)
    plt.close(fig)


def plot_queues(strategy: str, history: list[dict]) -> None:
    """Total queue length across all rides over time."""
    times = [s["time"] for s in history]
    totals = [sum(s["queue_lengths"].values()) for s in history]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(times, totals, color="#ef4444", linewidth=2)
    ax.fill_between(times, totals, alpha=0.2, color="#ef4444")
    # tick labels in clock format
    hour_ticks = list(range(0, PARK_CLOSE + 1, 60))
    ax.set_xticks(hour_ticks)
    ax.set_xticklabels([f"{9 + h // 60}:00" for h in hour_ticks], rotation=0)
    ax.set_xlabel("Time of Day")
    ax.set_ylabel("Total Agents Queued (all rides)")
    ax.set_title(f"{PASS_LABELS[strategy]} — Park-Wide Queue Length")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{strategy}_queues.png", dpi=140)
    plt.close(fig)


def plot_population(strategy: str, history: list[dict]) -> None:
    """In-park population over time."""
    times = [s["time"] for s in history]
    pop = []
    for s in history:
        sc = s["state_counts"]
        pop.append(sum(v for k, v in sc.items() if k not in ("inactive", "departed")))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(times, pop, color="#3b82f6", linewidth=2)
    ax.fill_between(times, pop, alpha=0.2, color="#3b82f6")
    hour_ticks = list(range(0, PARK_CLOSE + 1, 60))
    ax.set_xticks(hour_ticks)
    ax.set_xticklabels([f"{9 + h // 60}:00" for h in hour_ticks])
    ax.set_xlabel("Time of Day")
    ax.set_ylabel("Agents in Park")
    ax.set_title(f"{PASS_LABELS[strategy]} — Park Population")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{strategy}_population.png", dpi=140)
    plt.close(fig)


def plot_comparison_happiness(rows: list[dict]) -> None:
    """Bar chart of total park happiness by strategy with error bars across seeds."""
    by_strat = {s: [] for s in PASS_STRATEGIES}
    for r in rows:
        by_strat[r["strategy"]].append(r["total_park_happiness"])

    means = [np.mean(by_strat[s]) for s in PASS_STRATEGIES]
    stds = [np.std(by_strat[s]) for s in PASS_STRATEGIES]
    labels = [PASS_LABELS[s] for s in PASS_STRATEGIES]

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#888888", "#4ecdc4", "#a855f7", "#ef4444", "#ffe66d"]
    bars = ax.bar(labels, means, yerr=stds, color=colors, edgecolor="black",
                  capsize=5, error_kw={"linewidth": 1.5})
    baseline_mean = means[0]
    for bar, mean in zip(bars, means):
        pct = 100 * (mean - baseline_mean) / baseline_mean
        label = f"{mean / 1000:.0f}K" + ("" if pct == 0 else f"\n({pct:+.1f}%)")
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(stds) * 0.5,
                label, ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Total Park Happiness")
    ax.set_title("Total Park Happiness by Strategy (mean ± std over 3 seeds)")
    ax.tick_params(axis="x", labelrotation=15)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "comparison_happiness.png", dpi=140)
    plt.close(fig)


def plot_comparison_avg_metrics(rows: list[dict]) -> None:
    """Side-by-side bars: avg_happiness, avg_wait, avg_rides per strategy."""
    by_strat = {s: {"avg_happiness": [], "avg_wait": [], "avg_rides": []} for s in PASS_STRATEGIES}
    for r in rows:
        for k in ["avg_happiness", "avg_wait", "avg_rides"]:
            by_strat[r["strategy"]][k].append(r[k])

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    metrics = [("avg_happiness", "Avg Happiness per Agent"),
               ("avg_wait", "Avg Total Wait (min)"),
               ("avg_rides", "Avg Rides Completed")]
    colors = ["#888888", "#4ecdc4", "#a855f7", "#ef4444", "#ffe66d"]
    for ax, (key, title) in zip(axes, metrics):
        means = [np.mean(by_strat[s][key]) for s in PASS_STRATEGIES]
        stds = [np.std(by_strat[s][key]) for s in PASS_STRATEGIES]
        ax.bar([PASS_LABELS[s] for s in PASS_STRATEGIES], means, yerr=stds,
               color=colors, edgecolor="black", capsize=4)
        ax.set_title(title)
        ax.tick_params(axis="x", labelrotation=20, labelsize=8)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Per-Strategy Aggregates (mean ± std over 3 seeds)", y=1.02, fontsize=13)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "comparison_avg_metrics.png", dpi=140)
    plt.close(fig)


def plot_comparison_distributions(per_strategy_agents: dict) -> None:
    """Overlay each strategy's utility distribution as a stepfilled histogram."""
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = {"none": "#888888", "preselect": "#4ecdc4",
              "preselect_timed": "#a855f7", "dynamic": "#ef4444", "express": "#ffe66d"}
    cutoff = max(np.percentile([a["happiness"] for a in per_strategy_agents["none"]], 99) * 1.2, 50)
    bins = np.linspace(0, cutoff, 41)
    for strategy in PASS_STRATEGIES:
        agents = per_strategy_agents[strategy]
        happs = np.array([a["happiness"] for a in agents])
        ax.hist(happs[happs <= cutoff], bins=bins, alpha=0.45,
                color=colors[strategy], label=PASS_LABELS[strategy],
                histtype="stepfilled", edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Total Happiness")
    ax.set_ylabel("Number of Park-goers")
    ax.set_title("Utility Distributions Across Strategies")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "comparison_distributions.png", dpi=140)
    plt.close(fig)


def main():
    rows = []
    per_strategy_agents = {}     # seed-42 agent records per strategy (for distribution overlay)
    per_strategy_history = {}    # seed-42 history per strategy (for time-series plots)

    print(f"Running {len(PASS_STRATEGIES) * len(SEEDS)} simulations...\n")
    for strategy in PASS_STRATEGIES:
        for seed in SEEDS:
            print(f"  {strategy:18s} seed={seed:>4} ...", end=" ", flush=True)
            summary, history, agents = run_strategy(strategy, seed)
            rows.append({
                "strategy": strategy,
                "seed": seed,
                **{k: float(summary[k]) for k in
                   ["total_park_happiness", "avg_happiness", "median_happiness",
                    "std_happiness", "avg_wait", "avg_travel", "avg_rides", "peak_queue"]},
                "total_passes_used": int(summary["total_passes_used"]),
                "num_agents": int(summary["num_agents"]),
            })
            print(f"avgH={summary['avg_happiness']:.2f}  avgWait={summary['avg_wait']:.1f}")
            if seed == SEEDS[0]:
                per_strategy_agents[strategy] = agents
                per_strategy_history[strategy] = history

    # Save raw per-run results
    csv_path = Path(__file__).parent / "results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved per-run results to {csv_path.name}")

    # Per-strategy figures (use the seed-42 run for each)
    print("\nGenerating per-strategy figures...")
    for strategy in PASS_STRATEGIES:
        plot_histogram(strategy, per_strategy_agents[strategy])
        plot_queues(strategy, per_strategy_history[strategy])
        plot_population(strategy, per_strategy_history[strategy])
        print(f"  {strategy}: histogram, queues, population")

    # Cross-strategy comparison figures
    print("\nGenerating comparison figures...")
    plot_comparison_happiness(rows)
    plot_comparison_avg_metrics(rows)
    plot_comparison_distributions(per_strategy_agents)
    print("  comparison_happiness.png")
    print("  comparison_avg_metrics.png")
    print("  comparison_distributions.png")

    # Summary table to stdout
    print("\n" + "=" * 90)
    print(f"{'Strategy':<20} {'avgH (mean)':>14} {'avgH (std)':>14} {'avgWait':>10} {'avgRides':>10}")
    print("=" * 90)
    for strategy in PASS_STRATEGIES:
        sub = [r for r in rows if r["strategy"] == strategy]
        h = [r["avg_happiness"] for r in sub]
        w = [r["avg_wait"] for r in sub]
        r_count = [r["avg_rides"] for r in sub]
        print(f"{PASS_LABELS[strategy]:<20} {np.mean(h):>14.2f} {np.std(h):>14.3f} "
              f"{np.mean(w):>10.1f} {np.mean(r_count):>10.2f}")
    print("=" * 90)
    print(f"\nAll output in {FIG_DIR.relative_to(Path.cwd())}/ and results.csv")


if __name__ == "__main__":
    main()
