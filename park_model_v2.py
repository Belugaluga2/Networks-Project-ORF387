"""
Theme Park Network Congestion Game — Data Model (V2)
Uses dataclasses and networkx for cleaner graph operations.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
import networkx as nx
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARK_OPEN = 0       # minute 0 = 9:00 AM
PARK_CLOSE = 720    # minute 720 = 9:00 PM


class NodeType(Enum):
    HUB = auto()
    ATTRACTION = auto()


class AgentState(Enum):
    INACTIVE = auto()
    DECIDING = auto()
    TRAVELING = auto()
    QUEUED = auto()
    RIDING = auto()
    DEPARTED = auto()


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """A location in the park graph."""
    name: str
    node_type: NodeType
    area: str
    happiness: float = 0.0
    capacity: int = 0           # riders per dispatch
    ride_duration: float = 0.0  # minutes per ride cycle
    queue: list = field(default_factory=list, repr=False)
    cycle_timer: float = 0.0

    @property
    def wait_time(self) -> float:
        if self.capacity == 0:
            return 0.0
        return (len(self.queue) / self.capacity) * self.ride_duration

    def dispatch_riders(self) -> list:
        """Send up to `capacity` riders through. Returns finished agents."""
        batch = self.queue[:self.capacity]
        self.queue = self.queue[self.capacity:]
        return batch


# ---------------------------------------------------------------------------
# Park (networkx-based graph)
# ---------------------------------------------------------------------------

class Park:
    """Theme park as a networkx DiGraph. Nodes carry Node data, edges carry weight."""

    def __init__(self, name: str):
        self.name = name
        self.graph = nx.DiGraph()
        self._node_data: dict[str, Node] = {}

    def add_node(self, node: Node) -> None:
        self._node_data[node.name] = node
        self.graph.add_node(node.name, data=node)

    def add_edge(self, source: str, target: str, weight: float) -> None:
        self.graph.add_edge(source, target, weight=weight)

    def add_bidirectional_edge(self, a: str, b: str, weight: float) -> None:
        self.add_edge(a, b, weight)
        self.add_edge(b, a, weight)

    def node(self, name: str) -> Node:
        return self._node_data[name]

    def travel_time(self, source: str, target: str) -> float:
        if source == target:
            return 0.0
        try:
            return nx.shortest_path_length(self.graph, source, target, weight="weight")
        except nx.NetworkXNoPath:
            return float('inf')

    def shortest_path(self, source: str, target: str) -> list[str]:
        try:
            return nx.shortest_path(self.graph, source, target, weight="weight")
        except nx.NetworkXNoPath:
            return []

    @property
    def attractions(self) -> list[Node]:
        return [n for n in self._node_data.values() if n.node_type == NodeType.ATTRACTION]

    @property
    def hubs(self) -> list[Node]:
        return [n for n in self._node_data.values() if n.node_type == NodeType.HUB]

    def __repr__(self):
        return f"Park({self.name!r}, {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges)"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@dataclass
class Agent:
    """A utility-maximizing park visitor."""
    agent_id: int
    arrival_time: float
    departure_time: float
    decision_paralysis: float = 0.1

    # State
    state: AgentState = AgentState.INACTIVE
    current_node: str = ""
    target_node: str = ""
    time_remaining: float = 0.0

    # Tracking
    total_happiness: float = 0.0
    total_wait_time: float = 0.0
    total_travel_time: float = 0.0
    rides_completed: list = field(default_factory=list)
    preferences: dict = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.state not in (AgentState.INACTIVE, AgentState.DEPARTED)

    def time_left(self, current_time: float) -> float:
        return max(0.0, self.departure_time - current_time)

    def decay(self, current_time: float) -> float:
        """Linear happiness decay: 1.0 at arrival, 0.0 at departure."""
        stay_duration = self.departure_time - self.arrival_time
        if stay_duration <= 0:
            return 0.0
        return max(0.0, self.time_left(current_time) / stay_duration)

    def utility(self, attraction: Node, park: Park, current_time: float) -> float:
        """U(a) = H(a) * pref * decay - W(a) - D(curr, a) - switching_cost"""
        remaining = self.time_left(current_time)
        if remaining <= 0:
            return float('-inf')

        pref = self.preferences.get(attraction.name, 1.0)
        H = attraction.happiness * pref * self.decay(current_time)
        W = attraction.wait_time
        D = park.travel_time(self.current_node, attraction.name)

        # Can't finish in time?
        if D + W + attraction.ride_duration > remaining:
            return float('-inf')

        # Diminishing returns on re-rides
        repeats = self.rides_completed.count(attraction.name)
        if repeats > 0:
            H *= 0.3 ** repeats

        # Switching cost
        switch_cost = 0.0
        if self.target_node and self.target_node != attraction.name:
            switch_cost = self.decision_paralysis * H

        return H - W - D - switch_cost

    def best_attraction(self, park: Park, current_time: float) -> str | None:
        """Return name of highest-utility attraction, or None."""
        best_name, best_val = None, 0.0
        for attr in park.attractions:
            u = self.utility(attr, park, current_time)
            if u > best_val:
                best_val = u
                best_name = attr.name
        return best_name


# ---------------------------------------------------------------------------
# Event system (for event-driven simulation)
# ---------------------------------------------------------------------------

class EventType(Enum):
    AGENT_ARRIVES = auto()
    AGENT_DEPARTS = auto()
    AGENT_REACHES_DEST = auto()
    RIDE_DISPATCH = auto()


@dataclass(order=True)
class Event:
    """A scheduled event. Ordered by time for the priority queue."""
    time: float
    event_type: EventType = field(compare=False)
    data: dict = field(default_factory=dict, compare=False)


# ---------------------------------------------------------------------------
# Epic Universe Builder
# ---------------------------------------------------------------------------

def build_epic_universe() -> Park:
    park = Park("Epic Universe")

    # Hubs
    for name in ["Celestial Park", "Wizarding World", "Super Nintendo World",
                 "How to Train Your Dragon", "Dark Universe"]:
        park.add_node(Node(name, NodeType.HUB, area=name))

    # Attractions: (name, area, happiness, capacity, ride_duration)
    attractions = [
        ("Starfall Racers",              "Celestial Park",           8.0, 24, 3.0),
        ("Constellation Carousel",       "Celestial Park",           4.0, 40, 4.0),
        ("Harry Potter Coaster",         "Wizarding World",         10.0, 20, 4.5),
        ("Ministry of Magic",            "Wizarding World",          9.0, 16, 5.0),
        ("Mario Kart Bowsers Challenge", "Super Nintendo World",     9.5, 16, 5.0),
        ("Donkey Kong Mine Cart",        "Super Nintendo World",     9.0, 20, 3.5),
        ("Yoshis Adventure",             "Super Nintendo World",     5.0, 30, 4.0),
        ("Dragon Coaster",               "How to Train Your Dragon", 9.0, 24, 3.0),
        ("Hiccups Wing Gliders",         "How to Train Your Dragon", 6.5, 20, 3.5),
        ("Monsters Unchained",           "Dark Universe",            9.5, 18, 5.0),
        ("Curse of the Werewolf",        "Dark Universe",            7.0, 22, 3.0),
    ]
    for name, area, h, cap, dur in attractions:
        park.add_node(Node(name, NodeType.ATTRACTION, area, h, cap, dur))

    # Hub-to-hub connections (bidirectional)
    park.add_bidirectional_edge("Celestial Park", "Wizarding World", 5.0)
    park.add_bidirectional_edge("Celestial Park", "Super Nintendo World", 6.0)
    park.add_bidirectional_edge("Celestial Park", "How to Train Your Dragon", 5.0)
    park.add_bidirectional_edge("Celestial Park", "Dark Universe", 6.0)
    park.add_bidirectional_edge("Wizarding World", "Super Nintendo World", 8.0)
    park.add_bidirectional_edge("Dark Universe", "How to Train Your Dragon", 8.0)

    # Hub-to-attraction connections
    for name, area, *_ in attractions:
        park.add_bidirectional_edge(area, name, 1.5)

    return park
