"""Airport coordinates and classification for XP distance band calculation."""

import math

# (lat, lon) for airports relevant to SkyTeam route network
COORDS: dict[str, tuple[float, float]] = {
    # Netherlands
    "AMS": (52.3086, 4.7639),
    "ZWE": (51.2175, 4.4213),  # Antwerp (used as "hack" origin)
    # France — hubs
    "CDG": (49.0097, 2.5479),
    "ORY": (48.7262, 2.3652),
    # France — domestic
    "NCE": (43.6584, 7.2159),
    "MRS": (43.4393, 5.2214),
    "TLS": (43.6291, 1.3638),
    "LYS": (45.7256, 5.0811),
    "BOD": (44.8283, -0.7153),
    "NTE": (47.1532, -1.6107),
    "BIA": (42.5527, 9.4837),
    "AJA": (41.9236, 8.8029),
    "MPL": (43.5762, 3.9630),
    "RNS": (48.0694, -1.7348),
    "LIL": (50.5633, 3.0868),
    "SXB": (48.5383, 7.6282),
    "CFE": (45.7867, 3.1691),
    "PGF": (42.7404, 2.8707),
    "EGC": (44.8213, 0.5186),
    "PUF": (43.3800, -0.4186),
    "RDZ": (44.4079, 2.4827),
    "AUR": (44.8914, 2.4219),
    "LRH": (46.1792, -1.1953),
    "DNR": (48.5877, -2.0800),
    "BVE": (45.0397, 1.4856),
    # Italy
    "VCE": (45.5053, 12.3519),
    "BLQ": (44.5354, 11.2887),
    "FLR": (43.8100, 11.2051),
    "CTA": (37.4668, 15.0664),
    "PMO": (38.1760, 13.0910),
    "BRI": (41.1389, 16.7606),
    "TRN": (45.2008, 7.6497),
    "GOA": (44.4133, 8.8375),
    # North Africa
    "TUN": (36.8510, 10.2272),
    "CMN": (33.3675, -7.5898),
    "RAK": (31.6069, -8.0363),
    "ALG": (36.6910, 3.2155),
    "ORN": (35.6240, -0.6212),
    "RBA": (34.0515, -6.7515),
    "TNG": (35.7269, -5.9169),
    # Scandinavia
    "CPH": (55.6180, 12.6508),
    "OSL": (60.1976, 11.1004),
    "ARN": (59.6519, 17.9186),
    "GOT": (57.6628, 12.2798),
    "BGO": (60.2934, 5.2181),
    "SVG": (58.8767, 5.6378),
    "TRD": (63.4578, 10.9240),
    "TOS": (69.6833, 18.9189),
    "MMX": (55.5363, 13.3762),
    "BLL": (55.7403, 9.1518),
    "AAL": (57.0928, 9.8492),
    "LLA": (65.5438, 22.1220),
    "UME": (63.7918, 20.2828),
    "BOO": (67.2692, 14.3653),
    "AES": (62.5625, 6.1197),
    "EVE": (68.4913, 16.6781),
    "ALF": (69.9761, 23.3717),
    "KKN": (69.7258, 29.8913),
    "HAU": (59.3453, 5.2083),
    "MOL": (62.7447, 7.2625),
    "KSU": (63.1118, 7.8245),
    "FRO": (61.5836, 5.0247),
    "KRN": (67.8228, 20.3369),
    "OSD": (63.1944, 14.5003),
    "SDL": (62.5281, 17.4439),
    "VBY": (57.6628, 18.3462),
    "SFT": (64.6248, 21.0769),
    "FAE": (62.0636, -7.2772),
    # Spain
    "MAD": (40.4936, -3.5668),
    "TFN": (28.4827, -16.3415),
    "LPA": (27.9319, -15.3866),
    "ACE": (28.9455, -13.6052),
    "FUE": (28.4527, -13.8638),
    "PMI": (39.5517, 2.7388),
    "IBZ": (38.8729, 1.3731),
    "AGP": (36.6749, -4.4991),
    "ALC": (38.2822, -0.5582),
    "VLC": (39.4893, -0.4816),
    "BIO": (43.3011, -2.9106),
    "SCQ": (42.8963, -8.4152),
    "SVQ": (37.4180, -5.8931),
    "BCN": (41.2971, 2.0785),
    # Romania / Balkans
    "OTP": (44.5711, 26.0850),
    "CLJ": (46.7852, 23.6862),
    "TSR": (45.8098, 21.3379),
    "IAS": (47.1785, 27.6204),
    "SCV": (47.6878, 26.3548),
    "SOF": (42.6952, 23.4062),
    "BEG": (44.8184, 20.3091),
    # European hubs
    "KRK": (50.0777, 19.7848),
    "BUD": (47.4298, 19.2611),
    "WAW": (52.1657, 20.9671),
    "ATH": (37.9364, 23.9445),
    "IST": (41.2753, 28.7519),
    "BER": (52.3667, 13.5033),
    "DUB": (53.4213, -6.2701),
    "LIS": (38.7813, -9.1359),
    "FCO": (41.8003, 12.2389),
    "NAP": (40.8860, 14.2908),
    "OPO": (41.2481, -8.6814),
    "LHR": (51.4700, -0.4543),
    "MXP": (45.6306, 8.7281),
    # Middle East
    "JED": (21.6796, 39.1565),
    "RUH": (24.9576, 46.6988),
    "BEY": (33.8209, 35.4884),
    "AMM": (31.7226, 35.9932),
    "DXB": (25.2532, 55.3657),
    "CAI": (30.1219, 31.4056),
    "DOH": (25.2731, 51.6081),
    "TLV": (32.0114, 34.8867),
    # US — Delta hubs
    "ATL": (33.6407, -84.4277),
    "DTW": (42.2124, -83.3534),
    "MSP": (44.8848, -93.2223),
    "SEA": (47.4502, -122.3088),
    "SLC": (40.7884, -111.9778),
    "BOS": (42.3656, -71.0096),
    "JFK": (40.6413, -73.7781),
    "LAX": (33.9425, -118.4081),
    "MIA": (25.7959, -80.2870),
    # Asia Pacific
    "ICN": (37.4602, 126.4407),
    "NRT": (35.7647, 140.3864),
    "KIX": (34.4347, 135.2440),
    "PVG": (31.1443, 121.8083),
    "XMN": (24.5440, 118.1277),
    "HAN": (21.2187, 105.8070),
    "SGN": (10.8188, 106.6520),
    "CGK": (-6.1256, 106.6558),
    "TPE": (25.0797, 121.2342),
    "BKK": (13.6900, 100.7501),
    "SIN": (1.3502, 103.9944),
    "DEL": (28.5562, 77.1000),
    # Africa
    "DSS": (14.7397, -17.4902),
    "ABJ": (5.2614, -3.9262),
    "DLA": (4.0061, 9.7194),
    "BZV": (-4.2517, 15.2530),
    "BKO": (12.5335, -7.9499),
    "COO": (6.3573, 2.3844),
    "CKY": (9.5769, -13.6120),
    "OUA": (12.3532, -1.5124),
    "NDJ": (12.1337, 15.0340),
    "TNR": (-18.7969, 47.4788),
    "CPT": (-33.9649, 18.6017),
    "NBO": (-1.3192, 36.9278),
    "JNB": (-26.1392, 28.2460),
    "ACC": (5.6052, -0.1668),
    "DAR": (-6.8781, 39.2026),
    "LOS": (6.5774, 3.3212),
    # DOM-TOM
    "FDF": (14.5910, -61.0032),
    "PTP": (16.2653, -61.5318),
    "CAY": (4.8195, -52.3604),
    "RUN": (-20.8871, 55.5103),
    # Caribbean
    "CUR": (12.1889, -68.9598),
    "AUA": (12.5014, -70.0152),
    "SXM": (18.0410, -63.1089),
    "BON": (12.1310, -68.2685),
    "PBM": (5.4528, -55.1879),
    # Americas
    "MEX": (19.4363, -99.0721),
    "CUN": (21.0365, -86.8771),
    "BOG": (4.7016, -74.1469),
    "EZE": (-34.8222, -58.5358),
    "GRU": (-23.4356, -46.4731),
    "LIM": (-12.0219, -77.1143),
    "YUL": (45.4706, -73.7408),
}

FRENCH_DOMESTIC = frozenset([
    "NCE", "MRS", "TLS", "LYS", "BOD", "NTE", "BIA", "AJA",
    "ORY", "CDG", "MPL", "RNS", "LIL", "SXB", "CFE",
    "PGF", "EGC", "PUF", "RDZ", "AUR", "LRH", "DNR", "BVE",
])

CITY_NAMES: dict[str, str] = {
    "AMS": "Amsterdam", "CDG": "Paris CDG", "ORY": "Paris Orly",
    "NCE": "Nice", "MRS": "Marseille", "TLS": "Toulouse", "LYS": "Lyon",
    "BOD": "Bordeaux", "NTE": "Nantes", "BIA": "Bastia", "AJA": "Ajaccio",
    "TUN": "Tunis", "CMN": "Casablanca", "RAK": "Marrakech",
    "ALG": "Algiers", "RBA": "Rabat", "TNG": "Tangier",
    "CPH": "Copenhagen", "OSL": "Oslo", "ARN": "Stockholm",
    "GOT": "Gothenburg", "BGO": "Bergen", "TRD": "Trondheim", "TOS": "Tromso",
    "MAD": "Madrid", "PMI": "Palma", "AGP": "Malaga", "BCN": "Barcelona",
    "TFN": "Tenerife", "LPA": "Gran Canaria", "ACE": "Lanzarote",
    "OTP": "Bucharest", "CLJ": "Cluj", "TSR": "Timisoara",
    "KRK": "Krakow", "BUD": "Budapest", "WAW": "Warsaw",
    "ATH": "Athens", "IST": "Istanbul", "BER": "Berlin",
    "DUB": "Dublin", "LIS": "Lisbon", "FCO": "Rome",
    "JED": "Jeddah", "RUH": "Riyadh", "BEY": "Beirut", "DXB": "Dubai",
    "ATL": "Atlanta", "JFK": "New York", "LAX": "Los Angeles",
    "MIA": "Miami", "SEA": "Seattle", "BOS": "Boston",
    "ICN": "Seoul", "NRT": "Tokyo", "PVG": "Shanghai",
    "HAN": "Hanoi", "SGN": "Ho Chi Minh", "BKK": "Bangkok", "SIN": "Singapore",
    "DSS": "Dakar", "NBO": "Nairobi", "JNB": "Johannesburg", "CPT": "Cape Town",
    "FDF": "Martinique", "PTP": "Guadeloupe", "RUN": "Reunion", "CAY": "Cayenne",
    "CUR": "Curacao", "AUA": "Aruba", "SXM": "St Maarten",
    "MEX": "Mexico City", "EZE": "Buenos Aires", "GRU": "Sao Paulo",
    "YUL": "Montreal", "BOG": "Bogota", "LIM": "Lima",
    "ZWE": "Antwerp",
    "PGF": "Perpignan", "EGC": "Bergerac", "PUF": "Pau", "RDZ": "Rodez",
    "AUR": "Aurillac", "LRH": "La Rochelle", "DNR": "Dinard", "BVE": "Brive",
    "VCE": "Venice", "BLQ": "Bologna", "FLR": "Florence", "CTA": "Catania",
    "PMO": "Palermo", "BRI": "Bari", "TRN": "Turin", "GOA": "Genoa",
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + (
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distance_miles(origin: str, dest: str) -> float | None:
    """Return great-circle miles between two IATA codes, or None if unknown."""
    a, b = COORDS.get(origin), COORDS.get(dest)
    if not a or not b:
        return None
    return haversine_km(a[0], a[1], b[0], b[1]) * 0.621371
