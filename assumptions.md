# Assumptions

All modeling assumptions made during the development of this simulation, documented with reasoning.

## Data Assumptions

### Battle at the Ministry — Wait Time Adjusted Down
- **Real-world avg wait:** 135 minutes (from thrill-data.com lifetime stats)
- **Used in simulation:** 90 minutes
- **Reason:** The ride's theoretical capacity is 2,184 riders/hour, but it actually operates at ~1,450 riders/hour due to frequent downtime and mechanical issues. The 135-minute wait was measured under this reduced throughput. Since we model the park under **optimal operating conditions** (all rides running at theoretical capacity), we scaled the wait proportionally: `135 * (1450 / 2184) = 90 min`. This avoids inflating Battle at the Ministry's demand relative to other rides that don't have the same operational issues.

### Mine-Cart Madness — Ride Duration Estimated
- **Used in simulation:** 2 minutes
- **Reason:** No published ride duration could be found online. A 2-minute default was used as a reasonable estimate for a coaster-style ride.

### Fyre Drill — Capacity User-Provided
- **Used in simulation:** 600 riders/hour
- **Reason:** The hourly capacity was not available from any published source. User provided 600/hr based on their own research.

### Non-Ride Attractions Excluded from Graph
- **Excluded:** 14 attractions including all meet & greets (Mario, Peach, Toad, DK, Dark Universe characters, Toothless), shows (Le Cirque Arcanus, The Untrainable Dragon), experiences (Darkmoor Monster Makeup, Cosme Acajor Baguettes Magique), and open play areas (Astronomica, Vikings Training Camp).
- **Reason:** These attractions lack reliable published wait time and capacity data. Including them would require inventing data, undermining the project's claim of using real-world measurements. They are stored in `attraction_data.py` with `type: "non_ride"` for completeness but are not added to the simulation graph.

### Ride Durations from Multiple Sources
- Ride durations were sourced from orlandoinformer.com, undercovertourist.com, frommers.com, and attractionsmagazine.com. Where sources disagreed, the most commonly cited value was used. These are approximate and may differ from actual ride experience by 15-30 seconds.

## Graph Topology Assumptions

### Hub-and-Spoke — No Direct Land-to-Land Travel
- **Assumption:** All travel between themed lands must route through Celestial Park.
- **Reason:** This matches the real park layout. Epic Universe uses a portal system where each themed land is only accessible from Celestial Park. There are no shortcuts between lands.

### Attractions Located at Hub Center
- **Assumption:** All attractions within a land are co-located at the land's center point. The walking time from a hub to any of its rides is 1 minute.
- **Reason:** Exact intra-land walking distances are not published. Satellite imagery and park walkthroughs suggest most lands can be traversed in 2-4 minutes, so 1 minute from hub center to any ride is a reasonable simplification. The real variation (e.g., Mine-Cart Madness is deeper in Super Nintendo World than Mario Kart) is not captured.

### Hub-to-Hub Distances from Google Earth
- **Assumption:** Distances between land centers were measured as straight-line distance from Google Earth satellite view, then converted at 3 mph walking speed.
- **Actual measurements:** Celestial Park to Isle of Berk: 140m (1.7 min), Celestial Park to Super Nintendo World: 146m (1.8 min), Celestial Park to Wizarding World: 330m (4.1 min), Celestial Park to Dark Universe: 350m (4.3 min).
- **Limitation:** Straight-line distance underestimates actual walking paths, which follow curved pathways and go through portal entrances. Real walking times may be 20-40% longer.

## Agent Behavior Assumptions

### Utility Function: sqrt Penalty
- **Formula:** `U(a) = H * pref * decay * reride / sqrt(1 + W + D)`
- **Assumption:** Agents perceive wait+travel cost through a square root penalty, meaning utility is always non-negative and diminishes with longer waits but never reaches zero.
- **Reason:** A subtractive model (`H - W - D`) caused agents to leave the park after 4-5 rides because happiness scores (1-10) couldn't compete with wait times (30-100 minutes). The sqrt model keeps agents in the park all day, matching real behavior. The tradeoff is that agents are somewhat insensitive to the difference between a 60-minute and 120-minute wait.

### Re-Ride Diminishing Returns: 1/(1 + 0.5n)
- **Assumption:** The n-th ride on the same attraction yields `1/(1 + 0.5n)` of the original enjoyment: 100%, 67%, 50%, 40%, 33%...
- **Reason:** A steeper decay (originally `0.3^n`: 30%, 9%, 3%...) caused agents to exhaust all rides too quickly and depart early. The gentler hyperbolic decay allows agents to re-ride favorites while still preferring variety.

### Multiplicative Preferences, Not Additive
- **Assumption:** Each agent's personal enjoyment of a ride = `enjoyment_score * pref` where `pref ~ N(1.0, 0.3)`, floored at 0.1. This gives 30% relative variation.
- **Original proposal:** Additive Gaussian with SD=3 on each enjoyment score. This was rejected because SD=3 on a 1-10 scale distorts low-scoring rides (Constellation Carousel at 1.0 would have 37% of agents floored to 0) while barely affecting high-scoring rides.

### Agents Are Fully Rational
- **Assumption:** Agents have perfect information about current queue lengths at all rides and always choose the ride that maximizes their utility.
- **Limitation:** Real visitors have incomplete information (they can't see queue lengths at rides in other lands), exhibit herd behavior, travel in groups with conflicting preferences, and make suboptimal decisions. This is why simulated wait times are lower than real-world averages — rational agents spread load more efficiently than real visitors.

### No Group Travel
- **Assumption:** Each agent is an individual making independent decisions.
- **Limitation:** Real park visitors travel in groups (families, friends) who must agree on a ride, slowing decisions and causing suboptimal choices for some group members.

## Arrival Model Assumptions

### Gate Rush: 3,000 Agents Staggered Over 30 Minutes
- **Assumption:** Gate arrivals follow an exponential distribution with mean 5 minutes, clipped to 30 minutes. Most arrive in the first 10 minutes but not all at t=0.
- **Reason:** Real theme parks take 15-30 minutes to process thousands of guests through turnstiles. Instantaneous arrival of 3,000 agents at t=0 would cause an unrealistic herding spike.

### Steady-State Arrival: ~24.6 Agents/Minute
- **Assumption:** After the gate rush, agents arrive at a constant Poisson rate of 17,000/690 per minute (~24.6/min, ~1,478/hour).
- **Reason:** Achieves ~20,000 total daily attendance, which is close to the real park average of ~16,000-22,000.

### Departure Times: Normal(600, 60)
- **Assumption:** Each agent plans to depart around 7:00 PM (minute 600 from 9 AM open) with standard deviation of 1 hour. Clipped to [arrival + 60 min, park close at 9 PM].
- **Reason:** Produces realistic stay durations: gate-rush agents stay ~10 hours, afternoon arrivals stay ~4 hours. Agents also depart early if no ride has positive utility.

## Simulation Mechanics Assumptions

### Timestep: 1 Minute
- **Assumption:** The simulation advances in 1-minute increments.
- **Reason:** Sub-minute resolution (e.g., per-second) would require 43,200 steps instead of 720, increasing runtime 60x with no meaningful improvement in fidelity. Arrival rates of ~25 agents/minute are well-resolved at this granularity.

### Sequential Decision Processing (Anti-Herding)
- **Assumption:** Within each timestep, deciding agents are shuffled randomly and processed one at a time. Each agent's ride commitment updates a `pending_arrivals` counter so the next agent sees a slightly higher wait estimate.
- **Reason:** Without this, all agents deciding at the same timestep see identical queue states and all choose the same "best" ride — a coordination failure. Sequential processing is a standard technique in congestion game simulation (sequential best-response dynamics).

### Cycle Timer Carry-Over
- **Assumption:** When a ride completes a dispatch cycle, leftover time carries over to the next cycle (`cycle_timer -= service_rate`) rather than resetting to zero.
- **Reason:** Without carry-over, rides with non-integer cycle times (e.g., 1.5 min for Stardust Racers) effectively round up to the next integer, causing 25% throughput loss. The carry-over preserves accurate throughput over time.

### Park Operates at Theoretical Capacity
- **Assumption:** All rides run continuously at their published theoretical hourly capacity with no downtime, mechanical issues, or staffing constraints.
- **Limitation:** Real parks experience significant operational variance. Battle at the Ministry, for example, runs at ~66% of theoretical capacity due to frequent downtime. This assumption represents a best-case scenario for park operations.

## Enjoyment Score Assumptions

### Log-Normalized Demand Proxy
- **Assumption:** Enjoyment scores are derived from `avg_queue_size = avg_wait * hourly_capacity / 60` then log-normalized to a 1-10 scale.
- **Reason:** Raw wait time doesn't capture popularity for high-capacity rides. Stardust Racers has a 38-minute wait but 2,700/hr capacity — far more people are riding it than Mine-Cart Madness (116-min wait, 750/hr capacity). The log scale prevents the top ride from completely dominating.
- **Limitation:** This assumes current demand patterns are representative of inherent ride quality, which may not hold for new rides (novelty effect) or rides with operational issues.
