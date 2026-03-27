"""
Theme Park Network Congestion Game — Simulation Engine
"""

import numpy as np
from park_model import (
    Park, Agent, NodeType, PARK_OPEN, PARK_CLOSE, build_epic_universe,
)


class Simulation:
    """Discrete-time simulation of agents navigating a theme park network."""

    def __init__(self, park: Park, num_agents: int = 500,
                 dt: float = 1.0, seed: int = 42):
        self.park = park
        self.num_agents = num_agents
        self.dt = dt                    # time step in minutes
        self.rng = np.random.default_rng(seed)
        self.current_time: float = PARK_OPEN
        self.agents: list[Agent] = []

        # History: one snapshot per timestep
        self.history: list[dict] = []

    # ------------------------------------------------------------------
    # Agent generation
    # ------------------------------------------------------------------

    def generate_agents(self) -> None:
        """Create agents with stochastic arrival/departure times and preferences."""
        # Arrival peaks ~11am (120 min after 9am open), departure ~7pm (600 min)
        arrivals = self.rng.normal(loc=120, scale=45, size=self.num_agents)
        departures = self.rng.normal(loc=600, scale=60, size=self.num_agents)

        # Clip to valid park hours and ensure departure > arrival
        arrivals = np.clip(arrivals, PARK_OPEN, PARK_CLOSE - 60)
        departures = np.clip(departures, arrivals + 60, PARK_CLOSE)

        attractions = self.park.get_attractions()

        for i in range(self.num_agents):
            agent = Agent(
                agent_id=i,
                arrival_time=float(arrivals[i]),
                departure_time=float(departures[i]),
                preference_noise=0.1,
                decision_paralysis=self.rng.uniform(0.05, 0.20),
            )

            # Per-agent preference multipliers for each attraction
            for attr in attractions:
                # Base preference ~1.0 with some randomness per agent
                agent.preferences[attr.name] = max(
                    0.1, self.rng.normal(loc=1.0, scale=0.25)
                )

            self.agents.append(agent)

    # ------------------------------------------------------------------
    # Simulation step
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Advance the simulation by one timestep (dt minutes)."""
        t = self.current_time

        # Phase 1: Arrivals — activate agents entering the park
        for agent in self.agents:
            if agent.state == "inactive" and agent.arrival_time <= t:
                agent.state = "deciding"
                agent.current_node = "Celestial Park"  # park entrance

        # Phase 2: Ride processing — dispatch riders on completed cycles
        for node in self.park.get_attractions():
            if len(node.queue) == 0:
                node.cycle_timer = 0.0
                continue
            node.cycle_timer += self.dt
            if node.cycle_timer >= node.service_rate:
                finished = node.process_cycle()
                node.cycle_timer = 0.0
                for agent in finished:
                    decay = agent._decay(t)
                    pref = agent.preferences.get(node.name, 1.0)
                    agent.total_happiness += node.happiness * pref * decay
                    agent.rides_completed.append(node.name)
                    agent.state = "deciding"
                    agent.current_node = node.name

        # Phase 3: Departures — agents leaving the park
        for agent in self.agents:
            if agent.state == "departed":
                continue
            if agent.state != "inactive" and agent.departure_time <= t:
                # Remove from any queue
                if agent.state == "queued" and agent.current_node:
                    node = self.park.nodes.get(agent.target_node)
                    if node:
                        node.remove_from_queue(agent)
                agent.state = "departed"

        # Phase 4: Decisions — agents choose their next attraction
        for agent in self.agents:
            if agent.state != "deciding":
                continue
            best = agent.choose_next_attraction(self.park, t)
            if best is not None:
                travel = self.park.travel_time(agent.current_node, best)
                agent.target_node = best
                agent.time_remaining = travel
                agent.state = "traveling"
            else:
                # Nothing worth doing — depart early
                agent.state = "departed"

        # Phase 5: Travel updates — agents moving between nodes
        for agent in self.agents:
            if agent.state != "traveling":
                continue
            agent.time_remaining -= self.dt
            agent.total_travel_time += self.dt
            if agent.time_remaining <= 0:
                agent.current_node = agent.target_node
                target_node = self.park.nodes[agent.target_node]
                if target_node.node_type == NodeType.ATTRACTION:
                    target_node.add_to_queue(agent)
                    agent.state = "queued"
                else:
                    agent.state = "deciding"

        # Phase 6: Track wait time for queued agents
        for agent in self.agents:
            if agent.state == "queued":
                agent.total_wait_time += self.dt

        # Phase 7: Record snapshot
        self._record_snapshot()

        # Advance time
        self.current_time += self.dt

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Run the full simulation from park open to close."""
        print(f"Running simulation: {self.num_agents} agents, "
              f"dt={self.dt}min, {PARK_CLOSE - PARK_OPEN} min day")

        while self.current_time <= PARK_CLOSE:
            self.step()
            # Progress update every simulated hour
            if int(self.current_time) % 60 == 0 and self.current_time > PARK_OPEN:
                hour = 9 + int(self.current_time) // 60
                active = sum(1 for a in self.agents
                             if a.state not in ("inactive", "departed"))
                print(f"  {hour}:00 — {active} agents in park")

        return self.summary()

    # ------------------------------------------------------------------
    # Snapshot & summary
    # ------------------------------------------------------------------

    def _record_snapshot(self) -> None:
        """Capture the current state for later analysis."""
        queue_lengths = {}
        for node in self.park.get_attractions():
            queue_lengths[node.name] = len(node.queue)

        state_counts = {}
        for agent in self.agents:
            state_counts[agent.state] = state_counts.get(agent.state, 0) + 1

        self.history.append({
            "time": self.current_time,
            "queue_lengths": queue_lengths,
            "state_counts": state_counts,
        })

    def summary(self) -> dict:
        """Compute aggregate statistics from the completed simulation."""
        departed = [a for a in self.agents if a.state == "departed"]
        active_agents = [a for a in self.agents
                         if len(a.rides_completed) > 0 or a.total_happiness > 0]

        if not active_agents:
            return {"avg_happiness": 0, "avg_wait": 0, "avg_rides": 0}

        happinesses = [a.total_happiness for a in active_agents]
        waits = [a.total_wait_time for a in active_agents]
        rides = [len(a.rides_completed) for a in active_agents]
        travels = [a.total_travel_time for a in active_agents]

        # Most congested ride (peak queue length)
        peak_queues = {}
        for snapshot in self.history:
            for ride, ql in snapshot["queue_lengths"].items():
                peak_queues[ride] = max(peak_queues.get(ride, 0), ql)

        most_congested = max(peak_queues, key=peak_queues.get) if peak_queues else "N/A"

        results = {
            "num_agents": len(active_agents),
            "avg_happiness": np.mean(happinesses),
            "median_happiness": np.median(happinesses),
            "std_happiness": np.std(happinesses),
            "avg_wait": np.mean(waits),
            "avg_travel": np.mean(travels),
            "avg_rides": np.mean(rides),
            "most_congested": most_congested,
            "peak_queue": peak_queues.get(most_congested, 0),
        }
        return results

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_results(self) -> None:
        """Generate visualization of simulation results."""
        import matplotlib.pyplot as plt

        times = [s["time"] for s in self.history]
        attractions = self.park.get_attractions()

        # --- Figure 1: Queue lengths over time ---
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        ax = axes[0, 0]
        for attr in attractions:
            ql = [s["queue_lengths"].get(attr.name, 0) for s in self.history]
            ax.plot(times, ql, label=attr.name, alpha=0.7)
        ax.set_xlabel("Time (minutes from open)")
        ax.set_ylabel("Queue Length")
        ax.set_title("Queue Lengths Over Time")
        ax.legend(fontsize=6, ncol=2)

        # --- Figure 2: Active agents in park over time ---
        ax = axes[0, 1]
        active_counts = []
        for s in self.history:
            sc = s["state_counts"]
            active = sum(v for k, v in sc.items() if k not in ("inactive", "departed"))
            active_counts.append(active)
        ax.plot(times, active_counts, color="steelblue")
        ax.set_xlabel("Time (minutes from open)")
        ax.set_ylabel("Agents in Park")
        ax.set_title("Park Population Over Time")

        # --- Figure 3: Happiness distribution ---
        ax = axes[1, 0]
        happinesses = [a.total_happiness for a in self.agents
                       if a.state == "departed" and a.total_happiness > 0]
        if happinesses:
            ax.hist(happinesses, bins=30, color="coral", edgecolor="black")
        ax.set_xlabel("Total Happiness")
        ax.set_ylabel("Number of Agents")
        ax.set_title("Happiness Distribution")

        # --- Figure 4: Rides completed distribution ---
        ax = axes[1, 1]
        ride_counts = [len(a.rides_completed) for a in self.agents
                       if a.state == "departed"]
        if ride_counts:
            ax.hist(ride_counts, bins=range(0, max(ride_counts) + 2),
                    color="mediumpurple", edgecolor="black")
        ax.set_xlabel("Rides Completed")
        ax.set_ylabel("Number of Agents")
        ax.set_title("Rides Completed Distribution")

        plt.tight_layout()
        plt.savefig("simulation_results.png", dpi=150)
        plt.show()
        print("Saved plot to simulation_results.png")


# ======================================================================
# Main
# ======================================================================

if __name__ == "__main__":
    park = build_epic_universe()
    print(f"Built park: {park}")
    print(f"  Hubs: {[n.name for n in park.get_hubs()]}")
    print(f"  Attractions: {[n.name for n in park.get_attractions()]}")

    sim = Simulation(park, num_agents=500, dt=1.0, seed=42)
    sim.generate_agents()
    results = sim.run()

    print("\n=== RESULTS ===")
    print(f"  Active agents:       {results['num_agents']}")
    print(f"  Avg happiness:       {results['avg_happiness']:.2f}")
    print(f"  Median happiness:    {results['median_happiness']:.2f}")
    print(f"  Std happiness:       {results['std_happiness']:.2f}")
    print(f"  Avg wait time:       {results['avg_wait']:.2f} min")
    print(f"  Avg travel time:     {results['avg_travel']:.2f} min")
    print(f"  Avg rides completed: {results['avg_rides']:.1f}")
    print(f"  Most congested ride: {results['most_congested']} "
          f"(peak queue: {results['peak_queue']})")

    sim.plot_results()
