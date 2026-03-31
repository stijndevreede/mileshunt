"""Destination catalog: continents, route sets, community favorites, and custom search."""

from __future__ import annotations

from dataclasses import dataclass, field
from mileshunt.airports import CITY_NAMES


@dataclass
class DestCategory:
    """A category tab in the destination picker."""
    id: str
    label: str
    icon: str  # emoji or short label
    items: list[DestItem]


@dataclass
class DestItem:
    """A selectable group of destinations."""
    id: str
    label: str
    description: str
    destinations: list[str]
    tags: list[str] = field(default_factory=list)  # searchable tags


# ── Continents ──────────────────────────────────────────────

CONTINENTS: list[DestItem] = [
    DestItem(
        id="europe_west",
        label="Western Europe",
        description="France, Benelux, UK, Ireland, Iberia",
        destinations=["CDG", "ORY", "NCE", "MRS", "TLS", "LYS", "BOD", "NTE", "BIA", "AJA",
                       "MPL", "PGF", "PUF", "LHR", "DUB", "LIS", "OPO", "MAD", "BCN", "PMI",
                       "AGP", "IBZ", "BER", "MXP"],
        tags=["france", "uk", "spain", "portugal", "germany"],
    ),
    DestItem(
        id="europe_north",
        label="Northern Europe / Scandinavia",
        description="SAS network: Norway, Sweden, Denmark, Finland, Faroes",
        destinations=["CPH", "OSL", "ARN", "GOT", "BGO", "SVG", "TRD", "TOS", "MMX", "BLL",
                       "AAL", "LLA", "UME", "BOO", "AES", "EVE", "ALF", "KKN", "HAU", "MOL",
                       "KSU", "FRO", "KRN", "OSD", "SDL", "VBY", "SFT", "FAE"],
        tags=["scandinavia", "norway", "sweden", "denmark", "sas"],
    ),
    DestItem(
        id="europe_east",
        label="Eastern Europe",
        description="Romania, Poland, Hungary, Balkans, Baltics",
        destinations=["OTP", "CLJ", "TSR", "IAS", "SCV", "KRK", "WAW", "BUD", "SOF", "BEG"],
        tags=["romania", "poland", "hungary", "tarom"],
    ),
    DestItem(
        id="europe_south",
        label="Southern Europe / Mediterranean",
        description="Italy, Greece, Turkey, Canary Islands",
        destinations=["FCO", "NAP", "VCE", "BLQ", "FLR", "CTA", "PMO", "BRI", "TRN", "GOA",
                       "ATH", "IST", "TFN", "LPA", "ACE", "FUE"],
        tags=["italy", "greece", "turkey", "canaries"],
    ),
    DestItem(
        id="north_africa",
        label="North Africa",
        description="Morocco, Tunisia, Algeria",
        destinations=["TUN", "CMN", "RAK", "ALG", "ORN", "RBA", "TNG"],
        tags=["morocco", "tunisia", "algeria"],
    ),
    DestItem(
        id="sub_saharan_africa",
        label="Sub-Saharan Africa",
        description="AF Africa network via CDG + Kenya Airways",
        destinations=["DSS", "ABJ", "DLA", "BZV", "BKO", "COO", "CKY", "OUA", "NDJ",
                       "TNR", "CPT", "NBO", "JNB", "ACC", "DAR", "LOS"],
        tags=["africa", "kenya", "south africa"],
    ),
    DestItem(
        id="middle_east",
        label="Middle East",
        description="Saudia, MEA, Gulf states",
        destinations=["JED", "RUH", "BEY", "AMM", "DXB", "CAI", "DOH", "TLV"],
        tags=["saudi", "lebanon", "dubai", "qatar", "israel"],
    ),
    DestItem(
        id="asia_pacific",
        label="Asia Pacific",
        description="Korean Air, China Eastern, Vietnam Airlines, Garuda",
        destinations=["ICN", "NRT", "KIX", "PVG", "XMN", "HAN", "SGN", "CGK", "TPE",
                       "BKK", "SIN", "DEL"],
        tags=["korea", "japan", "china", "vietnam", "indonesia", "thailand"],
    ),
    DestItem(
        id="north_america",
        label="North America",
        description="Delta US hubs + Canada",
        destinations=["ATL", "DTW", "MSP", "SEA", "SLC", "BOS", "JFK", "LAX", "MIA", "YUL"],
        tags=["usa", "canada", "delta"],
    ),
    DestItem(
        id="latin_america",
        label="Latin America & Caribbean",
        description="Aeromexico, Aerolineas + KLM Caribbean",
        destinations=["MEX", "CUN", "BOG", "EZE", "GRU", "LIM", "CUR", "AUA", "SXM",
                       "BON", "PBM"],
        tags=["mexico", "brazil", "argentina", "caribbean", "curacao"],
    ),
    DestItem(
        id="french_overseas",
        label="French Overseas (DOM-TOM)",
        description="Huge XP! AMS-CDG-RUN = 102 XP RT",
        destinations=["FDF", "PTP", "CAY", "RUN"],
        tags=["martinique", "guadeloupe", "reunion", "cayenne"],
    ),
]

# ── Route Sets (existing groups, curated by airline/strategy) ──

ROUTE_SETS: list[DestItem] = [
    DestItem(
        id="french_via_cdg",
        label="French via CDG",
        description="AMS-CDG-French city: 15+6 XP per direction",
        destinations=["NCE", "MRS", "TLS", "LYS", "BOD", "NTE", "BIA", "AJA"],
        tags=["france", "cdg", "air france"],
    ),
    DestItem(
        id="french_small",
        label="French small airports",
        description="Max stops! Small French airports via CDG = 3+ segments",
        destinations=["MPL", "RNS", "LIL", "SXB", "CFE", "PGF", "EGC", "PUF", "RDZ", "AUR", "LRH", "DNR", "BVE"],
        tags=["france", "small", "multi-stop"],
    ),
    DestItem(
        id="scandinavia_sas",
        label="Scandinavia (SAS hubs)",
        description="SAS hubs + main cities via CPH/OSL/ARN",
        destinations=["CPH", "OSL", "ARN", "GOT", "BGO", "SVG", "TRD", "TOS", "MMX", "BLL", "AAL"],
        tags=["sas", "scandinavia"],
    ),
    DestItem(
        id="scandinavia_remote",
        label="Scandinavia remote",
        description="Max stops! Remote airports via CPH/OSL/ARN = 3+ segments",
        destinations=["LLA", "UME", "BOO", "AES", "EVE", "ALF", "KKN", "HAU", "MOL", "KSU", "FRO", "KRN", "OSD", "SDL", "VBY", "SFT", "FAE"],
        tags=["sas", "remote", "multi-stop"],
    ),
    DestItem(
        id="italy_via_cdg",
        label="Italy via CDG",
        description="Italian cities via CDG for multi-stop XP",
        destinations=["FCO", "NAP", "VCE", "BLQ", "FLR", "CTA", "PMO", "BRI", "TRN", "GOA"],
        tags=["italy", "cdg", "multi-stop"],
    ),
    DestItem(
        id="spain_air_europa",
        label="Spain (Air Europa)",
        description="AMS-MAD-Spanish domestic / Canary Islands",
        destinations=["MAD", "TFN", "LPA", "ACE", "FUE", "PMI", "IBZ", "AGP", "ALC", "VLC", "BIO", "SCQ", "SVQ"],
        tags=["spain", "air europa", "canaries"],
    ),
    DestItem(
        id="romania_tarom",
        label="Romania (TAROM)",
        description="AMS-OTP-Romanian domestic",
        destinations=["OTP", "CLJ", "TSR", "IAS", "SCV", "SOF", "BEG"],
        tags=["romania", "tarom"],
    ),
    DestItem(
        id="delta_us",
        label="Delta US hubs",
        description="Delta transatlantic + US domestic connections",
        destinations=["ATL", "DTW", "MSP", "SEA", "SLC", "BOS", "JFK", "LAX", "MIA"],
        tags=["delta", "usa"],
    ),
    DestItem(
        id="af_africa",
        label="AF Africa via CDG",
        description="Air France Africa network from CDG",
        destinations=["DSS", "ABJ", "DLA", "BZV", "BKO", "COO", "CKY", "OUA", "NDJ", "TNR", "CPT"],
        tags=["africa", "air france"],
    ),
    DestItem(
        id="klm_caribbean",
        label="KLM Caribbean",
        description="Dutch Caribbean + Suriname direct from AMS",
        destinations=["CUR", "AUA", "SXM", "BON", "PBM"],
        tags=["caribbean", "klm"],
    ),
]

# ── Community Favorites (famous XP runs from FlyerTalk/blogs) ──

FAVORITES: list[DestItem] = [
    DestItem(
        id="fav_antwerp_french",
        label="Antwerp Hack: French cities",
        description="ZWE-AMS-CDG-xxx: 3 segments/dir, often cheaper than AMS origin. ~90 XP RT biz",
        destinations=["NCE", "MRS", "TLS", "LYS", "TRN"],
        tags=["antwerp", "zwe", "hack", "flyertalk"],
    ),
    DestItem(
        id="fav_antwerp_africa",
        label="Antwerp Hack: North Africa",
        description="ZWE-AMS-CDG-TUN/RAK: 90 XP RT in business for ~EUR700-900",
        destinations=["TUN", "RAK", "CMN"],
        tags=["antwerp", "zwe", "north africa", "flyertalk"],
    ),
    DestItem(
        id="fav_turin_run",
        label="Turin XP Run",
        description="AMS-CDG-TRN: community favorite, often EUR619-700 for 90 XP RT. Best EUR/XP in Europe",
        destinations=["TRN"],
        tags=["turin", "flyertalk", "best value"],
    ),
    DestItem(
        id="fav_tunis_run",
        label="Tunis XP Run",
        description="AMS-CDG-TUN: 30 XP/dir (15+15), often EUR700-900 RT in business",
        destinations=["TUN"],
        tags=["tunis", "flyertalk", "north africa"],
    ),
    DestItem(
        id="fav_reunion_domtom",
        label="Reunion Island (DOM-TOM XP monster)",
        description="AMS-CDG-RUN: 51 XP per direction (15+36)! 102 XP RT in business",
        destinations=["RUN"],
        tags=["reunion", "dom-tom", "long haul", "max xp"],
    ),
    DestItem(
        id="fav_martinique",
        label="Martinique/Guadeloupe",
        description="AMS-CDG-FDF/PTP: ~90 XP RT, great for Caribbean + big XP",
        destinations=["FDF", "PTP"],
        tags=["caribbean", "dom-tom", "max xp"],
    ),
    DestItem(
        id="fav_scandinavia_multistop",
        label="Scandinavia multi-stop",
        description="AMS-CPH-OSL-TOS or AMS-ARN-LLA: 3+ segments, all SAS/FB earning",
        destinations=["TOS", "BOO", "AES", "EVE", "LLA", "ALF", "KKN"],
        tags=["sas", "multi-stop", "flyertalk"],
    ),
    DestItem(
        id="fav_nairobi_via_cdg",
        label="Nairobi via CDG",
        description="AMS-CDG-NBO: long-haul XP via CDG, Kenya Airways earns FB",
        destinations=["NBO"],
        tags=["kenya", "africa", "long haul"],
    ),
    DestItem(
        id="fav_new_york_delta",
        label="New York (Delta transatlantic)",
        description="AMS-JFK or CDG-JFK: 30 XP/dir long-haul, Delta earns FB",
        destinations=["JFK"],
        tags=["delta", "usa", "long haul"],
    ),
    DestItem(
        id="fav_korean_air_icn",
        label="Seoul (Korean Air)",
        description="AMS-ICN: 36 XP/dir (5000+ mi), Korean Air earns full FB XP",
        destinations=["ICN"],
        tags=["korean air", "asia", "max xp"],
    ),
    DestItem(
        id="fav_cheap_europe",
        label="Cheap European biz: the classics",
        description="Routes regularly found under EUR10/XP on FlyerTalk",
        destinations=["TRN", "TUN", "NCE", "MRS", "RAK", "CMN", "TLS"],
        tags=["cheap", "europe", "flyertalk", "best value"],
    ),
    DestItem(
        id="fav_krakow_grinder",
        label="Krakow Platinum Grinder",
        description="KRK-AMS-CDG-xxx: FlyerTalk's go-to for status runs. 90 XP RT, cheap J fares from KRK",
        destinations=["KRK"],
        tags=["krakow", "flyertalk", "status run", "off the beaten points"],
    ),
    DestItem(
        id="fav_double_hub",
        label="Double Hub Template (xxx-CDG-AMS-yyy)",
        description="FlyerTalk proven: depart cheap city via both CDG+AMS = 6 segments RT. Under EUR6/XP",
        destinations=["TRN", "KRK", "LIS", "BCN", "MRS", "NCE"],
        tags=["double hub", "flyertalk", "template", "best value"],
    ),
    DestItem(
        id="fav_saudia_hack",
        label="Saudia domestic stacking",
        description="JED-RUH + long-haul: Saudia domestic segments earn FB XP. 100+ XP possible",
        destinations=["JED", "RUH", "ICN", "CAI"],
        tags=["saudia", "hack", "middle east", "max xp"],
    ),
    DestItem(
        id="fav_seville_cheap",
        label="Seville: cheapest J fares",
        description="SVQ-CDG-TRN: Seville has the cheapest J departure fares in Europe. As low as EUR186 RT!",
        destinations=["SVQ"],
        tags=["seville", "spain", "cheapest", "flyertalk"],
    ),
    DestItem(
        id="fav_africa_longhaul",
        label="Africa long-haul via CDG",
        description="AMS-CDG-JNB/NBO/CPT: 90+ XP RT, AF network to South/East Africa",
        destinations=["JNB", "NBO", "CPT", "DSS"],
        tags=["africa", "long haul", "air france"],
    ),
    DestItem(
        id="fav_spain_canaries",
        label="Spain: Canary Islands via MAD",
        description="AMS-MAD-TFN/LPA: Air Europa via Madrid, 2 segments + domestic",
        destinations=["TFN", "LPA", "ACE", "FUE"],
        tags=["spain", "canaries", "air europa"],
    ),
]


def get_all_categories() -> list[dict]:
    """Return all destination categories for the picker API."""

    def _item_dict(item: DestItem) -> dict:
        return {
            "id": item.id,
            "label": item.label,
            "description": item.description,
            "destinations": item.destinations,
            "destination_names": {c: CITY_NAMES.get(c, c) for c in item.destinations},
            "tags": item.tags,
            "count": len(item.destinations),
        }

    return [
        {
            "id": "continents",
            "label": "Continents",
            "icon": "globe",
            "items": [_item_dict(i) for i in CONTINENTS],
        },
        {
            "id": "sets",
            "label": "Route Sets",
            "icon": "route",
            "items": [_item_dict(i) for i in ROUTE_SETS],
        },
        {
            "id": "favorites",
            "label": "XP Favorites",
            "icon": "star",
            "items": [_item_dict(i) for i in FAVORITES],
        },
    ]


def resolve_destinations(
    groups: list[str] | None = None,
    custom_codes: list[str] | None = None,
) -> list[str]:
    """Resolve selected group IDs + custom IATA codes into a flat destination list."""
    all_items = {i.id: i for i in CONTINENTS + ROUTE_SETS + FAVORITES}

    destinations: list[str] = []
    seen: set[str] = set()

    if groups:
        for gid in groups:
            item = all_items.get(gid)
            if item:
                for d in item.destinations:
                    if d not in seen:
                        destinations.append(d)
                        seen.add(d)

    if custom_codes:
        for code in custom_codes:
            c = code.strip().upper()
            if len(c) == 3 and c not in seen:
                destinations.append(c)
                seen.add(c)

    return destinations
