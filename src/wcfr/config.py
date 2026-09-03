PRIORITY_SPECIES = {
    "bluefin tuna", "yellowfin tuna", "albacore tuna", "bigeye tuna",
    "california yellowtail", "white seabass", "chinook salmon", "coho salmon",
    "striped marlin", "blue marlin", "swordfish",
}

REGIONS = {
    "southern_california": {
        "label": "Southern California", "reference_port": "San Diego",
        "point": (32.65, -117.45), "tide_station": "9410170",
        "buoys": ["46232", "46225", "46086"],
    },
    "central_california": {
        "label": "Central California", "reference_port": "Monterey",
        "point": (36.70, -122.05), "tide_station": "9413450",
        "buoys": ["46042", "46240"],
    },
    "northern_california": {
        "label": "Northern California", "reference_port": "Eureka",
        "point": (40.80, -124.45), "tide_station": "9418801",
        "buoys": ["46022", "46014"],
    },
    "oregon": {
        "label": "Oregon", "reference_port": "Newport",
        "point": (44.60, -124.25), "tide_station": "9435380",
        "buoys": ["46050", "46015"],
    },
    "washington": {
        "label": "Washington", "reference_port": "Westport",
        "point": (46.90, -124.35), "tide_station": "9441102",
        "buoys": ["46029", "46041", "46087"],
    },
}

PORTS = {
    "San Diego": (9410170, 32.7157, -117.1611),
    "Los Angeles/Long Beach": (9410660, 33.7542, -118.2165),
    "Santa Barbara": (9411340, 34.4208, -119.6982),
    "Monterey": (9413450, 36.6002, -121.8947),
    "San Francisco": (9414290, 37.8063, -122.4659),
    "Fort Bragg": (9417426, 39.4457, -123.8053),
    "Eureka": (9418801, 40.7665, -124.2170),
    "Brookings": (9430104, 42.0526, -124.2839),
    "Newport": (9435380, 44.6368, -124.0535),
    "Astoria/Columbia River": (9439040, 46.2073, -123.7683),
    "Westport": (9441102, 46.9043, -124.1051),
    "Neah Bay": (9443090, 48.3681, -124.6249),
}
TIDE_STATIONS = {name: str(values[0]) for name, values in PORTS.items()}

SPECIES_HABITAT = {
    "albacore tuna": {"temp_f": (58, 66), "chlorophyll": (0.15, 0.35), "features": ["temperature break", "clean/green edge"]},
    "bluefin tuna": {"temp_f": (60, 72), "features": ["temperature break", "bait concentration", "current edge"]},
    "yellowfin tuna": {"temp_f": (68, 78), "features": ["warm-water edge", "bait concentration"]},
    "bigeye tuna": {"temp_f": (62, 75), "features": ["deep structure", "current convergence", "bait concentration"]},
    "california yellowtail": {"temp_f": (62, 74), "features": ["kelp or structure", "current edge", "bait concentration"]},
    "white seabass": {"temp_f": (58, 70), "features": ["squid or bait concentration", "kelp edge", "low-light period"]},
    "chinook salmon": {"temp_f": (50, 60), "features": ["bait concentration", "upwelling edge", "river plume"]},
    "coho salmon": {"temp_f": (50, 60), "features": ["bait concentration", "upwelling edge"]},
    "striped marlin": {"temp_f": (66, 76), "features": ["warm-water edge", "current convergence", "bait concentration"]},
    "blue marlin": {"temp_f": (72, 82), "features": ["warm blue water", "current convergence"]},
    "swordfish": {"temp_f": (55, 72), "features": ["deep scattering layer", "slope or canyon", "temperature front"]},
}
