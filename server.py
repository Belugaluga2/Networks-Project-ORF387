"""
Backend server for the Epic Universe simulation visualization.

Runs simulations on demand. The browser POSTs a (pass_strategy, behaviors)
combination, the server runs one full-day simulation (~10s), and returns
snapshots + summary as JSON.

Usage:
    python server.py
    # then open http://localhost:5000/
"""

import random

from flask import Flask, request, jsonify, send_from_directory
from park_model import build_epic_universe, PARK_CLOSE
from simulation import Simulation
from export_viz import build_graph_layout, capture_snapshot

app = Flask(__name__, static_folder=".", static_url_path="")

# Static park layout — graph topology never changes between runs
_PARK_FOR_LAYOUT = build_epic_universe()
NODES, EDGES = build_graph_layout(_PARK_FOR_LAYOUT)

PASS_LABELS = {
    "none": "No Passes (Baseline)",
    "preselect": "Preselect (Anytime)",
    "preselect_timed": "Preselect (Timed Slots)",
    "dynamic": "Dynamic (On-Demand)",
    "express": "Express Pass (Universal-style)",
}

BEHAVIOR_LABELS = {
    "fatigue": "Direction Change Fatigue",
    "info_restricted": "Information Restrictions",
    "proximity_bias": "Proximity Bias",
    "decision_paralysis": "Decision Paralysis",
    "eating_resting": "Eating / Resting",
}


@app.route("/")
def index():
    return send_from_directory(".", "visualization.html")


@app.route("/<path:filename>")
def static_file(filename):
    return send_from_directory(".", filename)


@app.route("/api/park")
def park_layout():
    """Return the static park graph (nodes, edges) and dropdown labels."""
    return jsonify({
        "park_name": "Epic Universe",
        "nodes": NODES,
        "edges": EDGES,
        "pass_labels": PASS_LABELS,
        "behavior_labels": BEHAVIOR_LABELS,
    })


@app.route("/api/simulate", methods=["POST"])
def simulate():
    """Run one full-day simulation with the requested pass strategy and behaviors."""
    payload = request.get_json(force=True) or {}
    pass_strategy = payload.get("pass_strategy", "none")
    behaviors = payload.get("behaviors", []) or []
    raw_seed = payload.get("seed")
    if raw_seed is None:
        seed = random.randint(0, 2**31 - 1)
    else:
        seed = int(raw_seed)
    # Express Pass holders fraction (only meaningful when pass_strategy == "express")
    express_pct = float(payload.get("express_pct", 0.3))
    if not (0.0 <= express_pct <= 1.0):
        return jsonify({"error": f"express_pct must be in [0, 1]: got {express_pct}"}), 400

    if pass_strategy not in PASS_LABELS:
        return jsonify({"error": f"unknown pass_strategy: {pass_strategy}"}), 400
    for b in behaviors:
        if b not in BEHAVIOR_LABELS:
            return jsonify({"error": f"unknown behavior: {b}"}), 400

    park = build_epic_universe()
    sim = Simulation(
        park,
        dt=1.0,
        seed=seed,
        pass_strategy=pass_strategy,
        behaviors=behaviors,
        express_pct=express_pct,
    )
    sim.generate_agents()

    snapshots = []
    while sim.current_time <= PARK_CLOSE:
        sim.step()
        snapshots.append(capture_snapshot(sim, park))

    summary = sim.run_summary_only()
    agent_records = sim.agent_records()

    behavior_label = (
        " + ".join(BEHAVIOR_LABELS[b] for b in sorted(behaviors))
        if behaviors else "Perfectly Rational"
    )
    pass_label = PASS_LABELS[pass_strategy]
    if pass_strategy == "express":
        pass_label = f"{pass_label} ({int(round(express_pct * 100))}%)"
    label = f"{pass_label} + {behavior_label}"

    return jsonify({
        "label": label,
        "snapshots": snapshots,
        "summary": summary,
        "agents": agent_records,
        "pass_strategy": pass_strategy,
        "behaviors": sorted(behaviors),
        "seed": seed,
        "express_pct": express_pct,
    })


if __name__ == "__main__":
    print("Starting Epic Universe simulation server on http://localhost:5000/")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
