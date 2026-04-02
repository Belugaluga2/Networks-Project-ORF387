"""
Theme Park Network Congestion Game — Data Model
Classes: Node, Edge, Park, Agent
Builder: build_epic_universe()
"""

from enum import Enum
import heapq
import numpy as np
from collections import defaultdict


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARK_OPEN = 0       # minute 0 = 9:00 AM
PARK_CLOSE = 720    # minute 720 = 9:00 PM (12-hour day)


class NodeType(Enum):
    HUB = "hub"
    ATTRACTION = "attraction"


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class Node:
    """A location in the park: either a hub (themed area) or an attraction (ride)."""

    def __init__(self, name: str, node_type: NodeType, area: str,
                 happiness: float = 0.0, capacity: int = 0,
                 service_rate: float = 0.0):
        self.name = name
        self.node_type = node_type
        self.area = area                # which themed area this belongs to
        self.happiness = happiness      # enjoyment score (0 for hubs)
        self.capacity = capacity        # riders per cycle
        self.service_rate = service_rate  # minutes per ride cycle
        self.queue: list = []           # agents currently in line
        self.pending_arrivals: int = 0  # agents committed but still traveling
        self.cycle_timer: float = 0.0   # tracks time since last dispatch

    @property
    def current_wait_time(self) -> float:
        """Estimated wait time based on queue length, pending arrivals, and throughput."""
        if self.node_type == NodeType.HUB or self.capacity == 0:
            return 0.0
        total_demand = len(self.queue) + self.pending_arrivals
        cycles_needed = total_demand / self.capacity
        return cycles_needed * self.service_rate

    def add_to_queue(self, agent) -> None:
        self.queue.append(agent)

    def remove_from_queue(self, agent) -> None:
        if agent in self.queue:
            self.queue.remove(agent)

    def process_cycle(self) -> list:
        """Remove up to `capacity` agents from front of queue (they finished the ride).
        Returns list of agents who completed the ride."""
        if self.node_type == NodeType.HUB or self.capacity == 0:
            return []
        finished = self.queue[:self.capacity]
        self.queue = self.queue[self.capacity:]
        return finished

    def __repr__(self):
        return f"Node({self.name!r}, {self.node_type.value})"


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------

class Edge:
    """A directed connection between two nodes with a travel time weight."""

    def __init__(self, source: Node, target: Node, weight: float):
        self.source = source
        self.target = target
        self.weight = weight    # walking time in minutes

    def __repr__(self):
        return f"Edge({self.source.name!r} -> {self.target.name!r}, {self.weight}min)"


# ---------------------------------------------------------------------------
# Park (the network graph)
# ---------------------------------------------------------------------------

class Park:
    """The theme park as a directed weighted graph."""

    def __init__(self, name: str):
        self.name = name
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.adj: dict[str, list[Edge]] = defaultdict(list)

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, source_name: str, target_name: str, weight: float) -> None:
        source = self.nodes[source_name]
        target = self.nodes[target_name]
        edge = Edge(source, target, weight)
        self.edges.append(edge)
        self.adj[source_name].append(edge)

    def shortest_distances_from(self, source_name: str) -> dict[str, float]:
        """Single-source Dijkstra returning distances to all reachable nodes."""
        dist = {name: float('inf') for name in self.nodes}
        dist[source_name] = 0.0
        pq = [(0.0, source_name)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for edge in self.adj[u]:
                v = edge.target.name
                new_dist = d + edge.weight
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    heapq.heappush(pq, (new_dist, v))
        return dist

    def shortest_path(self, source_name: str, target_name: str) -> tuple[list[str], float]:
        """Dijkstra's algorithm. Returns (path_as_node_names, total_time)."""
        dist = {name: float('inf') for name in self.nodes}
        prev = {name: None for name in self.nodes}
        dist[source_name] = 0.0
        pq = [(0.0, source_name)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == target_name:
                break
            for edge in self.adj[u]:
                v = edge.target.name
                new_dist = d + edge.weight
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(pq, (new_dist, v))

        # Reconstruct path
        path = []
        current = target_name
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        if dist[target_name] == float('inf'):
            return [], float('inf')
        return path, dist[target_name]

    def travel_time(self, source_name: str, target_name: str) -> float:
        """Total travel time between any two nodes."""
        if source_name == target_name:
            return 0.0
        _, time = self.shortest_path(source_name, target_name)
        return time

    def get_attractions(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.node_type == NodeType.ATTRACTION]

    def get_hubs(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.node_type == NodeType.HUB]

    def hub_for_attraction(self, attraction_name: str) -> Node:
        """Return the hub node that an attraction belongs to."""
        area = self.nodes[attraction_name].area
        for node in self.nodes.values():
            if node.node_type == NodeType.HUB and node.area == area:
                return node
        return None

    def __repr__(self):
        return (f"Park({self.name!r}, {len(self.nodes)} nodes, "
                f"{len(self.edges)} edges)")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    """A park visitor who makes utility-maximizing decisions."""

    def __init__(self, agent_id: int, arrival_time: float, departure_time: float):
        self.agent_id = agent_id
        self.arrival_time = arrival_time
        self.departure_time = departure_time

        # State
        self.current_node: str | None = None
        self.target_node: str | None = None
        self.state: str = "inactive"  # inactive, traveling, queued, riding, deciding, departed
        self.time_remaining: float = 0.0

        # Tracking
        self.total_happiness: float = 0.0
        self.total_wait_time: float = 0.0
        self.total_travel_time: float = 0.0
        self.rides_completed: list[str] = []

        # Per-agent preference multipliers (set during generation)
        self.preferences: dict[str, float] = {}

    def _decay(self, current_time: float) -> float:
        """Linear happiness decay: full at arrival, zero at departure."""
        total_stay = self.departure_time - self.arrival_time
        if total_stay <= 0:
            return 0.0
        time_left = self.departure_time - current_time
        return max(0.0, time_left / total_stay)

    def utility(self, attraction: Node, park: Park, current_time: float,
                distances: dict[str, float] | None = None) -> float:
        """U(a) = H(a) * pref * decay * reride_penalty / sqrt(1 + W + D)

        Always non-negative. Higher enjoyment and lower wait/travel = higher utility.
        """
        import math

        time_left = self.departure_time - current_time
        if time_left <= 0:
            return float('-inf')

        decay = self._decay(current_time)
        pref = self.preferences.get(attraction.name, 1.0)

        H = attraction.happiness * pref * decay
        W = attraction.current_wait_time

        # Use pre-computed distances if available, otherwise compute
        if distances is not None:
            D = distances.get(attraction.name, float('inf'))
        else:
            D = park.travel_time(self.current_node, attraction.name)

        # Can't make it in time
        total_time_needed = D + W + attraction.service_rate
        if total_time_needed > time_left:
            return float('-inf')

        # Diminishing returns on re-rides: 1/(1 + 0.5n)
        # 1st ride: 100%, 2nd: 67%, 3rd: 50%, 4th: 40%, 5th: 33%
        times_ridden = self.rides_completed.count(attraction.name)
        reride_penalty = 1.0 / (1.0 + 0.5 * times_ridden)

        return H * reride_penalty / math.sqrt(1.0 + W + D)

    def choose_next_attraction(self, park: Park, current_time: float) -> str | None:
        """Pick the attraction with highest utility. Returns None if nothing is worth it."""
        best_name = None
        best_util = 0.0  # threshold: only go if utility is positive

        # Single Dijkstra from current position
        distances = park.shortest_distances_from(self.current_node)

        for attraction in park.get_attractions():
            u = self.utility(attraction, park, current_time, distances)
            if u > best_util:
                best_util = u
                best_name = attraction.name

        return best_name

    def __repr__(self):
        return f"Agent({self.agent_id}, state={self.state!r})"


# ---------------------------------------------------------------------------
# Epic Universe Builder
# ---------------------------------------------------------------------------

def build_epic_universe() -> Park:
    """Construct the Epic Universe park graph from real attraction data."""
    from attraction_data import ATTRACTIONS, HUB_WALKING_TIMES, LANDS

    park = Park("Epic Universe")

    # Hub nodes (one per land)
    for land_name in LANDS:
        park.add_node(Node(land_name, NodeType.HUB, area=land_name))

    # Ride nodes only (skip non-rides)
    for name, data in ATTRACTIONS.items():
        if data["type"] != "ride":
            continue
        cap_per_cycle = int(round(data["hourly_capacity"] * data["ride_time_min"] / 60))
        park.add_node(Node(
            name=name,
            node_type=NodeType.ATTRACTION,
            area=data["land"],
            happiness=data["enjoyment_score"],
            capacity=cap_per_cycle,
            service_rate=data["ride_time_min"],
        ))

    # Hub-to-hub edges (bidirectional walking times)
    for (hub_a, hub_b), walk_time in HUB_WALKING_TIMES.items():
        park.add_edge(hub_a, hub_b, walk_time)
        park.add_edge(hub_b, hub_a, walk_time)

    # Hub-to-ride edges (1 min walking each direction, NOT wait time)
    for name, data in ATTRACTIONS.items():
        if data["type"] != "ride":
            continue
        park.add_edge(data["land"], name, 1.0)  # walk to ride entrance
        park.add_edge(name, data["land"], 1.0)  # walk back after riding

    return park
