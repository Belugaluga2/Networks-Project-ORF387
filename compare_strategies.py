"""
Compare virtual queue strategies against baseline.
Runs 4 simulations with the same seed and compares total park happiness.
"""

from park_model import build_epic_universe, PARK_CLOSE
from simulation import Simulation


def run_strategy(strategy: str, seed: int = 42) -> dict:
    """Run a full simulation with the given pass strategy."""
    park = build_epic_universe()
    sim = Simulation(park, dt=1.0, seed=seed, pass_strategy=strategy)
    sim.generate_agents()
    return sim.run()


def main():
    strategies = ["none", "preselect", "preselect_timed", "dynamic"]
    labels = {"none": "Baseline", "preselect": "Preselect", "preselect_timed": "Timed", "dynamic": "Dynamic"}
    results = {}

    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"  Strategy: {labels[strategy].upper()}")
        print(f"{'='*60}")
        results[strategy] = run_strategy(strategy)

    # Comparison table
    baseline = results["none"]
    header = f"{'Metric':<25}"
    for s in strategies:
        header += f" {labels[s]:>12}"
    print(f"\n{'='*75}")
    print(f"  COMPARISON")
    print(f"{'='*75}")
    print(header)
    print("-" * 75)

    metrics = [
        ("Total Happiness", "total_park_happiness", ".0f"),
        ("Avg Happiness", "avg_happiness", ".2f"),
        ("Avg Wait (min)", "avg_wait", ".1f"),
        ("Avg Rides", "avg_rides", ".1f"),
        ("Total Rides", "total_rides", "d"),
        ("Total Passes Used", "total_passes_used", "d"),
        ("Peak Queue", "peak_queue", "d"),
    ]

    for label, key, fmt in metrics:
        row = f"{label:<25}"
        for s in strategies:
            val = results[s].get(key, 0)
            row += f" {val:>12{fmt}}"
        print(row)

    # Improvement percentages
    print()
    pct_header = f"{'% Change vs Baseline':<25}"
    for s in strategies:
        pct_header += f" {labels[s]:>12}"
    print(pct_header)
    print("-" * 75)

    pct_metrics = [
        ("Total Happiness", "total_park_happiness"),
        ("Avg Wait", "avg_wait"),
        ("Avg Rides", "avg_rides"),
        ("Total Rides", "total_rides"),
    ]

    for label, key in pct_metrics:
        base_val = baseline[key]
        if base_val == 0:
            continue
        row = f"{label:<25} {'---':>12}"
        for s in strategies[1:]:
            pct = (results[s][key] - base_val) / base_val * 100
            row += f" {pct:>+11.1f}%"
        print(row)

    # Most congested ride per strategy
    print()
    print("Most congested ride:")
    for s in strategies:
        r = results[s]
        print(f"  {labels[s]:<16}: {r['most_congested']} (peak queue: {r['peak_queue']})")


if __name__ == "__main__":
    main()
