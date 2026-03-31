"""Flight search via the fli library (Google Flights) with extended parsing."""

from __future__ import annotations

import json
import logging
import time as _time
from dataclasses import asdict, dataclass
from datetime import datetime

from fli.models import (
    Airport, FlightSearchFilters, FlightSegment, PassengerInfo,
    SeatType, SortBy, TripType,
)
from fli.models.airline import Airline
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


def _airport_enum(code: str) -> Airport:
    try:
        return getattr(Airport, code)
    except AttributeError:
        raise ValueError(f"Unknown airport code: {code}")


def _parse_airport_code(code: str) -> str:
    try:
        return getattr(Airport, code).name
    except Exception:
        return code


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
    route: str
    return_route: str | None
    trip_type: str
    price: float
    currency: str
    outbound_segments: int
    return_segments: int
    total_segments: int
    xp_outbound: int
    xp_return: int
    xp_total: int
    per_xp: float
    duration: int
    return_duration: int
    airlines: list[str]
    airline_names: list[str]
    all_fb: bool
    legs: list[dict]
    return_legs: list[dict]
    xp_breakdown: list[dict]
    return_xp_breakdown: list[dict]
    rating: str

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


# ── Raw Google Flights parsing (extends fli to get aircraft type) ──

def _parse_raw_leg(fl: list) -> dict:
    """Parse a single leg from raw Google Flights data, including aircraft type."""
    airline_code = fl[22][0] if fl[22] else "??"
    # Normalize airline code (fli prepends _ for digit-starting codes)
    if airline_code and airline_code[0].isdigit():
        airline_code = f"_{airline_code}"
    try:
        airline_name = getattr(Airline, airline_code).name
    except AttributeError:
        airline_name = airline_code

    dep_airport = fl[3] or ""
    arr_airport = fl[6] or ""
    aircraft = fl[17] if len(fl) > 17 and isinstance(fl[17], str) else None

    dep_date = fl[20] if len(fl) > 20 else [2026, 1, 1]
    dep_time = fl[8] if len(fl) > 8 else [0, 0]
    arr_date = fl[21] if len(fl) > 21 else [2026, 1, 1]
    arr_time = fl[10] if len(fl) > 10 else [0, 0]

    def _dt(d, t):
        try:
            return datetime(*(x or 0 for x in d), *(x or 0 for x in t)).isoformat()
        except Exception:
            return ""

    return {
        "from": dep_airport,
        "to": arr_airport,
        "airline": airline_code.lstrip("_"),
        "flight_number": fl[22][1] if fl[22] else "",
        "departure": _dt(dep_date, dep_time),
        "arrival": _dt(arr_date, arr_time),
        "duration": fl[11] if len(fl) > 11 and fl[11] else 0,
        "aircraft": aircraft,
    }


def _parse_price(data: list) -> float:
    try:
        if data[1] and data[1][0]:
            return data[1][0][-1]
    except (IndexError, TypeError):
        pass
    return 0.0


def _raw_search(
    origin: str, dest: str, date: str, cabin: str, return_date: str | None,
) -> list[dict]:
    """Search Google Flights with raw parsing to get ALL results + aircraft type."""
    seat = SEAT_MAP[cabin]
    is_rt = return_date is not None

    segments = [
        FlightSegment(
            departure_airport=[[_airport_enum(origin), 0]],
            arrival_airport=[[_airport_enum(dest), 0]],
            travel_date=date,
        )
    ]
    if is_rt:
        segments.append(
            FlightSegment(
                departure_airport=[[_airport_enum(dest), 0]],
                arrival_airport=[[_airport_enum(origin), 0]],
                travel_date=return_date,
            )
        )

    filters = FlightSearchFilters(
        trip_type=TripType.ROUND_TRIP if is_rt else TripType.ONE_WAY,
        passenger_info=PassengerInfo(adults=1),
        flight_segments=segments,
        seat_type=seat,
        sort_by=SortBy.CHEAPEST,
    )

    client = _client()
    encoded = filters.encode()

    for attempt in range(3):
        try:
            resp = client.client.post(
                url=client.BASE_URL,
                data=f"f.req={encoded}",
                impersonate="chrome",
                allow_redirects=True,
            )
            resp.raise_for_status()
            break
        except Exception as e:
            log.warning("Raw search %s>%s attempt %d: %s", origin, dest, attempt + 1, e)
            if "429" in str(e):
                _time.sleep(4 * (attempt + 1))
            else:
                return []
    else:
        return []

    try:
        parsed = json.loads(resp.text.lstrip(")]}'"))
        if not parsed[0][2]:
            return []
        raw = json.loads(parsed[0][2])
    except Exception:
        return []

    # Collect ALL flights from both best and other
    all_raw_flights = []
    for idx in [2, 3]:
        if isinstance(raw[idx], list) and raw[idx] and isinstance(raw[idx][0], list):
            all_raw_flights.extend(raw[idx][0])

    results = []
    for flight_data in all_raw_flights:
        try:
            price = _parse_price(flight_data)
            raw_legs = flight_data[0][2]
            total_duration = flight_data[0][9] if flight_data[0][9] else 0
            stops = len(raw_legs) - 1

            legs = [_parse_raw_leg(fl) for fl in raw_legs]

            results.append({
                "legs": legs,
                "price": price,
                "duration": total_duration,
                "stops": stops,
            })
        except Exception as e:
            log.debug("Failed to parse flight: %s", e)

    return results


def _fetch_return_flights(
    origin: str, dest: str, date: str, return_date: str, cabin: str,
    outbound_flight: dict,
) -> list[dict]:
    """Fetch return flights for a specific outbound by passing selected_flight."""
    # For round-trip, we need to do a second search with the selected outbound
    # For simplicity, we'll use the standard fli approach for returns
    return []  # Return flights are handled via the RT search directly


# ── Public API ──────────────────────────────────────────────

def search_route(
    origin: str,
    dest: str,
    date: str,
    cabin: str = "business",
    return_date: str | None = None,
) -> list[FlightDeal]:
    """Search flights with extended parsing (aircraft type, all results)."""
    is_rt = return_date is not None

    if is_rt:
        # For round-trip, use fli's built-in RT search (handles outbound+return pairing)
        # but also do raw search to get aircraft types
        raw_results = _raw_search(origin, dest, date, cabin, return_date)
        # Build aircraft lookup from raw data
        aircraft_lookup: dict[str, str] = {}  # "airline_fn" -> aircraft
        for r in raw_results:
            for leg in r["legs"]:
                key = f"{leg['airline']}_{leg['flight_number']}"
                if leg.get("aircraft"):
                    aircraft_lookup[key] = leg["aircraft"]

        # Use fli for proper RT pairing
        seat = SEAT_MAP[cabin]
        segments = [
            FlightSegment(
                departure_airport=[[_airport_enum(origin), 0]],
                arrival_airport=[[_airport_enum(dest), 0]],
                travel_date=date,
            ),
            FlightSegment(
                departure_airport=[[_airport_enum(dest), 0]],
                arrival_airport=[[_airport_enum(origin), 0]],
                travel_date=return_date,
            ),
        ]
        filters = FlightSearchFilters(
            trip_type=TripType.ROUND_TRIP,
            passenger_info=PassengerInfo(adults=1),
            flight_segments=segments,
            seat_type=seat,
            sort_by=SortBy.CHEAPEST,
        )
        client = _client()
        try:
            results = client.search(filters, top_n=15)
        except Exception as e:
            log.warning("RT search %s>%s failed: %s", origin, dest, e)
            results = None

        if not results:
            return []

        deals: list[FlightDeal] = []
        for item in results:
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            out_flight, ret_flight = item

            out_legs = _parse_fli_legs(out_flight, aircraft_lookup)
            ret_legs = _parse_fli_legs(ret_flight, aircraft_lookup)

            deal = _build_deal(origin, dest, "return", out_legs, ret_legs,
                               out_flight.price, out_flight.duration,
                               ret_flight.duration, cabin)
            if deal:
                deals.append(deal)

    else:
        # One-way: use raw search for all results + aircraft type
        raw_results = _raw_search(origin, dest, date, cabin, None)

        deals = []
        for r in raw_results:
            deal = _build_deal(origin, dest, "oneway", r["legs"], [],
                               r["price"], r["duration"], 0, cabin)
            if deal:
                deals.append(deal)

    # Filter and deduplicate
    deals = [d for d in deals if d.price > 0 and d.xp_total > 0]
    seen: dict[str, FlightDeal] = {}
    for d in deals:
        key = f"{d.route}_{d.return_route}_{d.price}"
        if key not in seen:
            seen[key] = d
    return sorted(seen.values(), key=lambda d: d.per_xp)


def _parse_fli_legs(flight, aircraft_lookup: dict[str, str]) -> list[dict]:
    """Parse legs from a fli FlightResult, enriching with aircraft type."""
    legs = []
    for leg in flight.legs:
        airline = leg.airline.name
        fn = leg.flight_number
        ac_key = f"{airline}_{fn}"
        legs.append({
            "from": leg.departure_airport.name,
            "to": leg.arrival_airport.name,
            "airline": airline,
            "flight_number": fn,
            "departure": leg.departure_datetime.isoformat(),
            "arrival": leg.arrival_datetime.isoformat(),
            "duration": leg.duration,
            "aircraft": aircraft_lookup.get(ac_key),
        })
    return legs


def _build_deal(
    origin: str, dest: str, trip_type: str,
    out_legs: list[dict], ret_legs: list[dict],
    price: float, out_duration: int, ret_duration: int,
    cabin: str,
) -> FlightDeal | None:
    """Build a FlightDeal from parsed legs."""
    if not out_legs:
        return None

    out_xp = calc_route_xp(out_legs, cabin)
    ret_xp = calc_route_xp(ret_legs, cabin) if ret_legs else None

    xp_outbound = out_xp.total_xp
    xp_return = ret_xp.total_xp if ret_xp else 0
    xp_total = xp_outbound + xp_return

    all_legs = out_legs + ret_legs
    airline_codes = list(dict.fromkeys(l["airline"] for l in all_legs))
    per_xp = round(price / xp_total, 1) if xp_total > 0 else 999.0
    non_fb = (out_xp.non_fb_segments + (ret_xp.non_fb_segments if ret_xp else 0))

    return FlightDeal(
        origin=origin,
        dest=dest,
        route=_route_str(out_legs),
        return_route=_route_str(ret_legs) if ret_legs else None,
        trip_type=trip_type,
        price=price,
        currency="EUR",
        outbound_segments=len(out_legs),
        return_segments=len(ret_legs),
        total_segments=len(all_legs),
        xp_outbound=xp_outbound,
        xp_return=xp_return,
        xp_total=xp_total,
        per_xp=per_xp,
        duration=out_duration,
        return_duration=ret_duration,
        airlines=airline_codes,
        airline_names=[AIRLINE_NAMES.get(c, c) for c in airline_codes],
        all_fb=non_fb == 0,
        legs=out_legs,
        return_legs=ret_legs,
        xp_breakdown=_xp_breakdown(out_xp),
        return_xp_breakdown=_xp_breakdown(ret_xp) if ret_xp else [],
        rating=_rate(per_xp),
    )


def hunt(
    date: str,
    origin: str = "AMS",
    group_ids: list[str] | None = None,
    cabin: str = "business",
    return_date: str | None = None,
    on_progress=None,
) -> list[FlightDeal]:
    """Search all destination groups and return deals sorted by EUR/XP."""
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

    unique: dict[str, FlightDeal] = {}
    for d in all_deals:
        key = f"{d.route}_{d.return_route}_{d.price}"
        if key not in unique:
            unique[key] = d

    return sorted(unique.values(), key=lambda d: d.per_xp)
