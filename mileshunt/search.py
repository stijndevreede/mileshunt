"""Flight search via the fli library (Google Flights)."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Callable

from fli.models import Airport, FlightSearchFilters, FlightSegment, PassengerInfo, SeatType, SortBy
from fli.search import SearchFlights

from mileshunt.airports import CITY_NAMES
from mileshunt.skyteam import AIRLINE_NAMES, DEST_GROUPS, DestGroup
from mileshunt.xp import RouteXP, calc_route_xp

log = logging.getLogger(__name__)

_search_client: SearchFlights | None = None


def _client() -> SearchFlights:
    global _search_client
    if _search_client is None:
        _search_client = SearchFlights()
    return _search_client


def _airport(code: str) -> Airport:
    """Convert IATA string to fli Airport enum."""
    try:
        return getattr(Airport, code)
    except AttributeError:
        raise ValueError(f"Unknown airport code: {code}")


@dataclass
class FlightDeal:
    origin: str
    dest: str
    route: str                  # "AMS > CDG > NCE"
    price: float
    currency: str
    segments: int
    xp: int                     # one-way XP
    xp_rt: int                  # estimated round-trip XP (2x)
    per_xp: float               # price / xp (one-way ratio)
    per_xp_rt: float            # price / xp_rt (if doing RT on same routing)
    duration: int               # minutes
    airlines: list[str]         # IATA codes
    airline_names: list[str]    # display names
    all_fb: bool
    legs: list[dict]
    xp_breakdown: list[dict]
    rating: str                 # EXCELLENT / GOOD / OK / EXPENSIVE

    def to_dict(self) -> dict:
        return asdict(self)


def _rate(per_xp: float) -> str:
    if per_xp <= 8:
        return "EXCELLENT"
    if per_xp <= 13:
        return "GOOD"
    if per_xp <= 20:
        return "OK"
    return "EXPENSIVE"


def search_route(
    origin: str,
    dest: str,
    date: str,
    cabin: str = "business",
) -> list[FlightDeal]:
    """Search one-way flights and calculate XP for each result."""
    seat = {"economy": SeatType.ECONOMY, "premium": SeatType.PREMIUM_ECONOMY,
            "business": SeatType.BUSINESS, "first": SeatType.FIRST}[cabin]

    filters = FlightSearchFilters(
        passenger_info=PassengerInfo(adults=1),
        flight_segments=[
            FlightSegment(
                departure_airport=[[_airport(origin), 0]],
                arrival_airport=[[_airport(dest), 0]],
                travel_date=date,
            )
        ],
        seat_type=seat,
        sort_by=SortBy.CHEAPEST,
    )

    client = _client()
    try:
        results = client.search(filters)
    except Exception as e:
        log.warning("Search %s>%s failed: %s", origin, dest, e)
        return []

    if not results:
        return []

    deals: list[FlightDeal] = []
    for flight in results:
        legs = []
        for leg in flight.legs:
            legs.append({
                "from": leg.departure_airport.name,
                "to": leg.arrival_airport.name,
                "airline": leg.airline.name,
                "flight_number": leg.flight_number,
                "departure": leg.departure_datetime.isoformat(),
                "arrival": leg.arrival_datetime.isoformat(),
                "duration": leg.duration,
            })

        xp_result: RouteXP = calc_route_xp(legs, cabin)

        airline_codes = list(dict.fromkeys(l["airline"] for l in legs))
        route_str = " > ".join([legs[0]["from"]] + [l["to"] for l in legs])

        xp_ow = xp_result.total_xp
        xp_rt = xp_ow * 2
        price = flight.price
        per_xp = round(price / xp_ow, 1) if xp_ow > 0 else 999.0
        per_xp_rt = round(price / xp_rt, 1) if xp_rt > 0 else 999.0

        deals.append(FlightDeal(
            origin=origin,
            dest=dest,
            route=route_str,
            price=price,
            currency="USD",
            segments=len(legs),
            xp=xp_ow,
            xp_rt=xp_rt,
            per_xp=per_xp,
            per_xp_rt=per_xp_rt,
            duration=flight.duration,
            airlines=airline_codes,
            airline_names=[AIRLINE_NAMES.get(c, c) for c in airline_codes],
            all_fb=xp_result.non_fb_segments == 0,
            legs=legs,
            xp_breakdown=[
                {"from": s.origin, "to": s.dest, "airline": s.airline,
                 "band": s.band, "xp": s.xp, "earns_fb": s.earns_fb}
                for s in xp_result.segments
            ],
            rating=_rate(per_xp),
        ))

    deals.sort(key=lambda d: d.per_xp)
    return deals


def hunt(
    date: str,
    origin: str = "AMS",
    group_ids: list[str] | None = None,
    cabin: str = "business",
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[FlightDeal]:
    """Search all destination groups and return deals sorted by $/XP.

    Args:
        date: Search date YYYY-MM-DD
        origin: Origin airport (default AMS)
        group_ids: Limit to specific group IDs, or None for all default-on groups
        cabin: Cabin class
        on_progress: Callback(route_label, current, total) for progress reporting
    """
    groups: list[DestGroup]
    if group_ids:
        by_id = {g.id: g for g in DEST_GROUPS}
        groups = [by_id[gid] for gid in group_ids if gid in by_id]
    else:
        groups = [g for g in DEST_GROUPS if g.default_on]

    # Build unique destination list
    destinations: list[str] = []
    seen: set[str] = set()
    for g in groups:
        for d in g.destinations:
            if d not in seen and d != origin:
                destinations.append(d)
                seen.add(d)

    all_deals: list[FlightDeal] = []
    for i, dest in enumerate(destinations):
        label = f"{origin}>{dest}"
        city = CITY_NAMES.get(dest, dest)
        if on_progress:
            on_progress(f"{origin} > {city} ({dest})", i + 1, len(destinations))

        try:
            deals = search_route(origin, dest, date, cabin)
            all_deals.extend(deals)
        except Exception as e:
            log.warning("Hunt %s>%s error: %s", origin, dest, e)

    # Deduplicate by route+price
    unique: dict[str, FlightDeal] = {}
    for d in all_deals:
        key = f"{d.route}_{d.price}"
        if key not in unique:
            unique[key] = d

    result = sorted(unique.values(), key=lambda d: d.per_xp)
    return result
