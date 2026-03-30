"""SkyTeam / Flying Blue airline data and destination groups."""

from dataclasses import dataclass

# IATA codes of airlines that earn Flying Blue XP
FB_AIRLINES: frozenset[str] = frozenset([
    "AF", "KL",   # Air France, KLM (programme owners)
    "HV", "TO",   # Transavia NL / FR
    "DL",         # Delta Air Lines
    "KE",         # Korean Air
    "SV",         # Saudia
    "RO",         # TAROM
    "ME",         # MEA (Middle East Airlines)
    "MU",         # China Eastern
    "MF",         # XiamenAir
    "CI",         # China Airlines
    "AR",         # Aerolineas Argentinas
    "VN",         # Vietnam Airlines
    "GA",         # Garuda Indonesia
    "UX",         # Air Europa
    "AM",         # Aeromexico
    "KQ",         # Kenya Airways
    "SK",         # SAS (joined SkyTeam Sep 2024)
])

AIRLINE_NAMES: dict[str, str] = {
    "KL": "KLM", "AF": "Air France", "DL": "Delta", "KE": "Korean Air",
    "SV": "Saudia", "RO": "TAROM", "ME": "MEA", "MU": "China Eastern",
    "MF": "XiamenAir", "CI": "China Airlines", "AR": "Aerolineas Argentinas",
    "VN": "Vietnam Airlines", "GA": "Garuda", "UX": "Air Europa",
    "AM": "Aeromexico", "KQ": "Kenya Airways", "SK": "SAS",
    "HV": "Transavia", "TO": "Transavia FR",
}


@dataclass
class DestGroup:
    id: str
    label: str
    description: str
    destinations: list[str]
    default_on: bool = False


DEST_GROUPS: list[DestGroup] = [
    DestGroup(
        id="french_via_cdg",
        label="French via CDG",
        description="AMS-CDG-French city: 15+6 XP per direction",
        destinations=["NCE", "MRS", "TLS", "LYS", "BOD", "NTE", "BIA", "AJA"],
        default_on=True,
    ),
    DestGroup(
        id="north_africa",
        label="North Africa",
        description="AMS-CDG-North Africa: 15+15 XP per direction",
        destinations=["TUN", "CMN", "RAK", "ALG", "ORN", "RBA", "TNG"],
        default_on=True,
    ),
    DestGroup(
        id="scandinavia",
        label="Scandinavia (SAS)",
        description="SAS hubs + main cities via CPH/OSL/ARN",
        destinations=["CPH", "OSL", "ARN", "GOT", "BGO", "SVG", "TRD", "TOS", "MMX", "BLL", "AAL"],
    ),
    DestGroup(
        id="scandinavia_small",
        label="Scandinavia remote",
        description="Max stops! Remote airports via CPH/OSL/ARN",
        destinations=["LLA", "UME", "BOO", "AES", "EVE", "ALF", "KKN", "HAU", "MOL", "KSU", "FRO", "KRN", "OSD", "SDL", "VBY", "SFT", "FAE"],
    ),
    DestGroup(
        id="spain_air_europa",
        label="Spain (Air Europa)",
        description="AMS-MAD-Spanish domestic / Canary Islands",
        destinations=["MAD", "TFN", "LPA", "ACE", "FUE", "PMI", "IBZ", "AGP", "ALC", "VLC", "BIO", "SCQ", "SVQ"],
    ),
    DestGroup(
        id="romania_tarom",
        label="Romania (TAROM)",
        description="AMS-OTP-Romanian domestic",
        destinations=["OTP", "CLJ", "TSR", "IAS", "SCV", "SOF", "BEG"],
    ),
    DestGroup(
        id="european_hubs",
        label="European hubs",
        description="Cities often requiring multi-stop from AMS",
        destinations=["KRK", "BUD", "WAW", "ATH", "IST", "BER", "DUB", "LIS", "FCO", "NAP", "OPO"],
    ),
    DestGroup(
        id="middle_east",
        label="Middle East",
        description="Saudia + MEA routes",
        destinations=["JED", "RUH", "BEY", "AMM", "DXB", "CAI", "DOH"],
    ),
    DestGroup(
        id="delta_us",
        label="Delta US hubs",
        description="Delta transatlantic + US domestic",
        destinations=["ATL", "DTW", "MSP", "SEA", "SLC", "BOS", "JFK", "LAX", "MIA"],
    ),
    DestGroup(
        id="asia_pacific",
        label="Asia Pacific",
        description="Korean Air, China Eastern, Vietnam Airlines",
        destinations=["ICN", "NRT", "KIX", "PVG", "XMN", "HAN", "SGN", "CGK", "TPE", "BKK", "SIN", "DEL"],
    ),
    DestGroup(
        id="af_africa",
        label="AF Africa via CDG",
        description="Air France Africa network from CDG",
        destinations=["DSS", "ABJ", "DLA", "BZV", "BKO", "COO", "CKY", "OUA", "NDJ", "TNR", "CPT"],
    ),
    DestGroup(
        id="af_domtom",
        label="DOM-TOM via CDG",
        description="French overseas: huge XP! AMS-CDG-RUN = 102 XP RT",
        destinations=["FDF", "PTP", "CAY", "RUN"],
    ),
    DestGroup(
        id="klm_caribbean",
        label="KLM Caribbean",
        description="Dutch Caribbean + Suriname direct from AMS",
        destinations=["CUR", "AUA", "SXM", "BON", "PBM"],
    ),
    DestGroup(
        id="americas",
        label="Americas",
        description="Aeromexico, Delta, Aerolineas routes",
        destinations=["MEX", "CUN", "BOG", "EZE", "GRU", "LIM"],
    ),
]
