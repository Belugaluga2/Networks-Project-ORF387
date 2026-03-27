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
        self.happiness = happiness      # intrinsic happiness value (0 for hubs)
        self.capacity = capacity        # riders per cycle
        self.service_rate = service_rate  # minutes per ride cycle
        self.queue: list = []           # agents currently in line
        self.cycle_timer: float = 0.0   # tracks time since last dispatch

    @property
    def current_wait_time(self) -> float:
        """Estimated wait time based on queue length and throughput."""
        if self.node_type == NodeType.HUB or self.capacity == 0:
            return 0.0
        cycles_needed = len(self.queue) / self.capacity
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

    def __init__(self, agent_id: int, arrival_time: float, departure_time: float,
                 preference_noise: float = 0.1, decision_paralysis: float = 0.1):
        self.agent_id = agent_id
        self.arrival_time = arrival_time
        self.departure_time = departure_time
        self.preference_noise = preference_noise  # randomness in preferences
        self.decision_paralysis = decision_paralysis

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

    def utility(self, attraction: Node, park: Park, current_time: float) -> float:
        """U(a) = H(a) * pref * decay - W(a) - D(curr, a) - paralysis_penalty"""
        time_left = self.departure_time - current_time
        if time_left <= 0:
            return float('-inf')

        decay = self._decay(current_time)
        pref = self.preferences.get(attraction.name, 1.0)

        H = attraction.happiness * pref * decay
        W = attraction.current_wait_time
        D = park.travel_time(self.current_node, attraction.name)

        # Can't make it in time
        total_time_needed = D + attraction.current_wait_time + attraction.service_rate
        if total_time_needed > time_left:
            return float('-inf')

        # Diminishing returns on re-rides
        times_ridden = self.rides_completed.count(attraction.name)
        if times_ridden > 0:
            H *= 0.3 ** times_ridden

        # Decision paralysis: cost of switching targets
        paralysis_cost = 0.0
        if self.target_node is not None and self.target_node != attraction.name:
            paralysis_cost = self.decision_paralysis * H

        return H - W - D - paralysis_cost

    def choose_next_attraction(self, park: Park, current_time: float) -> str | None:
        """Pick the attraction with highest utility. Returns None if nothing is worth it."""
        best_name = None
        best_util = 0.0  # threshold: only go if utility is positive

        for attraction in park.get_attractions():
            u = self.utility(attraction, park, current_time)
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
    """Construct the Epic Universe park graph."""
    park = Park("Epic Universe")

    # --- Hub Nodes (themed areas) ---
    hubs = [
        "Celestial Park",
        "Wizarding World",
        "Super Nintendo World",
        "How to Train Your Dragon",
        "Dark Universe",
    ]
    for name in hubs:
        park.add_node(Node(name, NodeType.HUB, area=name))

    # --- Attraction Nodes ---
    # (name, area, happiness, capacity_per_cycle, service_rate_minutes)
    attractions = [
        # Celestial Park
        ("Starfall Racers",           "Celestial Park",          8.0, 24, 3.0),
        ("Constellation Carousel",    "Celestial Park",          4.0, 40, 4.0),

        # Wizarding World
        ("Harry Potter Coaster",      "Wizarding World",        10.0, 20, 4.5),
        ("Ministry of Magic",         "Wizarding World",         9.0, 16, 5.0),

        # Super Nintendo World
        ("Mario Kart Bowsers Challenge", "Super Nintendo World",  9.5, 16, 5.0),
        ("Donkey Kong Mine Cart",     "Super Nintendo World",     9.0, 20, 3.5),
        ("Yoshis Adventure",          "Super Nintendo World",     5.0, 30, 4.0),

        # How to Train Your Dragon
        ("Dragon Coaster",            "How to Train Your Dragon", 9.0, 24, 3.0),
        ("Hiccups Wing Gliders",      "How to Train Your Dragon", 6.5, 20, 3.5),

        # Dark Universe
        ("Monsters Unchained",        "Dark Universe",            9.5, 18, 5.0),
        ("Curse of the Werewolf",     "Dark Universe",            7.0, 22, 3.0),
    ]
    for name, area, h, cap, sr in attractions:
        park.add_node(Node(name, NodeType.ATTRACTION, area, h, cap, sr))

    # --- Hub-to-Hub Edges (walking times in minutes, bidirectional) ---
    # Celestial Park is the central spoke connecting all areas
    hub_connections = [
        ("Celestial Park", "Wizarding World",        5.0),
        ("Celestial Park", "Super Nintendo World",   6.0),
        ("Celestial Park", "How to Train Your Dragon", 5.0),
        ("Celestial Park", "Dark Universe",          6.0),
        # Adjacent worlds have longer cross-connections
        ("Wizarding World", "Super Nintendo World",  8.0),
        ("Dark Universe", "How to Train Your Dragon", 8.0),
    ]
    for s, t, w in hub_connections:
        park.add_edge(s, t, w)
        park.add_edge(t, s, w)

    # --- Hub-to-Attraction Edges (short walk to ride entrance) ---
    for name, area, *_ in attractions:
        park.add_edge(area, name, 1.5)  # hub -> attraction
        park.add_edge(name, area, 1.5)  # attraction -> hub

    return park
