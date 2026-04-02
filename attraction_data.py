"""
Epic Universe attraction demand data for simulation.
Wait times and capacities manually verified from thrill-data.com (March 2026).
"""

PARK_CONTEXT = {
    "avg_daily_attendance": 16000,
    "max_ticket_availability": 22000,
    "total_theoretical_hourly_throughput": 18500,
    "park_wide_avg_wait_min": 53.5,
    "peak_day_avg_wait_min": 107,
    "lowest_avg_wait_min": 43,
}

ATTRACTIONS = {
    # --- Celestial Park ---
    "Stardust Racers": {
        "land": "Celestial Park",
        "type": "ride",
        "avg_wait_min": 38,
        "hourly_capacity": 2700,
        "ride_time_min": 1.5,
        "riders_per_hour": 2700,
        "enjoyment_score": 8.1,
    },
    "Constellation Carousel": {
        "land": "Celestial Park",
        "type": "ride",
        "avg_wait_min": 18,
        "hourly_capacity": 480,
        "ride_time_min": 2,
        "riders_per_hour": 480,
        "enjoyment_score": 1.0,
    },
    "Astronomica": {
        "land": "Celestial Park",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },

    # --- Super Nintendo World ---
    "Mario Kart: Bowser's Challenge": {
        "land": "Super Nintendo World",
        "type": "ride",
        "avg_wait_min": 96,
        "hourly_capacity": 1100,
        "ride_time_min": 4,
        "riders_per_hour": 1100,
        "enjoyment_score": 8.2,
    },
    "Mine-Cart Madness": {
        "land": "Super Nintendo World",
        "type": "ride",
        "avg_wait_min": 116,
        "hourly_capacity": 750,
        "ride_time_min": 2,  # not found online, using default
        "riders_per_hour": 750,
        "enjoyment_score": 7.7,
    },
    "Yoshi's Adventure": {
        "land": "Super Nintendo World",
        "type": "ride",
        "avg_wait_min": 45,
        "hourly_capacity": 675,
        "ride_time_min": 5,
        "riders_per_hour": 675,
        "enjoyment_score": 4.6,
    },
    "Mario & Luigi Meet and Greet": {
        "land": "Super Nintendo World",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
    "Princess Peach Meet & Greet": {
        "land": "Super Nintendo World",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
    "Toad Meet & Greet": {
        "land": "Super Nintendo World",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
    "Donkey Kong Meet & Greet": {
        "land": "Super Nintendo World",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },

    # --- Dark Universe ---
    "Monsters Unchained: The Frankenstein Experiment": {
        "land": "Dark Universe",
        "type": "ride",
        "avg_wait_min": 29,
        "hourly_capacity": 2400,
        "ride_time_min": 4,
        "riders_per_hour": 2400,
        "enjoyment_score": 7.0,
    },
    "Curse of the Werewolf": {
        "land": "Dark Universe",
        "type": "ride",
        "avg_wait_min": 54,
        "hourly_capacity": 750,
        "ride_time_min": 2,
        "riders_per_hour": 750,
        "enjoyment_score": 5.4,
    },
    "Dark Universe Character Meet & Greet": {
        "land": "Dark Universe",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
    "Darkmoor Monster Makeup Experience": {
        "land": "Dark Universe",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },

    # --- Wizarding World - Ministry of Magic ---
    "Harry Potter and the Battle at the Ministry": {
        "land": "Wizarding World",
        "type": "ride",
        "avg_wait_min": 90,  # adjusted from 135 (real) to optimal: 135 * 1450/2184
        "hourly_capacity": 2184,
        "ride_time_min": 4.5,
        "riders_per_hour": 2184,
        "enjoyment_score": 10.0,
    },
    "Le Cirque Arcanus": {
        "land": "Wizarding World",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
    "Cosme Acajor Baguettes Magique": {
        "land": "Wizarding World",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },

    # --- How to Train Your Dragon - Isle of Berk ---
    "Hiccup's Wing Gliders": {
        "land": "Isle of Berk",
        "type": "ride",
        "avg_wait_min": 62,
        "hourly_capacity": 1800,
        "ride_time_min": 2,
        "riders_per_hour": 1800,
        "enjoyment_score": 8.4,
    },
    "Dragon Racer's Rally": {
        "land": "Isle of Berk",
        "type": "ride",
        "avg_wait_min": 45,
        "hourly_capacity": 275,
        "ride_time_min": 1.5,
        "riders_per_hour": 275,
        "enjoyment_score": 2.0,
    },
    "Fyre Drill": {
        "land": "Isle of Berk",
        "type": "ride",
        "avg_wait_min": 30,
        "hourly_capacity": 600,
        "ride_time_min": 3.5,
        "riders_per_hour": 600,
        "enjoyment_score": 3.1,
    },
    "The Untrainable Dragon": {
        "land": "Isle of Berk",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
    "Vikings Training Camp": {
        "land": "Isle of Berk",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
    "Meet Toothless and Friends": {
        "land": "Isle of Berk",
        "type": "non_ride",
        "avg_wait_min": 0,
        "hourly_capacity": None,
        "ride_time_min": 0,
    },
}

# Hub-to-hub walking times (minutes) at 3 mph, distances from Google Earth
HUB_WALKING_TIMES = {
    ("Celestial Park", "Isle of Berk"): 1.7,        # 140m
    ("Celestial Park", "Super Nintendo World"): 1.8, # 146m
    ("Celestial Park", "Wizarding World"): 4.1,      # 330m
    ("Celestial Park", "Dark Universe"): 4.3,        # 350m
}

# Directed edges: (from, to) -> time_min
#   Hub -> Hub: bidirectional, walking time
#   Hub -> Attraction: avg wait time of the ride
#   Attraction -> Hub: 1 min (walking back after riding)
EDGES = {}
for (hub_a, hub_b), walk_time in HUB_WALKING_TIMES.items():
    EDGES[(hub_a, hub_b)] = walk_time
    EDGES[(hub_b, hub_a)] = walk_time

for name, data in ATTRACTIONS.items():
    EDGES[(data["land"], name)] = data["avg_wait_min"]  # hub -> attraction = wait time
    EDGES[(name, data["land"])] = 1                      # attraction -> hub = 1 min

# Convenience: list of lands and their attractions
LANDS = {}
for name, data in ATTRACTIONS.items():
    land = data["land"]
    LANDS.setdefault(land, []).append(name)
