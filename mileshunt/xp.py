"""Flying Blue XP calculation engine.

XP is earned per flight segment based on distance band and cabin class.
More stopovers = more segments = more XP.
"""

from dataclasses import dataclass

from mileshunt.airports import FRENCH_DOMESTIC, distance_miles
from mileshunt.skyteam import FB_AIRLINES

# XP per segment by distance band and cabin
XP_TABLE: dict[str, dict[str, int]] = {
    "domestic":  {"economy": 2, "premium": 4,  "business": 6,  "first": 6},
    "medium":    {"economy": 5, "premium": 10, "business": 15, "first": 15},
    "long1":     {"economy": 8, "premium": 16, "business": 24, "first": 24},
    "long2":     {"economy": 10, "premium": 20, "business": 30, "first": 30},
    "long3":     {"economy": 12, "premium": 24, "business": 36, "first": 36},
}

BAND_LABELS = {
    "domestic": "Domestic FR",
    "medium": "<2 000 mi",
    "long1": "2 000–3 500 mi",
    "long2": "3 500–5 000 mi",
    "long3": "5 000+ mi",
}


def distance_band(origin: str, dest: str) -> str:
    """Classify a segment into a Flying Blue distance band."""
    if origin in FRENCH_DOMESTIC and dest in FRENCH_DOMESTIC:
        return "domestic"
    miles = distance_miles(origin, dest)
    if miles is None:
        return "medium"  # safe fallback for unknown airports
    if miles < 2000:
        return "medium"
    if miles < 3500:
        return "long1"
    if miles < 5000:
        return "long2"
    return "long3"


@dataclass
class SegmentXP:
    origin: str
    dest: str
    airline: str
    band: str
    xp: int
    earns_fb: bool


@dataclass
class RouteXP:
    segments: list[SegmentXP]
    total_xp: int
    fb_segments: int
    non_fb_segments: int


def calc_segment_xp(
    origin: str, dest: str, airline: str, cabin: str = "business",
) -> SegmentXP:
    """Calculate XP for a single flight segment."""
    earns_fb = airline in FB_AIRLINES
    band = distance_band(origin, dest)
    xp = XP_TABLE[band][cabin] if earns_fb else 0
    return SegmentXP(origin=origin, dest=dest, airline=airline, band=band, xp=xp, earns_fb=earns_fb)


def calc_route_xp(
    legs: list[dict], cabin: str = "business",
) -> RouteXP:
    """Calculate XP for a full route (list of leg dicts with 'from', 'to', 'airline')."""
    segments = []
    for leg in legs:
        seg = calc_segment_xp(leg["from"], leg["to"], leg["airline"], cabin)
        segments.append(seg)

    return RouteXP(
        segments=segments,
        total_xp=sum(s.xp for s in segments),
        fb_segments=sum(1 for s in segments if s.earns_fb),
        non_fb_segments=sum(1 for s in segments if not s.earns_fb),
    )
