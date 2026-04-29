# Epic Universe Theme Park Congestion Simulation

ORF387 Networks class project modeling Universal Studios Epic Universe as a network congestion game. Utility-maximizing agents navigate a directed graph of rides and themed lands, creating emergent congestion dynamics.

## Research Question

How do congestion, stochastic arrivals, and rational decision-making jointly influence equilibrium behavior and systemic efficiency in networked theme park queueing environments?

## How We Built the Network

### 1. Defining the Graph Structure

The park is modeled as a **directed weighted graph** with a **hub-and-spoke topology**, matching Epic Universe's real layout.

**Nodes (16 total):**
- **5 Hub nodes** — one per themed land (Celestial Park, Super Nintendo World, Dark Universe, Wizarding World, Isle of Berk)
- **11 Ride nodes** — the queue-based attractions with published wait/capacity data

**Edges (30 total):**
- **Hub-to-Hub (8 edges):** Bidirectional walking times between Celestial Park and each land. All inter-land travel must route through Celestial Park, matching the real park's portal system. Distances were measured from Google Earth satellite imagery and converted to walking time at 3 mph.
- **Hub-to-Ride (11 edges):** 1 minute walking time from a land hub to each of its rides.
- **Ride-to-Hub (11 edges):** 1 minute walking time from a ride back to its land hub.

### 2. Collecting Real Data

All ride data was manually verified from primary sources:

| Data Point | Source | Method |
|---|---|---|
| Average wait times | thrill-data.com (lifetime stats) | Manually checked each ride's summary page |
| Hourly capacity | thrill-data.com, touringplans.com | Cross-referenced multiple sources |
| Ride duration | orlandoinformer.com, undercovertourist.com, frommers.com, attractionsmagazine.com | Web research |
| Hub-to-hub distances | Google Earth | User measured straight-line distance between land centers |
| Park attendance | thrill-data.com, disneytouristblog.com | ~16,000-20,000 avg daily |

### 3. Computing Enjoyment Scores

Raw wait times don't capture popularity because high-capacity rides process more people with shorter waits. We used **Little's Law** to estimate demand:

```
avg_queue_size = avg_wait_min * hourly_capacity / 60
```

Then applied a **log-normalized scale (1-10)** across all rides:

```
score = 1 + 9 * (ln(queue) - ln(min_queue)) / (ln(max_queue) - ln(min_queue))
```

This produces enjoyment scores where Stardust Racers (38 min wait, 2700/hr capacity) scores 8.1 — higher than Mine-Cart Madness (116 min wait, 750/hr capacity) at 7.7 — because vastly more people are actually riding it.

### 4. Converting Capacity for Simulation

The data provides `hourly_capacity` (riders per hour). The simulation needs `capacity_per_cycle` (riders per dispatch). Conversion:

```
capacity_per_cycle = round(hourly_capacity * ride_time_min / 60)
```

## Agent Model

Each agent (park visitor) is a rational utility maximizer.

### Utility Function

```
U(a) = H(a) * pref * decay * reride_penalty / sqrt(1 + W(a) + D(a))
```

| Term | Meaning |
|---|---|
| `H(a)` | Ride's enjoyment score (1.0 - 10.0) |
| `pref` | Per-agent preference multiplier ~ N(1.0, 0.3), floored at 0.1 |
| `decay` | Linear decay from 1.0 at arrival to 0.0 at planned departure |
| `reride_penalty` | 1/(1 + 0.5n) where n = times already ridden this ride |
| `W(a)` | Dynamic wait time (queue length / capacity * cycle time) |
| `D(a)` | Travel time from current position (Dijkstra shortest path) |

The `sqrt(1 + W + D)` denominator ensures utility is **always non-negative** while penalizing longer waits. Agents choose the ride with the highest utility at each decision point.

### Arrival Model

- **Gate rush:** 3,000 agents staggered over the first 30 minutes (exponential inter-arrival, scale=5 min)
- **Steady state:** ~17,000 agents arriving at a constant rate (~24.6/min via Poisson process) from t=30 to park close
- **Total:** ~20,000 agents per day
- **Departure:** Each agent's departure time ~ N(600 min, 60 min), clipped to [arrival+60, park close]. Agents also depart early if no ride has positive utility.

### Anti-Herding Mechanism

Within each timestep, deciding agents are **shuffled and processed sequentially**. Each agent's ride commitment increments a `pending_arrivals` counter, so the next agent sees an updated wait estimate. This is a **sequential best-response dynamic** — a core concept in congestion game theory.

## Simulation Architecture

Discrete-time simulation with dt=1 minute, 720 timesteps (9 AM to 9 PM).

**7 phases per timestep:**
1. **Arrivals** — Activate agents whose arrival time has passed
2. **Ride processing** — Dispatch riders from queues when cycle completes (with timer carry-over for accuracy)
3. **Departures** — Remove agents past their departure time
4. **Decisions** — Sequential utility-maximizing ride selection
5. **Travel** — Agents move along edges, decrementing travel time
6. **Wait tracking** — Queued agents accumulate wait time
7. **Snapshot** — Record queue lengths and agent states for analysis

## Repository Structure

```
attraction_data.py   — Real park data: 25 attractions, walking edges, enjoyment scores
park_model.py        — Graph data model: Node, Edge, Park (Dijkstra), Agent (utility)
simulation.py        — Simulation engine: 7-phase discrete-time loop, agent generation
export_viz.py        — Exports simulation snapshots to JSON for visualization
visualization.html   — Interactive HTML/Canvas visualization with time scrubber
assumptions.md       — All modeling assumptions documented
```

## Running the Simulation

```bash
# Run simulation with text output
python simulation.py

# Export data and launch interactive visualization
python export_viz.py
python -m http.server 8000
# Open http://localhost:8000/visualization.html
```

## Pass Strategies

The simulation supports five virtual-queue strategies, selectable from the visualization UI:

| Strategy | Description |
|---|---|
| `none` | Baseline — no passes |
| `preselect` | Each agent picks their top-3 rides by personal preference; passes are usable any time |
| `preselect_timed` | Same top-3 picks, but each is bound to an assigned 30-minute time window (round-robin slot assignment, ≥30 min apart per agent) — Disney Lightning Lane Multi Pass model |
| `dynamic` | 3 on-demand passes per agent; used when wait > 30 min |
| `express` | Universal Orlando Express Pass model — pass holders skip the regular line **once per ride** for every ride in the park. The user specifies what fraction of guests hold the pass via the "Express Pass holders %" UI field. |

**Modeling note:** Universal Orlando's real Express Pass excludes Dragon Racer's Rally (and a few headliners that change over time). For simplicity, this simulation lets Express Pass holders use the pass on every ride in the park, including Dragon Racer's Rally.

## Sample Results (20,000 agents)

| Metric | Value |
|---|---|
| Peak in-park population | ~13,800 (5 PM) |
| Avg rides per agent | 8.0 |
| Avg wait per ride | 32 min |
| Most congested ride | Harry Potter (peak queue: 2,761) |
| Runtime | ~60 seconds |

## Data Sources

- [thrill-data.com](https://www.thrill-data.com/waits/park/uor/epic-universe/) — Wait times and capacity stats
- [queue-times.com](https://queue-times.com/en-US/parks/334/stats) — Park-wide statistics
- [orlandoinformer.com](https://orlandoinformer.com/universal/epic-universe/) — Ride durations and park layout
- [undercovertourist.com](https://www.undercovertourist.com/blog/) — Ride specs and layout guides
- [touringplans.com](https://touringplans.com/) — Capacity analysis
- [Google Earth](https://earth.google.com/) — Hub-to-hub distance measurements
