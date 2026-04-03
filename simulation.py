"""
Theme Park Network Congestion Game — Simulation Engine
"""

import numpy as np
from park_model import (
    Park, Agent, NodeType, PARK_OPEN, PARK_CLOSE, build_epic_universe,
)


class Simulation:
    """Discrete-time simulation of agents navigating a theme park network."""

    def __init__(self, park: Park, dt: float = 1.0, seed: int = 42,
                 pass_strategy: str = "none"):
        self.park = park
        self.dt = dt                    # time step in minutes
        self.rng = np.random.default_rng(seed)
        self.current_time: float = PARK_OPEN
        self.agents: list[Agent] = []
        self.pass_strategy = pass_strategy  # "none", "preselect", "dynamic"

        # History: one snapshot per timestep
        self.history: list[dict] = []

    # ------------------------------------------------------------------
    # Agent generation
    # ------------------------------------------------------------------

    def generate_agents(self) -> None:
        """Create agents with stochastic arrival/departure times and preferences.

        Arrival model:
          - 3000 agents at gate rush, staggered over ~30 min (exponential)
          - 1000 agents/hour constant rate from t=30 to park close (Poisson)

        Preferences:
          - Multiplicative: pref ~ N(1.0, 0.3), floored at 0.1
          - Effective enjoyment = enjoyment_score * pref
        """
        attractions = self.park.get_attractions()
        agent_id = 0

        # Gate rush: 3000 agents staggered over first 30 minutes
        gate_arrivals = self.rng.exponential(scale=5.0, size=3000)
        gate_arrivals = np.clip(gate_arrivals, 0, 30)
        gate_arrivals.sort()

        for arr in gate_arrivals:
            dep = float(np.clip(self.rng.normal(600, 60), arr + 60, PARK_CLOSE))
            agent = self._create_agent(agent_id, float(arr), dep, attractions)
            self.agents.append(agent)
            agent_id += 1

        # Steady state: ~17000 over 690 min = 24.6/min from t=30 to park close
        for t_min in range(30, PARK_CLOSE):
            n_arrivals = self.rng.poisson(17000 / 690)
            for _ in range(n_arrivals):
                arr = float(t_min) + self.rng.uniform(0, 1)
                dep = float(np.clip(self.rng.normal(600, 60), arr + 60, PARK_CLOSE))
                agent = self._create_agent(agent_id, arr, dep, attractions)
                self.agents.append(agent)
                agent_id += 1

        # For timed passes, assign slots after all agents are created
        if self.pass_strategy == "preselect_timed":
            slot_counters = {n.name: 0 for n in self.park.get_attractions()}
            for agent in self.agents:
                agent.assign_timed_passes(self.park, slot_counters)

        print(f"Generated {len(self.agents)} agents "
              f"(3000 gate rush + {len(self.agents) - 3000} steady state)")

    def _create_agent(self, agent_id: int, arrival: float, departure: float,
                      attractions: list) -> Agent:
        """Create a single agent with random preferences."""
        agent = Agent(
            agent_id=agent_id,
            arrival_time=arrival,
            departure_time=departure,
        )
        # Multiplicative preference: pref ~ N(1.0, 0.3), floored at 0.1
        for attr in attractions:
            agent.preferences[attr.name] = max(0.1, self.rng.normal(1.0, 0.3))

        # Assign pass strategy
        agent.pass_strategy = self.pass_strategy
        if self.pass_strategy == "preselect":
            agent.assign_preselected_passes(self.park)
        elif self.pass_strategy == "dynamic":
            agent.dynamic_passes = 3
        # preselect_timed is assigned after all agents are created (needs shared counters)

        return agent

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
            if len(node.queue) == 0 and len(node.priority_queue) == 0:
                node.cycle_timer = 0.0
                continue
            node.cycle_timer += self.dt
            if node.cycle_timer >= node.service_rate:
                finished = node.process_cycle()
                node.cycle_timer -= node.service_rate  # carry-over for accuracy
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
                if agent.state == "queued" and agent.target_node:
                    node = self.park.nodes.get(agent.target_node)
                    if node:
                        node.remove_from_queue(agent)
                agent.state = "departed"

        # Phase 4: Decisions — sequential best-response (anti-herding)
        # Shuffle deciding agents; each sees updated queue state from prior decisions
        deciding = [a for a in self.agents if a.state == "deciding"]
        self.rng.shuffle(deciding)

        for agent in deciding:
            best = agent.choose_next_attraction(self.park, t)
            if best is not None:
                travel = self.park.travel_time(agent.current_node, best)
                agent.target_node = best
                agent.time_remaining = travel
                agent.state = "traveling"

                # Determine if agent will use a pass on arrival
                target_node = self.park.nodes[best]
                W = target_node.current_wait_time
                if agent.pass_strategy == "preselect" and best in agent.preselect_passes:
                    agent.using_pass = True
                elif agent.pass_strategy == "preselect_timed" and agent.has_active_timed_pass(best, t):
                    agent.using_pass = True
                elif agent.would_use_dynamic_pass(W):
                    agent.using_pass = True
                else:
                    agent.using_pass = False

                # Signal commitment so next agent sees updated wait estimate
                # Pass users don't add to regular queue pressure
                if not agent.using_pass:
                    target_node.pending_arrivals += 1
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
                    if agent.using_pass:
                        # Skip the line — go to priority queue
                        agent.consume_pass(agent.target_node, t)
                        target_node.add_to_priority_queue(agent)
                        agent.using_pass = False
                    else:
                        target_node.add_to_queue(agent)
                        target_node.pending_arrivals = max(0, target_node.pending_arrivals - 1)
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

    def run_summary_only(self) -> dict:
        """Return summary stats without running (call after manual stepping)."""
        return self.summary()

    def run(self) -> dict:
        """Run the full simulation from park open to close."""
        print(f"Running simulation: {len(self.agents)} agents, "
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

        # Per-ride average wait times
        ride_total_wait = {}
        ride_wait_counts = {}
        for snapshot in self.history:
            for ride, ql in snapshot["queue_lengths"].items():
                ride_total_wait[ride] = ride_total_wait.get(ride, 0) + ql
                ride_wait_counts[ride] = ride_wait_counts.get(ride, 0) + 1

        avg_queue_by_ride = {}
        for ride in ride_total_wait:
            avg_queue_by_ride[ride] = ride_total_wait[ride] / ride_wait_counts[ride]

        total_passes_used = sum(a.passes_used for a in self.agents)

        results = {
            "num_agents": len(active_agents),
            "total_park_happiness": np.sum(happinesses),
            "avg_happiness": np.mean(happinesses),
            "median_happiness": np.median(happinesses),
            "std_happiness": np.std(happinesses),
            "avg_wait": np.mean(waits),
            "avg_travel": np.mean(travels),
            "avg_rides": np.mean(rides),
            "total_rides": int(np.sum(rides)),
            "total_passes_used": total_passes_used,
            "most_congested": most_congested,
            "peak_queue": peak_queues.get(most_congested, 0),
            "avg_queue_by_ride": avg_queue_by_ride,
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
    print(f"  Capacity per cycle: {{n.name: n.capacity for n in park.get_attractions()}}")

    sim = Simulation(park, dt=1.0, seed=42)
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

    print("\n=== AVG QUEUE BY RIDE ===")
    for ride, avg_q in sorted(results['avg_queue_by_ride'].items(),
                               key=lambda x: -x[1]):
        print(f"  {ride:<50} {avg_q:.0f}")

    sim.plot_results()
