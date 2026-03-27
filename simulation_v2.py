"""
Theme Park Network Congestion Game — Event-Driven Simulation (V2)
Uses a priority-queue event loop instead of fixed time steps.
"""

import heapq
import numpy as np
import matplotlib.pyplot as plt
from park_model_v2 import (
    Park, Node, Agent, AgentState, NodeType,
    Event, EventType,
    PARK_OPEN, PARK_CLOSE, build_epic_universe,
)


class Simulation:
    """Event-driven simulation: events are processed in time order via a heap."""

    def __init__(self, park: Park, num_agents: int = 500, seed: int = 42):
        self.park = park
        self.num_agents = num_agents
        self.rng = np.random.default_rng(seed)
        self.agents: list[Agent] = []
        self.event_queue: list[Event] = []  # min-heap of Event objects
        self.current_time: float = PARK_OPEN

        # Sampling interval for recording snapshots (every N minutes)
        self.snapshot_interval = 1.0
        self.history: list[dict] = []

    # ------------------------------------------------------------------
    # Event scheduling
    # ------------------------------------------------------------------

    def schedule(self, time: float, event_type: EventType, **data) -> None:
        heapq.heappush(self.event_queue, Event(time, event_type, data))

    # ------------------------------------------------------------------
    # Agent generation
    # ------------------------------------------------------------------

    def generate_agents(self) -> None:
        arrivals = np.clip(
            self.rng.normal(120, 45, self.num_agents), PARK_OPEN, PARK_CLOSE - 60
        )
        departures = np.clip(
            self.rng.normal(600, 60, self.num_agents), arrivals + 60, PARK_CLOSE
        )

        for i in range(self.num_agents):
            agent = Agent(
                agent_id=i,
                arrival_time=float(arrivals[i]),
                departure_time=float(departures[i]),
                decision_paralysis=float(self.rng.uniform(0.05, 0.20)),
            )
            # Random per-agent preferences
            for attr in self.park.attractions:
                agent.preferences[attr.name] = float(
                    max(0.1, self.rng.normal(1.0, 0.25))
                )
            self.agents.append(agent)

            # Schedule arrival and departure events
            self.schedule(agent.arrival_time, EventType.AGENT_ARRIVES, agent_id=i)
            self.schedule(agent.departure_time, EventType.AGENT_DEPARTS, agent_id=i)

        # Schedule ride dispatches for all attractions
        for attr in self.park.attractions:
            self.schedule(PARK_OPEN + attr.ride_duration, EventType.RIDE_DISPATCH,
                          ride_name=attr.name)

        # Schedule periodic snapshots
        t = PARK_OPEN
        while t <= PARK_CLOSE:
            self.schedule(t, EventType.AGENT_ARRIVES, snapshot_only=True)
            t += self.snapshot_interval

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _handle_arrival(self, event: Event) -> None:
        """Agent enters the park and makes their first decision."""
        if event.data.get("snapshot_only"):
            self._record_snapshot()
            return

        agent = self.agents[event.data["agent_id"]]
        if agent.state != AgentState.INACTIVE:
            return
        agent.state = AgentState.DECIDING
        agent.current_node = "Celestial Park"
        self._agent_decide(agent)

    def _handle_departure(self, event: Event) -> None:
        """Agent leaves the park."""
        agent = self.agents[event.data["agent_id"]]
        if agent.state == AgentState.DEPARTED:
            return

        # Remove from queue if queued
        if agent.state == AgentState.QUEUED and agent.target_node:
            node = self.park.node(agent.target_node)
            if agent in node.queue:
                node.queue.remove(agent)

        agent.state = AgentState.DEPARTED

    def _handle_agent_reaches_dest(self, event: Event) -> None:
        """Agent arrives at their target node after traveling."""
        agent = self.agents[event.data["agent_id"]]
        if agent.state != AgentState.TRAVELING:
            return

        travel_time = event.data.get("travel_time", 0)
        agent.total_travel_time += travel_time
        agent.current_node = agent.target_node
        target = self.park.node(agent.target_node)

        if target.node_type == NodeType.ATTRACTION:
            target.queue.append(agent)
            agent.state = AgentState.QUEUED
        else:
            agent.state = AgentState.DECIDING
            self._agent_decide(agent)

    def _handle_ride_dispatch(self, event: Event) -> None:
        """A ride completes a cycle: unload riders, they decide next move."""
        ride_name = event.data["ride_name"]
        ride = self.park.node(ride_name)

        if ride.queue:
            finished = ride.dispatch_riders()
            for agent in finished:
                if agent.state == AgentState.DEPARTED:
                    continue
                pref = agent.preferences.get(ride_name, 1.0)
                happiness_gained = ride.happiness * pref * agent.decay(self.current_time)
                agent.total_happiness += happiness_gained
                agent.rides_completed.append(ride_name)
                agent.current_node = ride_name
                agent.state = AgentState.DECIDING
                self._agent_decide(agent)

            # Track wait time for remaining queued agents
            for agent in ride.queue:
                if agent.state == AgentState.QUEUED:
                    agent.total_wait_time += ride.ride_duration

        # Schedule next dispatch for this ride
        next_time = self.current_time + ride.ride_duration
        if next_time <= PARK_CLOSE:
            self.schedule(next_time, EventType.RIDE_DISPATCH, ride_name=ride_name)

    # ------------------------------------------------------------------
    # Agent decision-making
    # ------------------------------------------------------------------

    def _agent_decide(self, agent: Agent) -> None:
        """Agent picks next attraction and starts traveling."""
        if agent.state == AgentState.DEPARTED:
            return

        best = agent.best_attraction(self.park, self.current_time)
        if best is None:
            agent.state = AgentState.DEPARTED
            return

        agent.target_node = best
        travel = self.park.travel_time(agent.current_node, best)
        agent.state = AgentState.TRAVELING
        agent.time_remaining = travel

        arrive_time = self.current_time + travel
        self.schedule(arrive_time, EventType.AGENT_REACHES_DEST,
                      agent_id=agent.agent_id, travel_time=travel)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> dict:
        print(f"Running event-driven simulation: {self.num_agents} agents, "
              f"{PARK_CLOSE - PARK_OPEN} min day")
        print(f"  Total events scheduled: {len(self.event_queue)}")

        last_hour_printed = -1
        events_processed = 0

        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            self.current_time = event.time

            if self.current_time > PARK_CLOSE:
                break

            # Dispatch to handler
            if event.event_type == EventType.AGENT_ARRIVES:
                self._handle_arrival(event)
            elif event.event_type == EventType.AGENT_DEPARTS:
                self._handle_departure(event)
            elif event.event_type == EventType.AGENT_REACHES_DEST:
                self._handle_agent_reaches_dest(event)
            elif event.event_type == EventType.RIDE_DISPATCH:
                self._handle_ride_dispatch(event)

            events_processed += 1

            # Hourly progress
            hour = 9 + int(self.current_time) // 60
            if hour != last_hour_printed and self.current_time > PARK_OPEN:
                active = sum(1 for a in self.agents if a.is_active)
                print(f"  {hour}:00 — {active} agents in park")
                last_hour_printed = hour

        # Force-depart everyone still active
        for agent in self.agents:
            if agent.state != AgentState.DEPARTED:
                agent.state = AgentState.DEPARTED

        print(f"  Events processed: {events_processed}")
        return self.summary()

    # ------------------------------------------------------------------
    # Snapshot & summary
    # ------------------------------------------------------------------

    def _record_snapshot(self) -> None:
        queue_lengths = {a.name: len(a.queue) for a in self.park.attractions}
        active = sum(1 for a in self.agents if a.is_active)
        self.history.append({
            "time": self.current_time,
            "queue_lengths": queue_lengths,
            "active_agents": active,
        })

    def summary(self) -> dict:
        participated = [a for a in self.agents if len(a.rides_completed) > 0]
        if not participated:
            return {"avg_happiness": 0, "avg_wait": 0, "avg_rides": 0}

        h = [a.total_happiness for a in participated]
        w = [a.total_wait_time for a in participated]
        r = [len(a.rides_completed) for a in participated]
        t = [a.total_travel_time for a in participated]

        peak_queues = {}
        for snap in self.history:
            for ride, ql in snap["queue_lengths"].items():
                peak_queues[ride] = max(peak_queues.get(ride, 0), ql)

        most_congested = max(peak_queues, key=peak_queues.get) if peak_queues else "N/A"

        return {
            "num_agents": len(participated),
            "avg_happiness": float(np.mean(h)),
            "median_happiness": float(np.median(h)),
            "std_happiness": float(np.std(h)),
            "avg_wait": float(np.mean(w)),
            "avg_travel": float(np.mean(t)),
            "avg_rides": float(np.mean(r)),
            "most_congested": most_congested,
            "peak_queue": peak_queues.get(most_congested, 0),
        }

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_results(self) -> None:
        if not self.history:
            print("No history recorded — nothing to plot.")
            return

        times = [s["time"] for s in self.history]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"{self.park.name} Simulation Results ({self.num_agents} agents)",
                     fontsize=14, fontweight="bold")

        # 1. Queue lengths over time
        ax = axes[0, 0]
        for attr in self.park.attractions:
            ql = [s["queue_lengths"].get(attr.name, 0) for s in self.history]
            ax.plot(times, ql, label=attr.name, alpha=0.7, linewidth=1)
        ax.set_xlabel("Time (min from open)")
        ax.set_ylabel("Queue Length")
        ax.set_title("Queue Lengths Over Time")
        ax.legend(fontsize=5, ncol=2, loc="upper right")
        ax.grid(True, alpha=0.3)

        # 2. Park population over time
        ax = axes[0, 1]
        active = [s["active_agents"] for s in self.history]
        ax.fill_between(times, active, alpha=0.4, color="steelblue")
        ax.plot(times, active, color="steelblue", linewidth=1)
        ax.set_xlabel("Time (min from open)")
        ax.set_ylabel("Agents in Park")
        ax.set_title("Park Population Over Time")
        ax.grid(True, alpha=0.3)

        # 3. Happiness distribution
        ax = axes[1, 0]
        happinesses = [a.total_happiness for a in self.agents if a.total_happiness > 0]
        if happinesses:
            ax.hist(happinesses, bins=30, color="coral", edgecolor="black", alpha=0.8)
        ax.set_xlabel("Total Happiness")
        ax.set_ylabel("Count")
        ax.set_title("Happiness Distribution")
        ax.grid(True, alpha=0.3)

        # 4. Rides completed distribution
        ax = axes[1, 1]
        ride_counts = [len(a.rides_completed) for a in self.agents
                       if len(a.rides_completed) > 0]
        if ride_counts:
            ax.hist(ride_counts, bins=range(0, max(ride_counts) + 2),
                    color="mediumpurple", edgecolor="black", alpha=0.8)
        ax.set_xlabel("Rides Completed")
        ax.set_ylabel("Count")
        ax.set_title("Rides Completed Distribution")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("simulation_results_v2.png", dpi=150)
        plt.show()
        print("Saved plot to simulation_results_v2.png")


# ======================================================================
# Main
# ======================================================================

if __name__ == "__main__":
    park = build_epic_universe()
    print(f"Built park: {park}")
    print(f"  Hubs: {[n.name for n in park.hubs]}")
    print(f"  Attractions: {[n.name for n in park.attractions]}")

    sim = Simulation(park, num_agents=500, seed=42)
    sim.generate_agents()
    results = sim.run()

    print("\n=== RESULTS ===")
    for key, val in results.items():
        if isinstance(val, float):
            print(f"  {key:25s} {val:.2f}")
        else:
            print(f"  {key:25s} {val}")

    sim.plot_results()
