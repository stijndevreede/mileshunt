"""Flight search via the fli library (Google Flights)."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Callable

from fli.models import (
    Airport, FlightSearchFilters, FlightSegment, PassengerInfo,
    SeatType, SortBy, TripType,
)
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


SEAT_MAP = {
    "economy": SeatType.ECONOMY,
    "premium": SeatType.PREMIUM_ECONOMY,
    "business": SeatType.BUSINESS,
    "first": SeatType.FIRST,
}


@dataclass
class FlightDeal:
    origin: str
    dest: str
    route: str                  # "AMS > CDG > NCE"
    return_route: str | None    # "NCE > CDG > AMS" (round-trip only)
    trip_type: str              # "oneway" or "return"
    price: float
    currency: str
    outbound_segments: int
    return_segments: int
    total_segments: int
    xp_outbound: int
    xp_return: int
    xp_total: int
    per_xp: float               # price / xp_total
    duration: int               # outbound duration in minutes
    return_duration: int        # return duration (0 if one-way)
    airlines: list[str]         # IATA codes
    airline_names: list[str]    # display names
    all_fb: bool
    legs: list[dict]            # outbound legs
    return_legs: list[dict]     # return legs (empty if one-way)
    xp_breakdown: list[dict]    # outbound breakdown
    return_xp_breakdown: list[dict]  # return breakdown
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


def _parse_legs(flight) -> list[dict]:
    """Extract leg dicts from a fli FlightResult."""
    return [
        {
            "from": leg.departure_airport.name,
            "to": leg.arrival_airport.name,
            "airline": leg.airline.name,
            "flight_number": leg.flight_number,
            "departure": leg.departure_datetime.isoformat(),
            "arrival": leg.arrival_datetime.isoformat(),
            "duration": leg.duration,
        }
        for leg in flight.legs
    ]


def _xp_breakdown(xp_result: RouteXP) -> list[dict]:
    return [
        {"from": s.origin, "to": s.dest, "airline": s.airline,
         "band": s.band, "xp": s.xp, "earns_fb": s.earns_fb}
        for s in xp_result.segments
    ]


def _route_str(legs: list[dict]) -> str:
    if not legs:
        return ""
    return " > ".join([legs[0]["from"]] + [l["to"] for l in legs])


def search_route(
    origin: str,
    dest: str,
    date: str,
    cabin: str = "business",
    return_date: str | None = None,
) -> list[FlightDeal]:
    """Search flights and calculate XP for each result.

    If return_date is provided, searches round-trip flights.
    """
    seat = SEAT_MAP[cabin]
    is_rt = return_date is not None
    trip_type = TripType.ROUND_TRIP if is_rt else TripType.ONE_WAY

    segments = [
        FlightSegment(
            departure_airport=[[_airport(origin), 0]],
            arrival_airport=[[_airport(dest), 0]],
            travel_date=date,
        )
    ]
    if is_rt:
        segments.append(
            FlightSegment(
                departure_airport=[[_airport(dest), 0]],
                arrival_airport=[[_airport(origin), 0]],
                travel_date=return_date,
            )
        )

    import time as _time

    client = _client()

    # Search twice: cheapest (good prices) + duration-sorted (surfaces multi-stop)
    all_results = []
    for i, sort in enumerate([SortBy.CHEAPEST, SortBy.DURATION]):
        if i > 0:
            _time.sleep(1.5)  # rate limit pause between searches

        filters = FlightSearchFilters(
            trip_type=trip_type,
            passenger_info=PassengerInfo(adults=1),
            flight_segments=segments,
            seat_type=seat,
            sort_by=sort,
        )
        try:
            results = client.search(filters, top_n=8)
            if results:
                all_results.extend(results)
        except Exception as e:
            log.warning("Search %s>%s sort=%s failed: %s", origin, dest, sort, e)
            if "429" in str(e):
                _time.sleep(3)  # extra backoff on rate limit

    if not all_results:
        return []

    results = all_results

    deals: list[FlightDeal] = []

    if is_rt:
        # Round-trip: results are tuples of (outbound, return)
        for item in results:
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            out_flight, ret_flight = item

            out_legs = _parse_legs(out_flight)
            ret_legs = _parse_legs(ret_flight)

            out_xp = calc_route_xp(out_legs, cabin)
            ret_xp = calc_route_xp(ret_legs, cabin)

            all_airlines = list(dict.fromkeys(
                l["airline"] for l in out_legs + ret_legs
            ))
            total_xp = out_xp.total_xp + ret_xp.total_xp
            price = out_flight.price  # RT price is on the outbound
            per_xp = round(price / total_xp, 1) if total_xp > 0 else 999.0

            deals.append(FlightDeal(
                origin=origin,
                dest=dest,
                route=_route_str(out_legs),
                return_route=_route_str(ret_legs),
                trip_type="return",
                price=price,
                currency="EUR",
                outbound_segments=len(out_legs),
                return_segments=len(ret_legs),
                total_segments=len(out_legs) + len(ret_legs),
                xp_outbound=out_xp.total_xp,
                xp_return=ret_xp.total_xp,
                xp_total=total_xp,
                per_xp=per_xp,
                duration=out_flight.duration,
                return_duration=ret_flight.duration,
                airlines=all_airlines,
                airline_names=[AIRLINE_NAMES.get(c, c) for c in all_airlines],
                all_fb=(out_xp.non_fb_segments + ret_xp.non_fb_segments) == 0,
                legs=out_legs,
                return_legs=ret_legs,
                xp_breakdown=_xp_breakdown(out_xp),
                return_xp_breakdown=_xp_breakdown(ret_xp),
                rating=_rate(per_xp),
            ))
    else:
        # One-way
        for flight in results:
            legs = _parse_legs(flight)
            xp_result = calc_route_xp(legs, cabin)

            airline_codes = list(dict.fromkeys(l["airline"] for l in legs))
            xp_ow = xp_result.total_xp
            price = flight.price
            per_xp = round(price / xp_ow, 1) if xp_ow > 0 else 999.0

            deals.append(FlightDeal(
                origin=origin,
                dest=dest,
                route=_route_str(legs),
                return_route=None,
                trip_type="oneway",
                price=price,
                currency="EUR",
                outbound_segments=len(legs),
                return_segments=0,
                total_segments=len(legs),
                xp_outbound=xp_ow,
                xp_return=0,
                xp_total=xp_ow,
                per_xp=per_xp,
                duration=flight.duration,
                return_duration=0,
                airlines=airline_codes,
                airline_names=[AIRLINE_NAMES.get(c, c) for c in airline_codes],
                all_fb=xp_result.non_fb_segments == 0,
                legs=legs,
                return_legs=[],
                xp_breakdown=_xp_breakdown(xp_result),
                return_xp_breakdown=[],
                rating=_rate(per_xp),
            ))

    # Filter out price=0 (error) and 0 XP (non-FB carriers)
    deals = [d for d in deals if d.price > 0 and d.xp_total > 0]
    seen: dict[str, FlightDeal] = {}
    for d in deals:
        key = f"{d.route}_{d.return_route}_{d.price}"
        if key not in seen:
            seen[key] = d
    deals = sorted(seen.values(), key=lambda d: d.per_xp)
    return deals


def hunt(
    date: str,
    origin: str = "AMS",
    group_ids: list[str] | None = None,
    cabin: str = "business",
    return_date: str | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[FlightDeal]:
    """Search all destination groups and return deals sorted by $/XP."""
    groups: list[DestGroup]
    if group_ids:
        by_id = {g.id: g for g in DEST_GROUPS}
        groups = [by_id[gid] for gid in group_ids if gid in by_id]
    else:
        groups = [g for g in DEST_GROUPS if g.default_on]

    destinations: list[str] = []
    seen: set[str] = set()
    for g in groups:
        for d in g.destinations:
            if d not in seen and d != origin:
                destinations.append(d)
                seen.add(d)

    all_deals: list[FlightDeal] = []
    for i, dest in enumerate(destinations):
        city = CITY_NAMES.get(dest, dest)
        if on_progress:
            on_progress(f"{origin} > {city} ({dest})", i + 1, len(destinations))

        try:
            deals = search_route(origin, dest, date, cabin, return_date)
            all_deals.extend(deals)
        except Exception as e:
            log.warning("Hunt %s>%s error: %s", origin, dest, e)

    # Deduplicate by route+price
    unique: dict[str, FlightDeal] = {}
    for d in all_deals:
        key = f"{d.route}_{d.return_route}_{d.price}"
        if key not in unique:
            unique[key] = d

    return sorted(unique.values(), key=lambda d: d.per_xp)
