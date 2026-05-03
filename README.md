# Epic Universe Theme Park Congestion Simulation

ORF387 (Networks) class project modeling Universal Studios Epic Universe as a stochastic network congestion game. Up to ~20,000 utility-maximizing agents per simulated day navigate a directed weighted graph of rides and themed lands, producing emergent congestion dynamics. The simulation supports six pass strategies, five composable agent behaviors, and an interactive Flask-backed visualization where the user can select a configuration and run a fresh simulation on demand.

## Research Question

How do congestion, stochastic arrivals, agent rationality, and virtual-queue interventions jointly influence equilibrium behavior and systemic efficiency in networked theme park queueing environments? Specifically: (a) which pass strategies most increase aggregate visitor utility, (b) how does the strategy ranking shift when agents are imperfect, and (c) how do efficiency and equity tradeoffs vary as pass adoption scales from 0% to 100%?

## How We Built the Network

### 1. Defining the Graph Structure

The park is modeled as a **directed weighted graph** with a **hub-and-spoke topology**, matching Epic Universe's real layout.

**Nodes (16 total):**
- **5 Hub nodes** — one per themed land (Celestial Park, Super Nintendo World, Dark Universe, Wizarding World, Isle of Berk)
- **11 Ride nodes** — the queue-based attractions with published wait/capacity data

**Edges (30 total):**
- **Hub-to-Hub (8 edges):** Bidirectional walking times between Celestial Park and each land. All inter-land travel routes through Celestial Park, matching the real park's portal system. Distances were measured from Google Earth satellite imagery and converted to walking time at 3 mph.
- **Hub-to-Ride (11 edges):** 1 minute walking time from a land hub to each of its rides.
- **Ride-to-Hub (11 edges):** 1 minute walking time from a ride back to its land hub.

### 2. Collecting Real Data

All ride data was manually verified from primary sources:

| Data Point | Source | Method |
|---|---|---|
| Average wait times | thrill-data.com (lifetime stats) | Manually checked each ride's summary page |
| Hourly capacity | thrill-data.com, touringplans.com | Cross-referenced multiple sources |
| Ride duration | orlandoinformer.com, undercovertourist.com, frommers.com, attractionsmagazine.com | Web research |
| Hub-to-hub distances | Google Earth | Straight-line measurements between land centers |
| Park attendance | thrill-data.com, disneytouristblog.com | ~16,000–20,000 daily |

### 3. Computing Enjoyment Scores

Raw wait times don't capture popularity because high-capacity rides process more people with shorter waits. We use **Little's Law** to estimate latent demand:

```
avg_queue_size = avg_wait_min * hourly_capacity / 60
```

Then apply a **log-normalized 1–10 scale** across all rides:

```
score = 1 + 9 * (ln(queue) - ln(min_queue)) / (ln(max_queue) - ln(min_queue))
```

This produces enjoyment scores where Stardust Racers (38 min wait, 2,700/hr capacity) scores 8.1 — higher than Mine-Cart Madness (116 min wait, 750/hr capacity) at 7.7 — because vastly more people are actually riding it.

### 4. Converting Capacity for Simulation

Hourly capacity converts to per-cycle capacity for discrete dispatch:

```
capacity_per_cycle = round(hourly_capacity * ride_time_min / 60)
```

## Agent Model

### Utility Function

```
U(a) = H(a) * pref * decay * reride_penalty / sqrt(1 + W(a) + D(a))
```

| Term | Meaning |
|---|---|
| `H(a)` | Ride's enjoyment score (1.0–10.0) |
| `pref` | Per-agent preference multiplier ~ N(1.0, 0.3), floored at 0.1 |
| `decay` | Linear decay from 1.0 at arrival to 0.0 at planned departure |
| `reride_penalty` | 1/(1 + 0.5n) where n = times already ridden this ride |
| `W(a)` | Wait the agent would actually face — priority queue if they have a pass for `a`, regular queue otherwise (see *Wait Time Model* below) |
| `D(a)` | Travel time from current position (Dijkstra shortest path) |

The `sqrt(1 + W + D)` denominator ensures utility is always non-negative while penalizing longer waits. Agents pick the ride with the highest utility at each decision point, subject to a feasibility check that they can complete the ride before their departure time.

### Wait Time Model

Each ride node maintains two queues — a regular FIFO queue and a separate priority queue for pass holders. Each ride cycle drains the priority queue first up to capacity, with any remaining capacity drawn from the regular queue. Two wait estimates are computed per ride:

```
wait_priority = |priority_queue| / capacity * service_rate
wait_regular  = (|priority_queue| + |regular_queue| + pending_arrivals) / capacity * service_rate
```

Pass holders use `wait_priority` in their utility computation; non-holders use `wait_regular`. The regular-queue formula correctly accounts for the entire priority queue blocking ahead of regular queueers.

### Agent Behaviors (composable)

Each agent carries a `behaviors: set[str]` — any subset of the five flags below. An empty set is the rational baseline; multiple flags layer independently on a single agent.

| Behavior | Effect |
|---|---|
| `fatigue` | Switching away from `last_target` requires a ≥5% utility improvement (anti-flip-flop). |
| `info_restricted` | Agent uses a 15-minute-stale shared wait-time board instead of live queue lengths. Models informational cascades. |
| `proximity_bias` | Utility multiplied by `0.95^(D/0.5)`, so every extra 30s of travel costs 5%. |
| `decision_paralysis` | Each agent draws `decision_speed ∈ {0, 1, 2, 4}` min uniformly. On near-tie decisions (≥2 rides within 5% of best), they stall before committing. |
| `eating_resting` | Hunger-driven meal breaks. Each agent draws a hunger threshold from `clip(N(225, 15), 180, 270)` min. On threshold cross, they walk to their land's hub and rest for `clip(N(30, 5), 25, 35)` min. |

### Arrival Model

- **Gate rush:** 3,000 agents staggered over the first 30 minutes (exponential inter-arrival, scale=5 min)
- **Steady state:** ~17,000 agents arriving via Poisson process at ~24.6/min from t=30 to park close
- **Total:** ~20,000 agents per day
- **Departure:** Each agent's planned departure time ~ N(600 min, 60 min), clipped to [arrival+60, park close]. Agents also depart early if no ride yields positive utility.

### Anti-Herding Mechanism

Within each timestep, deciding agents are shuffled and processed sequentially. Each agent's ride commitment increments a `pending_arrivals` counter on the target ride, so the next deciding agent sees an updated wait estimate. This is the **sequential best-response dynamic** from congestion-game theory; under it, the Rosenthal potential function is monotonically non-increasing.

## Pass Strategies

The simulation supports six virtual-queue strategies, all selectable from the visualization UI:

| Strategy | Description |
|---|---|
| `none` | Baseline — no passes (FCFS only) |
| `preselect` (free) | Every agent picks their top-3 rides by personal preference; passes are usable any time. Models Disney's pre-2021 free FastPass+. |
| `preselect_paid` | Same mechanic as free Preselect, but only an adopter fraction (settable in UI) receives the 3 passes. Models a hypothetical paid Disney-style anytime pass. |
| `preselect_timed` | Top-3 picks bound to assigned 5-minute time windows (round-robin across 144 windows per ride, ≥30 min apart per agent). Models Disney Lightning Lane Multi Pass. |
| `dynamic` | 3 on-demand passes per agent, burned when perceived wait > 30 min. |
| `express` | Universal Orlando Express Pass — pass holders skip the regular queue **once per ride** for every ride. The user specifies the adopter fraction in the UI ("Express Pass holders %"). |

**Modeling note:** Universal Orlando's real Express Pass excludes Dragon Racer's Rally (and a few headliners that change over time). For simplicity, this simulation lets Express Pass holders use the pass on every ride in the park, including Dragon Racer's Rally.

## Simulation Architecture

Discrete-time simulation with `dt = 1` minute, 720 timesteps per day (9 AM to 9 PM). Eight phases per timestep:

1. **Arrivals** — Activate agents whose arrival time has passed
2. **Ride processing** — Dispatch riders from priority then regular queues when each cycle completes (with timer carry-over for accuracy)
3. **Departures** — Remove agents past their departure time
4. **Decisions** — Sequential best-response: each deciding agent picks the highest-utility ride; hungry agents reroute to a land hub for a meal
5. **Travel** — Agents move along edges; on arrival, route to priority or regular queue based on pass availability
6. **Rest tick** — Resting agents count down their meal timer
7. **Wait/hunger accumulation** — Queued agents accumulate wait time; active agents accumulate hunger
8. **Snapshot** — Record queue lengths and agent state counts

The engine uses per-state agent buckets (sets) and an all-pairs shortest-path cache so each phase iterates only the relevant agents and Dijkstra is O(1) at runtime. A full 20k-agent day runs in ~5–15 seconds (faster on baseline, slower with all behaviors enabled).

## Repository Structure

```
attraction_data.py            — Real park data: 25 attractions, walking edges, enjoyment scores
park_model.py                 — Graph data model: Node, Edge, Park (Dijkstra), Agent (utility)
simulation.py                 — Simulation engine: 8-phase discrete-time loop, agent generation, behaviors
server.py                     — Flask backend: serves visualization.html and runs sims on demand
visualization.html            — Interactive HTML/Canvas UI with utility histogram and arrival-window filter
export_viz.py                 — Legacy: writes static viz_data.json (superseded by server.py)

generate_report_data.py       — Sweeps all 5 strategies × 3 seeds, rational baseline
generate_report_data_behaviors.py — Same sweep with all behaviors enabled
express_sweep.py              — Express adoption sweep 0–100% (rational)
behaviors_express_sweep.py    — Same sweep with behaviors enabled
preselect_paid_sweep.py       — Paid Preselect adoption sweep 0–100% (rational)
behaviors_preselect_paid_sweep.py — Same sweep with behaviors enabled

assumptions.md                — All modeling assumptions documented
final_report_draft.tex        — Final report (LaTeX)
progress_report.tex           — Progress report (LaTeX, earned 100%)
figures/                      — All PNG figures referenced from the report
*.csv                         — Per-run summary statistics from each sweep
```

## Running the Simulation

### Interactive UI (recommended)

```bash
python server.py
# then open http://localhost:5000/
```

In the browser:
1. Pick a **Virtual Queue Strategy** from the dropdown.
2. If Express or Paid Preselect is selected, set the **adopter %** in the input that appears.
3. Check any combination of **People Actions** (the 5 agent behaviors).
4. Choose **Reproducible seed** (typed) or **Random seed** in the Randomness section.
5. Click **Run Simulation**. A full day runs in ~5–15 seconds depending on configuration.

The page shows a live network visualization (animated agent flows, queue sizes), per-strategy summary stats, and a utility distribution histogram at the bottom with an arrival-time filter and pass-holder/non-holder color split where applicable.

### Batch sweeps for the report

```bash
python generate_report_data.py            # 5 strategies × 3 seeds, rational
python generate_report_data_behaviors.py  # same, all behaviors enabled
python express_sweep.py                   # Express 0–100% adoption (rational)
python behaviors_express_sweep.py         # Express 0–100% (all behaviors)
python preselect_paid_sweep.py            # Paid Preselect 0–100% (rational)
python behaviors_preselect_paid_sweep.py  # Paid Preselect 0–100% (all behaviors)
```

Each script writes a CSV of per-run summary statistics and emits PNG figures into the `figures/` directory.

### Standalone single run

```bash
python simulation.py
```

Runs one default-config simulation and prints summary statistics + per-ride averages.

## Headline Results

3-seed Monte Carlo strategy comparison (per-agent average happiness, mean ± std):

| Strategy | Rational avgH | Behaviors avgH | Robustness Δ |
|---|---|---|---|
| Baseline (No Passes) | 38.03 ± 0.21 | 39.27 ± 0.20 | +1.24 |
| Preselect (Anytime, free) | **47.09 ± 0.22** | **45.02 ± 0.28** | −2.07 |
| Preselect (Timed Slots) | 38.54 ± 0.20 | 39.20 ± 0.21 | +0.66 |
| Dynamic (On-Demand) | 46.22 ± 0.27 | 39.87 ± 0.44 | **−6.35** |
| Express Pass (30%) | 41.64 ± 0.24 | 41.23 ± 0.13 | **−0.41** |

**Three findings:**
- **Preselect dominates Express on both efficiency and equity** at every adoption level. Targeted top-3 access concentrates pass benefit where marginal value is highest.
- **Strategy ranking re-orders under bounded rationality.** Dynamic falls from #2 to #3 (its threshold rule depends on accurate wait perception that `info_restricted` agents lack); Express climbs from #3 to #2 (its "always use" rule is judgment-free).
- **Universal's ~30% Express adoption** (set by pricing pressure) approximately matches the welfare-maximizing rate under realistic agent behavior — Pigovian-style optimization without explicit Pigovian taxation.

See `final_report_draft.tex` for the full write-up with figures.

## Data Sources

- [thrill-data.com](https://www.thrill-data.com/waits/park/uor/epic-universe/) — Wait times and capacity stats
- [queue-times.com](https://queue-times.com/en-US/parks/334/stats) — Park-wide statistics
- [orlandoinformer.com](https://orlandoinformer.com/universal/epic-universe/) — Ride durations and park layout
- [undercovertourist.com](https://www.undercovertourist.com/blog/) — Ride specs and layout guides
- [touringplans.com](https://touringplans.com/) — Capacity analysis
- [Google Earth](https://earth.google.com/) — Hub-to-hub distance measurements
