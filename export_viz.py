"""
Export simulation data for the HTML visualization.
Runs all 4 strategies and saves per-timestep snapshots to a single JSON.
"""

import json
import math
from park_model import build_epic_universe, PARK_OPEN, PARK_CLOSE, NodeType
from simulation import Simulation


def build_graph_layout(park):
    """Compute node positions for visualization."""
    hub_positions = {
        "Celestial Park":        {"x": 400, "y": 300},
        "Super Nintendo World":  {"x": 150, "y": 150},
        "Dark Universe":         {"x": 650, "y": 150},
        "Wizarding World":       {"x": 650, "y": 450},
        "Isle of Berk":          {"x": 150, "y": 450},
    }

    ride_positions = {}
    for land_name, hub_pos in hub_positions.items():
        rides = [n for n in park.get_attractions() if n.area == land_name]
        n_rides = len(rides)
        for i, ride in enumerate(rides):
            angle = 2 * math.pi * i / max(n_rides, 1) - math.pi / 2
            radius = 70
            ride_positions[ride.name] = {
                "x": hub_pos["x"] + radius * math.cos(angle),
                "y": hub_pos["y"] + radius * math.sin(angle),
            }

    nodes = {}
    for name, pos in hub_positions.items():
        nodes[name] = {"x": pos["x"], "y": pos["y"], "type": "hub", "area": name}
    for name, pos in ride_positions.items():
        node = park.nodes[name]
        nodes[name] = {
            "x": pos["x"], "y": pos["y"],
            "type": "attraction",
            "area": node.area,
            "happiness": node.happiness,
            "capacity": node.capacity,
            "service_rate": node.service_rate,
        }

    edges = []
    for edge in park.edges:
        edges.append({
            "source": edge.source.name,
            "target": edge.target.name,
            "weight": edge.weight,
        })

    return nodes, edges


def run_and_capture(strategy: str, seed: int = 42):
    """Run a simulation and capture snapshots + summary."""
    park = build_epic_universe()
    sim = Simulation(park, dt=1.0, seed=seed, pass_strategy=strategy)
    sim.generate_agents()

    snapshots = []
    while sim.current_time <= PARK_CLOSE:
        sim.step()

        node_counts = {}
        for name in park.nodes:
            node_counts[name] = {"queued": 0, "deciding": 0, "riding": 0}

        traveling_edges = {}
        total_in_park = 0
        total_traveling = 0
        total_queued = 0

        for agent in sim.agents:
            if agent.state in ("inactive", "departed"):
                continue
            total_in_park += 1
            if agent.state == "queued" and agent.target_node:
                node_counts.setdefault(agent.target_node, {"queued": 0, "deciding": 0, "riding": 0})
                node_counts[agent.target_node]["queued"] += 1
                total_queued += 1
            elif agent.state == "deciding" and agent.current_node:
                node_counts.setdefault(agent.current_node, {"queued": 0, "deciding": 0, "riding": 0})
                node_counts[agent.current_node]["deciding"] += 1
            elif agent.state == "traveling" and agent.current_node and agent.target_node:
                key = f"{agent.current_node}|{agent.target_node}"
                traveling_edges[key] = traveling_edges.get(key, 0) + 1
                total_traveling += 1

        queue_lengths = {}
        for node in park.get_attractions():
            queue_lengths[node.name] = len(node.queue)

        snapshots.append({
            "time": round(sim.current_time, 1),
            "hour": f"{9 + int(sim.current_time) // 60}:{int(sim.current_time) % 60:02d}",
            "total_in_park": total_in_park,
            "total_queued": total_queued,
            "total_traveling": total_traveling,
            "queue_lengths": queue_lengths,
            "node_counts": node_counts,
            "traveling_edges": traveling_edges,
        })

        if int(sim.current_time) % 60 == 0 and sim.current_time > 0:
            print(f"    {snapshots[-1]['hour']} — {total_in_park} in park")

    results = sim.run_summary_only()
    return snapshots, results


def export_visualization_data(output_path: str = "viz_data.json"):
    park = build_epic_universe()
    nodes, edges = build_graph_layout(park)

    strategies = ["none", "preselect", "preselect_timed", "dynamic"]
    labels = {"none": "No Passes (Baseline)", "preselect": "Preselect (Anytime)",
              "preselect_timed": "Preselect (Timed Slots)", "dynamic": "Dynamic (On-Demand)"}

    all_strategies = {}
    for strategy in strategies:
        print(f"\n  Running: {labels[strategy]}")
        snapshots, summary = run_and_capture(strategy)
        all_strategies[strategy] = {
            "label": labels[strategy],
            "snapshots": snapshots,
            "summary": summary,
        }

    output = {
        "park_name": "Epic Universe",
        "nodes": nodes,
        "edges": edges,
        "strategies": all_strategies,
    }

    with open(output_path, "w") as f:
        json.dump(output, f)

    size_mb = len(json.dumps(output)) / 1024 / 1024
    print(f"\nExported {len(strategies)} strategies to {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    export_visualization_data()
