# Epic Universe Theme Park Congestion Simulation

## Project Overview
ORF387 (Networks) class project modeling Universal Studios Epic Universe as a network congestion game. Agents (park visitors) make utility-maximizing decisions about which attractions to visit, creating emergent congestion dynamics.

**Central question:** How do congestion, stochastic arrivals, and information lag jointly influence attraction-utility-seeking equilibrium behavior and systemic efficiency in networked theme park queueing environments?

## Repository Structure

- `attraction_data.py` — All park data: attraction stats, walking edges, and graph structure
- `park_model.py` — Data model classes: Node, Edge, Park (directed weighted graph), Agent (utility-maximizing visitor)
- `simulation.py` — Discrete-time simulation engine with arrival/departure, queueing, and decision-making phases
- `hello.py` — Test file

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
- **Hub → Attraction:** Edge weight = `avg_wait_min` (cost of going to ride)
- **Attraction → Hub:** Edge weight = 1 min (walking back after riding)

### Data Sources
- **Wait times & capacity:** Manually verified from thrill-data.com summary stats (March 2026)
- **Ride durations:** orlandoinformer.com, undercovertourist.com, frommers.com, attractionsmagazine.com
- **Hub-to-hub distances:** Measured by user from Google Earth satellite view
- **Park layout research:** Wikipedia, orlandoinformer.com, undercovertourist.com, touringplans.com

## Simulation Model (`park_model.py` + `simulation.py`)

### Agent Utility Function
```
U(a) = H(a) * preference * decay - W(a) - D(current, a) - paralysis_cost
```
- `H(a)` = intrinsic happiness of attraction
- `W(a)` = current wait time (queue-based)
- `D(current, a)` = travel time from current position (Dijkstra shortest path)
- `decay` = linear decay from 1.0 at arrival to 0.0 at departure
- `paralysis_cost` = penalty for switching targets mid-decision
- Diminishing returns: 0.3^n multiplier for n-th re-ride

### Simulation Phases (per timestep)
1. Arrivals — activate agents (normal distribution, peak ~11am)
2. Ride processing — dispatch riders on completed cycles
3. Departures — agents leave at their departure time (~7pm)
4. Decisions — agents choose highest-utility attraction
5. Travel — agents move between nodes
6. Wait tracking — accumulate wait time for queued agents
7. Snapshot recording

### Project Goals
1. Simulate baseline park behavior with normal queues
2. Test virtual queue strategies and other interventions
3. Assess whether virtual queues improve average visitor utility
4. Derive optimal organizational strategy for park operators

## Important Notes
- `park_model.py` currently has placeholder attraction names/values from initial scaffolding — needs to be updated to use `attraction_data.py`
- Non-ride attractions (meet & greets, shows, experiences) have `avg_wait_min: 0` and `type: "non_ride"`
- Fyre Drill is missing `hourly_capacity` (data not found)
- Mine-Cart Madness `ride_time_min: 2` is a default estimate (not found online)
