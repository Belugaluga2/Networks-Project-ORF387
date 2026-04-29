# Epic Universe Theme Park Congestion Simulation

## Project Overview
ORF387 (Networks) class project modeling Universal Studios Epic Universe as a network congestion game. Agents (park visitors) make utility-maximizing decisions about which attractions to visit, creating emergent congestion dynamics.

**Central question:** How do congestion, stochastic arrivals, and information lag jointly influence attraction-utility-seeking equilibrium behavior and systemic efficiency in networked theme park queueing environments?

## Repository Structure

- `attraction_data.py` — All park data: attraction stats, walking edges, and graph structure
- `park_model.py` — Data model classes: Node, Edge, Park (directed weighted graph), Agent (utility-maximizing visitor)
- `simulation.py` — Discrete-time simulation engine with arrival/departure, queueing, and decision-making phases
- `compare_strategies.py` — Driver to run multiple pass strategies and compare summary stats
- `server.py` — Flask backend serving `visualization.html` and exposing `/api/park` + `/api/simulate` (the primary workflow)
- `export_viz.py` — (Legacy pre-compute path) runs every (pass strategy × behavior) combo and writes `viz_data.json`
- `visualization.html` — Browser UI that talks to the backend; checkboxes for behaviors + Run Simulation button
- `assumptions.md`, `README.md`, `progress_report_draft.md`, `progress_report.tex` — Write-ups

## Data Model (`attraction_data.py`)

### Attractions (25 total)
Each attraction has:
- `land` — Which themed area it belongs to (5 lands)
- `type` — `"ride"` or `"non_ride"` (meet & greets, shows, experiences)
- `avg_wait_min` — Lifetime average wait time from thrill-data.com (rides only; 0 for non-rides)
- `hourly_capacity` — Riders per hour (None if unknown)
- `ride_time_min` — Duration of the ride experience

### Graph Structure (Hub-and-Spoke)
The park uses a hub-and-spoke topology matching the real Epic Universe layout. All travel between lands goes through Celestial Park (the central hub).

**5 Hub nodes:** Celestial Park, Super Nintendo World, Dark Universe, Wizarding World, Isle of Berk

**Directed edges:**
- **Hub → Hub:** Bidirectional walking times (measured from Google Earth at 3 mph)
  - Celestial Park ↔ Isle of Berk: 1.7 min (140m)
  - Celestial Park ↔ Super Nintendo World: 1.8 min (146m)
  - Celestial Park ↔ Wizarding World: 4.1 min (330m)
  - Celestial Park ↔ Dark Universe: 4.3 min (350m)
- **Hub → Attraction:** 1 min walking time (entering ride area)
- **Attraction → Hub:** 1 min walking time (walking back after riding)
- Wait time is *not* baked into edge weights — it lives on the attraction node and is recomputed each step from queue length + pending arrivals.

### Data Sources
- **Wait times & capacity:** Manually verified from thrill-data.com summary stats (March 2026)
- **Ride durations:** orlandoinformer.com, undercovertourist.com, frommers.com, attractionsmagazine.com
- **Hub-to-hub distances:** Measured by user from Google Earth satellite view
- **Park layout research:** Wikipedia, orlandoinformer.com, undercovertourist.com, touringplans.com

## Simulation Model (`park_model.py` + `simulation.py`)

### Park day
- 12-hour day: `PARK_OPEN = 0` (9 AM) to `PARK_CLOSE = 720` (9 PM)
- Default `dt = 1.0` minute timestep

### Agent Utility Function
```
U(a) = H(a) * pref * decay * reride_penalty / sqrt(1 + W + D)
```
- `H(a)` = attraction happiness × per-agent preference × time-of-day decay
- `W(a)` = current wait time (set to 0 if agent will skip the line via a pass)
- `D(current, a)` = travel time from current position (Dijkstra shortest path)
- `decay` = linear decay from 1.0 at arrival to 0.0 at departure (time-left / total-stay)
- `reride_penalty = 1 / (1 + 0.5 * times_already_ridden)` — diminishing returns
- Returns `-inf` if `D + W + service_rate > time_left` (can't finish before close/departure)
- Utility is always non-negative; agents only commit if `U > 0`

### Agent Behaviors (composable)
Each agent carries `behaviors: set[str]` — any subset of the five flags below. An empty set is the rational baseline. Multiple flags layer independently on a single agent. The `Simulation` constructor takes `behaviors: list[str]` and copies it onto every generated agent.
- `fatigue` — requires ≥5% utility improvement to switch away from `last_target` (anti-flip-flop)
- `info_restricted` — uses a shared wait-time board snapshot (refreshed every 15 min) instead of live queue lengths
- `proximity_bias` — utility multiplied by `0.95^(D/0.5)` so every extra 30s of travel costs ~5%
- `decision_paralysis` — when ≥2 attractions are within 5% of the chosen utility (a "near-tie"), slow agents stall before committing. Each agent draws `decision_speed` ∈ {0, 1, 2, 4} min uniformly (¼ each). They lock in `paralysis_target` and remain in `deciding` for `decision_speed` minutes; `decision_speed = 0` agents are unaffected. Stall time accumulates in `total_paralysis_time`. During paralysis no `pending_arrivals` signal is emitted (delayed herding signal).
- `eating_resting` — hunger-driven meal breaks. Each agent draws `hunger_threshold` from `clip(N(225, 15), 180, 270)` min. `time_since_last_meal` ticks up while active and not resting; once it crosses the threshold (and ≥32 min remain before departure) the agent reroutes to its land hub via `hub_for_attraction`, walks there as a normal `traveling` state with `target_rest_hub` set, then transitions to `resting` for `clip(N(30, 5), 25, 35)` min. After the rest, `time_since_last_meal` resets to 0 and `meals_taken` increments. Resting agents stay at the hub, accumulate no wait/travel, and don't add to `pending_arrivals` during the meal-walk. Phase 5b decrements `rest_remaining`; Phase 6 accumulates hunger.

### Skip-the-Line Pass Strategies
Set on the `Simulation` via `pass_strategy`. Pass holders go to `priority_queue` and are dispatched before the regular queue each ride cycle.
- `none` — baseline, no passes
- `preselect` — each agent picks top 3 rides by personal preference, anytime use
- `preselect_timed` — same top-3 picks but assigned 30-min time windows via round-robin slot counters; min 30 min between an agent's passes
- `dynamic` — 3 on-demand passes per agent, used when wait > `dynamic_pass_threshold` (default 30 min)
- `express` — Universal Orlando model: a fraction of agents (`Simulation.express_pct`, default 0.3, range [0, 1]) get an Express Pass that lets them skip the regular queue **once per ride** for every ride in the park. Tracked via `Agent.has_express_pass` (boolean) and `Agent.express_passes_used` (set of ride names already burned). The `express_pct` value is exposed in the UI as a number-input field that only appears when the Express strategy is selected. The 30% default mirrors observed real-world participation ranges; cache key includes `express_pct` so different fractions are independent cache entries. **Simplification:** the simulation lets pass holders use Express on every attraction, including Dragon Racer's Rally, which the real Universal Orlando product excludes.

### Queue / Capacity Model
- Each attraction has `capacity` (riders per cycle) = `hourly_capacity * ride_time_min / 60`
- `service_rate` = `ride_time_min`; `cycle_timer` accumulates and dispatches when ≥ service_rate
- `current_wait_time = (len(queue) + pending_arrivals) / capacity * service_rate`
- `pending_arrivals` increments when an agent commits to traveling there (so the next decider sees congestion forming) and decrements on arrival

### Arrival Model
- 3000-agent gate rush staggered exponentially over the first 30 min
- Steady state: Poisson arrivals at ~17000/690 min (~24.6/min) until close → ~20k total agents/day
- Departure: `~N(600, 60)` minutes after open, clipped to `[arrival+60, PARK_CLOSE]`
- Per-agent preferences: multiplicative `~N(1.0, 0.3)`, floored at 0.1

### Simulation Phases (per timestep)
1. Arrivals — activate agents at Celestial Park entrance
2. Ride processing — advance `cycle_timer`, dispatch (priority queue first, then regular)
3. Departures — agents leaving at `departure_time`
4. Decisions — shuffle deciding agents (anti-herding); hungry agents (eating_resting) reroute to hub for a meal; otherwise each runs Dijkstra and picks best attraction; sets `using_pass` and bumps `pending_arrivals`. Shared wait board refreshes every 15 min.
5. Travel — decrement `time_remaining`; on arrival, transition to `resting` if `target_rest_hub` matches, else route to priority queue (if pass) or regular queue
5b. Rest — decrement `rest_remaining` for resting agents; on completion, reset `time_since_last_meal` and transition back to `deciding`
6. Wait tracking — accumulate `total_wait_time` for queued agents and `time_since_last_meal` for active non-resting agents
7. Snapshot recording

### Project Goals
1. Simulate baseline park behavior with normal queues
2. Test virtual queue strategies and other interventions
3. Assess whether virtual queues improve average visitor utility
4. Derive optimal organizational strategy for park operators

## Visualization Pipeline (on-demand backend)
Primary workflow:
- `python server.py` (Flask, port 5000) serves the page and runs simulations on demand
- Open `http://localhost:5000/`
- Pick a pass strategy (dropdown) + check any combination of behaviors → click **Run Simulation** (~10–15 s)
- Results are cached in browser memory; re-selecting a previously-run combo loads instantly
- The first sim run is treated as the "vs Baseline" reference for the % comparison

API:
- `GET /api/park` — static park layout (nodes, edges) + label maps for the dropdown/checkboxes
- `POST /api/simulate` body `{pass_strategy, behaviors: [...], seed?}` — runs one full-day sim and returns `{label, snapshots, summary, pass_strategy, behaviors}`

Snapshots include `queue_lengths`, `node_counts` (queued/deciding/riding per node), and `traveling_edges`.

Legacy pre-compute path: `python export_viz.py` still works and writes `viz_data.json` for offline analysis, but the visualization no longer reads it.

## Important Notes
- Non-ride attractions (meet & greets, shows, experiences) have `avg_wait_min: 0` and `type: "non_ride"` and are *skipped* by `build_epic_universe()` — only ride nodes are added to the graph
- Fyre Drill is missing `hourly_capacity` (data not found)
- Mine-Cart Madness `ride_time_min: 2` is a default estimate (not found online)
