"""
Export simulation data for the HTML visualization.
Runs the simulation and saves per-timestep snapshots to JSON.
"""

import json
from park_model import build_epic_universe, PARK_OPEN, PARK_CLOSE, NodeType
from simulation import Simulation


def export_visualization_data(output_path: str = "viz_data.json"):
    park = build_epic_universe()
    sim = Simulation(park, dt=1.0, seed=42)
    sim.generate_agents()

    # Build graph layout info for the visualization
    # Position hubs in a star layout with Celestial Park at center
    hub_positions = {
        "Celestial Park":        {"x": 400, "y": 300},
        "Super Nintendo World":  {"x": 150, "y": 150},
        "Dark Universe":         {"x": 650, "y": 150},
        "Wizarding World":       {"x": 650, "y": 450},
        "Isle of Berk":          {"x": 150, "y": 450},
    }

    # Position rides around their hub
    import math
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

    # Run simulation and capture detailed snapshots every minute
    print("Running simulation...")
    snapshots = []

    while sim.current_time <= PARK_CLOSE:
        sim.step()

        # Count agents at each node by state
        node_counts = {}
        for name in park.nodes:
            node_counts[name] = {"queued": 0, "deciding": 0, "riding": 0}

        traveling_edges = {}  # (source, target) -> count
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

        # Queue lengths for rides
        queue_lengths = {}
        for node in park.get_attractions():
            queue_lengths[node.name] = len(node.queue)

        snapshot = {
            "time": round(sim.current_time, 1),
            "hour": f"{9 + int(sim.current_time) // 60}:{int(sim.current_time) % 60:02d}",
            "total_in_park": total_in_park,
            "total_queued": total_queued,
            "total_traveling": total_traveling,
            "queue_lengths": queue_lengths,
            "node_counts": node_counts,
            "traveling_edges": traveling_edges,
        }
        snapshots.append(snapshot)

        if int(sim.current_time) % 60 == 0 and sim.current_time > 0:
            print(f"  {snapshot['hour']} — {total_in_park} in park")

    # Build output
    output = {
        "park_name": park.name,
        "total_agents": len(sim.agents),
        "nodes": nodes,
        "edges": edges,
        "snapshots": snapshots,
    }

    with open(output_path, "w") as f:
        json.dump(output, f)

    size_mb = len(json.dumps(output)) / 1024 / 1024
    print(f"\nExported {len(snapshots)} snapshots to {output_path} ({size_mb:.1f} MB)")
    return output


if __name__ == "__main__":
    export_visualization_data()
