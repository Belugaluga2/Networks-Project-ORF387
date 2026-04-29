# Dynamic Congestion in Theme Park Queuing Networks: A Stochastic Congestion Game Simulation

**Evan Cantwell, Tanay Dalmia, Zubayer Mahbub**
*ORF 387: Networks — Spring 2026 Progress Report*

---

## [1] Motivation, Vision, and Problem Statement

Theme parks are among the most complex real-world instances of a networked congestion game. Thousands of utility-maximizing agents — park visitors — traverse a spatial network of attractions connected by pathways, each simultaneously choosing destinations based on incomplete information about the system state. The result is a decentralized, emergent equilibrium that is, in general, far from socially optimal — producing systemic waste in the form of avoidable waiting.

**Central research question:** How do congestion, stochastic arrivals, and different queuing strategies jointly influence equilibrium behavior and systemic efficiency in networked theme park queuing environments? Specifically, can virtual queue interventions — skip-the-line passes, timed reservations, and on-demand queue-skipping — increase aggregate visitor happiness compared to a standard first-come-first-served (FCFS) baseline?

**Practical stakes.** Virtual queue systems at Disney World (Genie+) and Universal Studios (Express Pass) have repeatedly underperformed or caused visitor backlash. We aim to quantify *why* some strategies work better than others by modeling each as a structural modification to the queuing network's service discipline and measuring the effect on total visitor utility.

**Case study.** We apply this framework to Universal Studios' **Epic Universe** (opened May 2025), a new park with five themed lands, 11 major ride attractions, and a hub-and-spoke spatial layout. Its recency provides a genuine modeling challenge while its scale produces rich congestion dynamics.

**Course topics applied:**
- **Congestion games and potential functions** (Easley & Kleinberg, Ch. 8): The park is formally a weighted congestion game where edge costs (wait times) are non-decreasing functions of flow. Rosenthal's theorem guarantees convergence to a pure-strategy Nash equilibrium under best-response dynamics.
- **Price of Anarchy** (Ch. 8): We measure the gap between the decentralized equilibrium and what a centralized planner could achieve, quantifying the cost of selfish routing.
- **Shortest-path routing** (Ch. 3): Agents use Dijkstra's algorithm on the directed park graph to compute travel times when making ride selection decisions.
- **Informational cascades** (Ch. 16): Under lagged information regimes (planned for final report), delayed wait-time signals cause herding behavior that compounds congestion dynamics.

**Project vision.** We build an agent-based simulation of Epic Universe calibrated to real wait-time and capacity data, then systematically test a battery of virtual queue strategies to identify which maximizes total park happiness. Our goal is to derive concrete, data-grounded recommendations for theme park operators about optimal queuing design.

---

## [2] Methodologies, Setup, and Mathematical Framework

### 2.1 Network Model

We represent Epic Universe as a weighted directed graph $G = (V, E)$ where the node set $V = V_H \cup V_A$ consists of **hub nodes** $V_H$ (themed land centers) and **attraction nodes** $V_A$ (individual rides).

- $|V_H| = 5$ hub nodes: Celestial Park (central hub), Super Nintendo World, Dark Universe, Wizarding World, Isle of Berk
- $|V_A| = 11$ attraction nodes: the queue-based rides with published capacity and wait-time data
- Total: $|V| = 16$ nodes, $|E| = 30$ directed edges

**Hub-and-spoke topology.** All inter-land travel must route through Celestial Park, matching the real park's portal system. There are no direct connections between themed lands. This produces a star graph at the hub level with ride nodes as leaves attached to their respective land hubs.

**Edge cost structure:**

| Edge Type | Direction | Weight | Count |
|---|---|---|---|
| Hub-to-hub (walkways) | Bidirectional | $c_e = d_e$ (walking time in minutes) | 8 |
| Hub-to-attraction (ride entrance) | Hub $\to$ Ride | $c_e = 1$ min | 11 |
| Attraction-to-hub (ride exit) | Ride $\to$ Hub | $c_e = 1$ min | 11 |

Hub-to-hub distances were measured as straight-line distances between land centers using Google Earth satellite imagery and converted to walking time at 80 m/min (approximately 3 mph):

| Route | Distance (m) | Walking Time (min) |
|---|---|---|
| Celestial Park $\leftrightarrow$ Isle of Berk | 140 | 1.7 |
| Celestial Park $\leftrightarrow$ Super Nintendo World | 146 | 1.8 |
| Celestial Park $\leftrightarrow$ Wizarding World | 330 | 4.1 |
| Celestial Park $\leftrightarrow$ Dark Universe | 350 | 4.3 |

### 2.2 Attraction Data and Enjoyment Scores

All ride data was manually verified from thrill-data.com lifetime summary statistics (as of March 2026). For each of the 11 rides, we collected average wait time, theoretical hourly capacity, and ride duration from multiple theme park databases (orlandoinformer.com, undercovertourist.com, frommers.com, attractionsmagazine.com).

**Enjoyment score derivation.** Raw wait time alone does not capture true popularity because high-capacity rides process more visitors with shorter waits. We estimate underlying demand using Little's Law:

$$\bar{Q}_a = \bar{W}_a \cdot \frac{\mu_a}{60}$$

where $\bar{W}_a$ is the lifetime average wait (minutes) and $\mu_a$ is hourly capacity (riders/hour). The enjoyment score is then log-normalized to a 1–10 scale:

$$h_a = 1 + 9 \cdot \frac{\ln \bar{Q}_a - \ln \bar{Q}_{\min}}{\ln \bar{Q}_{\max} - \ln \bar{Q}_{\min}}$$

This produces scores where Harry Potter and the Battle at the Ministry ($h = 10.0$) ranks highest — reflecting both its extreme wait times and high capacity — while Constellation Carousel ($h = 1.0$) ranks lowest. The log scale prevents a single dominant ride from compressing all other scores.

**Capacity conversion.** The simulation dispatches riders in discrete cycles. Per-cycle capacity is derived from hourly throughput:

$$C_a = \text{round}\left(\mu_a \cdot \frac{s_a}{60}\right)$$

where $s_a$ is the ride duration in minutes. For example, Stardust Racers with $\mu_a = 2{,}700$ riders/hr and $s_a = 1.5$ min yields $C_a = \text{round}(2700 \times 1.5 / 60) = 68$ riders per cycle.

### 2.3 Agent Model and Utility Function

We model $N \approx 20{,}000$ agents (park visitors), each seeking to maximize total accumulated happiness over their visit. Each agent $i$ has a heterogeneous personal preference vector drawn at creation:

$$\text{pref}_{ia} \sim \max(0.1,\; \mathcal{N}(1.0, 0.3)) \quad \forall a \in V_A$$

This multiplicative model gives 30% relative variation — agents agree on the rough ranking of rides but differ meaningfully in personal taste.

**Utility function.** At each decision point, agent $i$ evaluates every ride $a$ using:

$$U_i(a, t) = \frac{h_a \cdot \text{pref}_{ia} \cdot \gamma_i(t) \cdot r_{ia}}{\sqrt{1 + W_t(a) + D(v_i, a)}}$$

where:
- $h_a$ is the ride's enjoyment score (1–10), derived from real data as described in Section 2.2
- $\text{pref}_{ia}$ is the agent's personal preference multiplier
- $\gamma_i(t) = \frac{T_{\text{dep},i} - t}{T_{\text{dep},i} - T_{\text{arr},i}}$ is a linear time-decay factor (1.0 at arrival, 0.0 at planned departure)
- $r_{ia} = \frac{1}{1 + 0.5 \, n_{ia}}$ is a diminishing-returns factor for re-rides, where $n_{ia}$ counts prior rides on attraction $a$ (1st ride: 100%, 2nd: 67%, 3rd: 50%, 4th: 40%)
- $W_t(a)$ is the dynamic estimated wait time at attraction $a$ at time $t$
- $D(v_i, a)$ is the shortest-path travel time from agent $i$'s current node $v_i$ to attraction $a$, computed via Dijkstra's algorithm on the park graph

The $\sqrt{1 + W + D}$ denominator was chosen to ensure that: (1) utility is always non-negative, so agents remain in the park throughout the day rather than departing after a few rides; (2) agents tolerate long waits for high-value rides, matching real visitor behavior; and (3) wait and travel time impose diminishing rather than absolute penalties. An earlier subtractive formulation ($U = H - W - D$) caused agents to leave after 4–5 rides because the 1–10 enjoyment scale could not compete with wait times of 30–100 minutes.

Agent $i$ selects $a^* = \arg\max_{a \in V_A} U_i(a, t)$, subject to the feasibility constraint $D + W + s_a \leq T_{\text{dep},i} - t$. If no ride yields positive utility, the agent departs the park early.

**Dynamic wait time estimation.** The estimated wait time at ride $a$ with current queue length $x_a$, pending committed arrivals $p_a$, per-cycle capacity $C_a$, and service rate $s_a$ is:

$$W_t(a) = \frac{x_a + p_a}{C_a} \cdot s_a$$

This deterministic-service model is consistent with the fixed cycle structure of theme park rides (batch dispatch every $s_a$ minutes).

### 2.4 Arrival and Departure Dynamics

**Arrival model (two components):**

1. **Gate rush:** 3,000 agents arrive during the first 30 minutes with inter-arrival times drawn from $\text{Exp}(\lambda = 1/5)$ minutes, clipped to $[0, 30]$. This models the realistic constraint that turnstiles limit the rate at which visitors can enter.

2. **Steady state:** From $t = 30$ to $t = 720$ (park close), new agents arrive each minute at rate $\text{Poisson}(17{,}000 / 690 \approx 24.6)$. Total steady-state arrivals $\approx 17{,}000$.

Combined daily attendance: $\approx 20{,}000$ agents, consistent with reported Epic Universe averages of 16,000–22,000 daily visitors.

**Departure model:** Each agent's planned departure time $T_{\text{dep},i} \sim \mathcal{N}(600, 60)$ minutes from park open (mean 7:00 PM), clipped to $[T_{\text{arr},i} + 60, \, 720]$. Agents also depart early if all rides yield zero or negative utility.

### 2.5 Simulation Architecture

The simulation is a discrete-time agent-based model with timestep $\Delta t = 1$ minute, running for 720 steps (9:00 AM to 9:00 PM). Each timestep executes seven sequential phases:

1. **Arrivals:** Agents whose arrival time $T_{\text{arr},i} \leq t$ enter the park at the Celestial Park hub and begin deciding.

2. **Ride processing:** For each attraction, if the cycle timer exceeds the service rate $s_a$, the ride dispatches up to $C_a$ riders. Priority queue riders (pass holders) board first; remaining capacity is filled from the regular FIFO queue. Completed riders accumulate happiness $h_a \cdot \text{pref}_{ia} \cdot \gamma_i(t)$. The cycle timer carries over excess time ($\tau \leftarrow \tau - s_a$) to prevent throughput loss from discretization of non-integer cycle times.

3. **Departures:** Agents past their planned departure time exit the system and are removed from any queue they occupy.

4. **Decisions (sequential best-response):** All deciding agents are shuffled randomly and processed one at a time. Each agent computes $U_i(a, t)$ for all 11 rides using a single-source Dijkstra from their current position, then commits to the highest-utility ride. Each commitment increments a *pending arrivals* counter on the target ride, so the next agent sees an updated wait estimate. This implements a **sequential best-response dynamic** — a core mechanism in congestion game theory. Under this process, the Rosenthal potential function $\Phi(x) = \sum_{e \in E} \sum_{k=1}^{x_e} c_e(k)$ strictly decreases with each improvement move, guaranteeing convergence to a pure-strategy Nash equilibrium (Easley & Kleinberg, Theorem 8.3).

5. **Travel:** Agents in transit decrement their remaining travel time. Upon arriving at a ride node, they enter either the priority queue (if using a pass) or the regular FIFO queue.

6. **Wait tracking:** All queued agents accumulate $\Delta t$ of wait time for post-simulation analysis.

7. **Snapshot:** Queue lengths, agent state counts, and traveling flows are recorded for analysis and visualization.

### 2.6 Virtual Queue Strategies

We test three virtual queue strategies against a first-come-first-served (FCFS) baseline. Each strategy gives every agent **3 skip-the-line passes**. All strategies share the same priority queue mechanics: pass holders enter a separate priority queue at the ride, and during each dispatch cycle, the ride fills seats from the priority queue first, then fills remaining capacity from the regular queue. This means pass holders consume ride capacity that would otherwise serve regular riders — a realistic model of how Express Pass systems work in practice.

**Strategy 1 — Preselect (Anytime).** At park entry, each agent selects their top 3 rides by personal valuation $h_a \cdot \text{pref}_{ia}$. They may use these passes at any time during the day. When evaluating utility for a ride with an available pass, the agent sets $W = 0$. This models an unrestricted Express Pass.

**Strategy 2 — Preselect (Timed Slots).** Same top-3 selection, but each pass is assigned to a specific 5-minute time slot. The park distributes slots via round-robin across 144 windows per ride (720 min / 5 min = 144), ensuring even load distribution throughout the day. Each agent's 3 passes must be spaced at least 30 minutes apart. Each pass is valid within a $\pm 15$ minute window around its assigned slot; expired passes are forfeited. This models Disney's former FastPass+ and similar time-reservation systems.

**Strategy 3 — Dynamic (On-Demand).** Each agent carries 3 unassigned passes and decides when to use them in real time. When an agent selects a ride whose estimated wait exceeds 30 minutes, they burn a pass to skip the queue. This models an adaptive system where guests make on-the-fly decisions about which queues to skip.

---

## [3] Simulated Data

### 3.1 Data Sources

| Source | Data Collected | Use in Model |
|---|---|---|
| thrill-data.com (lifetime stats) | Average wait times, hourly capacity for all 11 rides | Enjoyment scores $h_a$, service rates $\mu_a$ |
| Google Earth satellite imagery | Straight-line distances between 5 land centers | Hub-to-hub edge weights |
| orlandoinformer.com, undercovertourist.com, frommers.com, attractionsmagazine.com | Ride durations (1.5–5 min per ride) | Cycle time $s_a$ |
| thrill-data.com, disneytouristblog.com | Daily attendance estimates (16,000–22,000) | Total agent count $N$ |

### 3.2 Attraction Parameter Table

| Attraction | Land | Avg Wait (min) | Capacity (riders/hr) | Ride Time (min) | Per-Cycle Cap | Enjoyment |
|---|---|---|---|---|---|---|
| Harry Potter Battle at Ministry | Wizarding World | 90* | 2,184 | 4.5 | 164 | 10.0 |
| Hiccup's Wing Gliders | Isle of Berk | 62 | 1,800 | 2.0 | 60 | 8.4 |
| Mario Kart: Bowser's Challenge | Super Nintendo | 96 | 1,100 | 4.0 | 73 | 8.2 |
| Stardust Racers | Celestial Park | 38 | 2,700 | 1.5 | 68 | 8.1 |
| Mine-Cart Madness | Super Nintendo | 116 | 750 | 2.0 | 25 | 7.7 |
| Monsters Unchained | Dark Universe | 29 | 2,400 | 4.0 | 160 | 7.0 |
| Curse of the Werewolf | Dark Universe | 54 | 750 | 2.0 | 25 | 5.4 |
| Yoshi's Adventure | Super Nintendo | 45 | 675 | 5.0 | 56 | 4.6 |
| Fyre Drill | Isle of Berk | 30 | 600 | 3.5 | 35 | 3.1 |
| Dragon Racer's Rally | Isle of Berk | 45 | 275 | 1.5 | 7 | 2.0 |
| Constellation Carousel | Celestial Park | 18 | 480 | 2.0 | 16 | 1.0 |

*\*Harry Potter's observed average wait is 135 min under actual operations (~1,450 riders/hr). We adjusted to 90 min to model optimal theoretical capacity (2,184 riders/hr), since our simulation assumes all rides run at full capacity. See Assumptions document.*

### 3.3 Key Modeling Assumptions

- **Optimal operations:** All rides run continuously at theoretical hourly capacity with no downtime.
- **Rational agents:** Visitors are individual utility maximizers with perfect information about current queue lengths.
- **No group dynamics:** Each agent makes independent decisions (real visitors travel in groups).
- **Attractions at hub center:** All rides within a land are co-located at the land hub center; intra-land walking variation is not modeled.
- **Hub-and-spoke only:** No shortcuts between lands; all inter-land travel routes through Celestial Park.

A full accounting of all assumptions is maintained in a separate Assumptions document in our repository.

---

## [4] Preliminary Results (No Conclusions Yet)

### 4.1 Baseline Simulation (FCFS, Full Information)

| Metric | Value |
|---|---|
| Total agents generated | ~20,000 |
| Peak in-park population | ~13,800 (5:00 PM) |
| Avg rides completed per agent | 8.0 |
| Avg wait time per ride | 32 min |
| Total park happiness (sum across all agents) | 753,326 |
| Most congested ride | Harry Potter (peak queue: 2,761) |

The simulated congestion ranking matches real-world observations: Harry Potter, Hiccup's Wing Gliders, and Mario Kart are the three most congested attractions. Simulated per-ride waits are lower than real-world park averages (32 min vs. 53.5 min), which is expected because our rational agents spread load more efficiently than real visitors who exhibit herding and incomplete-information behavior.

### 4.2 Virtual Queue Strategy Comparison

| Metric | Baseline (FCFS) | Preselect (Anytime) | Preselect (Timed) | Dynamic |
|---|---|---|---|---|
| Total Park Happiness | 753,326 | 930,841 | 757,840 | 881,772 |
| **% Change vs Baseline** | **---** | **+23.6%** | **+0.6%** | **+17.1%** |
| Avg Total Wait (min) | 256.5 | 259.5 | 263.1 | 290.8 |
| Avg Rides per Agent | 8.0 | 7.8 | 8.1 | 7.4 |
| Total Passes Used | 0 | 59,781 | 13,826 | 20,144 |
| Peak Queue (Harry Potter) | 2,761 | 2,746 | 2,768 | 783 |

**Observations (not yet conclusions):**

- **Preselect (Anytime) produces the highest total happiness (+23.6%).** Agents get guaranteed skip-the-line access to their personally highest-valued rides, accumulating more enjoyment even though they complete slightly fewer total rides (7.8 vs 8.0).

- **Timed slots barely improve over baseline (+0.6%).** Only 13,826 of approximately 60,000 possible passes were actually used, because agents are frequently at the wrong location when their assigned time window opens. This suggests a fundamental utilization problem with time-slotted systems when agents are making locally optimal decisions — the globally assigned schedule conflicts with each agent's real-time best-response path through the park.

- **Dynamic passes are the most efficient at reducing peak congestion.** Harry Potter's peak queue drops from 2,761 to 783 — a 72% reduction — because agents selectively skip only the queues that exceed the 30-minute threshold. However, only 20,144 passes were used (vs. 59,781 for preselect), suggesting the threshold mechanism is selective.

- **All virtual queue strategies increase total wait time.** This is counterintuitive: virtual queues are designed to reduce waiting. The mechanism is that pass holders experience higher utility (they skip their worst waits), which keeps them in the park longer rather than departing early, causing them to accumulate more total queue time on their additional rides. Individual rides are faster, but agents stay for more rides overall.

- **Pass holders consume ride capacity from non-pass-holders.** The priority queue mechanics mean that when a pass holder boards, one fewer seat is available for the standby queue. This is realistic (it is exactly how Express Pass works), and it creates a distributional tension: pass holders gain utility at the expense of slightly longer waits for everyone else.

### 4.3 Per-Ride Average Queue Length

| Ride | Baseline | Preselect | Timed | Dynamic |
|---|---|---|---|---|
| Harry Potter | 1,142 | — | — | — |
| Hiccup's Wing Gliders | 837 | — | — | — |
| Mario Kart | 797 | — | — | — |
| Stardust Racers | 776 | — | — | — |
| Mine-Cart Madness | 651 | — | — | — |
| Monsters Unchained | 526 | — | — | — |
| Curse of the Werewolf | 290 | — | — | — |
| Yoshi's Adventure | 211 | — | — | — |
| Fyre Drill | 87 | — | — | — |
| Dragon Racer's Rally | 29 | — | — | — |
| Constellation Carousel | 23 | — | — | — |

*Per-ride breakdown for non-baseline strategies to be added in final report.*

---

## [5] Changes and Progress Made from Initial Proposal

1. **We updated our utility function**
    - Our original proposal used a subtractive formulation: $U = h_{ia} - w_1 W - w_2 D - w_3(T_{\text{close}} - t - W)$. This caused agents to leave the park after only 4–5 rides because enjoyment scores (1–10 scale) could not compete with wait times measured in minutes (30–100+). We replaced this with a multiplicative formulation $U = H \cdot \text{pref} \cdot \gamma \cdot r / \sqrt{1 + W + D}$ that keeps utility always non-negative and produces realistic all-day visits of 8+ rides per agent.

2. **We narrowed our focus into evaluating the utility differentials between a wide host of queuing strategies**
    - Rather than focusing primarily on Braess's Paradox as proposed, we shifted toward a practical comparative analysis of virtual queue interventions. We implemented and compared three distinct strategies (preselect anytime, preselect timed slots, dynamic on-demand) against the FCFS baseline, measuring total park happiness as the primary metric. This pivot provides more actionable insights for theme park operators.

3. **We collected data from the following sources**
    - thrill-data.com: lifetime average wait times and capacity statistics for all 11 ride attractions, manually verified from each ride's individual summary statistics page
    - Google Earth: straight-line distances between the 5 land centers, converted to walking time at 80 m/min
    - orlandoinformer.com, undercovertourist.com, frommers.com, attractionsmagazine.com: ride durations for each attraction
    - Park attendance reports: daily attendance estimates of 16,000–22,000 for calibrating agent count

4. **We ran the following simulations**
    - Baseline (FCFS, no virtual queues): ~20,000 agents, full 12-hour day, full real-time information
    - Preselect (Anytime): 3 skip passes per agent for top-3 personal rides, usable any time
    - Preselect (Timed Slots): 3 skip passes assigned to 5-minute time windows distributed via round-robin across 144 daily slots per ride
    - Dynamic (On-Demand): 3 unassigned passes, used when estimated wait exceeds 30 minutes
    - All four simulations use the same random seed for direct comparison

5. **We separated our optimal framework from our realistic framework**
    - Our current simulation models an "optimal operations" scenario: all rides running at theoretical capacity, agents with perfect real-time information, and fully rational decision-making. For the final report, we plan to introduce a "realistic" framework with information lag (5-minute delayed wait time updates), reduced ride throughput (matching observed operational capacity), and bounded rationality. Comparing the two frameworks will quantify how much real-world inefficiency is due to information structure versus operational constraints.

---

## [6] Next Steps for Our Project

1. **Expanding attraction coverage**
    - Currently we model only the 11 ride attractions with published wait-time data. We are considering adding shows (Le Cirque Arcanus, The Untrainable Dragon) and interactive experiences (meet-and-greets) with estimated or synthetically generated wait-time and capacity data. This would increase the graph to ~20 attraction nodes and provide agents with more non-ride options that might reduce ride congestion.

2. **Additional queuing strategies**
    - **Priced Express Pass:** Model a paid skip-the-line system where the pass price $p_a$ reduces effective enjoyment ($h_{\text{eff}} = h_a - p_a$). Only agents whose personal valuation exceeds the price will purchase. We will derive the congestion-correcting Pigouvian toll $p_a^* = x_a^* / \mu_a$ analytically and compare it to the empirically optimal price found via grid search.
    - **Unlimited free virtual queue:** Every agent can skip every queue for free. This tests whether an unrestricted virtual queue worsens aggregate welfare — a direct test of whether Braess-like paradox effects emerge.
    - **Capacity-constrained timed entry:** Limit the number of skip passes available per time window (e.g., $K = 25$ per 5-min slot per ride) to test whether supply constraints improve the timed strategy's poor utilization rate.

3. **Information regime comparison**
    - Implement three information structures: (i) full information (current — agents see real-time queues), (ii) lagged information (agents see queue lengths from 5 minutes ago, matching real app update cycles), and (iii) no information (agents choose based solely on ride enjoyment and distance). Compare total happiness and congestion variance across regimes to quantify the value of information in the congestion game.

4. **Price of Anarchy computation**
    - Implement a centralized planner simulation where a single controller assigns each agent to the ride that minimizes total system wait (rather than maximizing individual utility). Use this as the social optimum benchmark to compute PoA = SC(Nash) / SC(Optimal). Theory predicts PoA $\leq 4/3$ for linear congestion costs; our nonlinear utility may produce different values.

5. **Monte Carlo robustness**
    - Run 50 independent simulation runs per strategy with different random seeds. Report mean and 95% confidence intervals for all metrics to ensure results are robust to stochastic variation in agent preferences and arrival times.

6. **Interactive visualization**
    - We have built an interactive HTML visualization that displays the park graph with animated agent flows, queue sizes, and a strategy dropdown for comparing all four scenarios in real time. We plan to add per-ride wait-time charts and a side-by-side comparison mode for the final presentation.
