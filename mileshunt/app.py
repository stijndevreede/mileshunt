"""MilesHunt web server — FastAPI app serving the XP hunter UI and admin backend."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mileshunt.airports import CITY_NAMES
from mileshunt.db import (
    create_session, create_user, delete_session, delete_user,
    get_best_deals, get_search_stats, get_session_user, init_db,
    list_users, log_search, save_best_deals, verify_user,
)
from mileshunt.search import FlightDeal, search_route
from mileshunt.skyteam import DEST_GROUPS
from mileshunt.xp import BAND_LABELS, XP_TABLE

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="XP Hunt", version="2.0.0")


@app.on_event("startup")
def startup():
    init_db()


# ── API models ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    origin: str = "AMS"
    dest: str
    date: str
    return_date: str | None = None
    cabin: str = "business"


class HuntRequest(BaseModel):
    origin: str = "AMS"
    date: str
    return_date: str | None = None
    groups: list[str] | None = None
    cabin: str = "business"


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str
    is_admin: bool = False


# ── Helpers ─────────────────────────────────────────────────

def _get_admin(token: str | None):
    if not token:
        raise HTTPException(401, "Not authenticated")
    user = get_session_user(token)
    if not user:
        raise HTTPException(401, "Session expired")
    if not user["is_admin"]:
        raise HTTPException(403, "Admin access required")
    return user


def _get_user(token: str | None):
    """Validate any user session token."""
    if not token:
        raise HTTPException(401, "Not authenticated")
    user = get_session_user(token)
    if not user:
        raise HTTPException(401, "Session expired")
    return user


# ── Public API (no auth) ───────────────────────────────────

@app.get("/api/groups")
def api_groups():
    return [
        {
            "id": g.id,
            "label": g.label,
            "description": g.description,
            "destinations": g.destinations,
            "destination_names": {code: CITY_NAMES.get(code, code) for code in g.destinations},
            "default_on": g.default_on,
        }
        for g in DEST_GROUPS
    ]


@app.get("/api/xp-table")
def api_xp_table():
    return {"bands": BAND_LABELS, "table": XP_TABLE}


# ── User Auth ──────────────────────────────────────────────

@app.post("/api/login")
def user_login(req: LoginRequest):
    user = verify_user(req.email, req.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token = create_session(user["id"])
    return {"token": token, "user": {"email": user["email"], "name": user["name"], "is_admin": bool(user["is_admin"])}}


@app.post("/api/logout")
def user_logout(token: str | None = None):
    if token:
        delete_session(token)
    return {"ok": True}


@app.get("/api/me")
def api_me(token: str):
    user = _get_user(token)
    return {"email": user["email"], "name": user["name"], "is_admin": bool(user["is_admin"])}


# ── Search (auth required) ─────────────────────────────────

@app.post("/api/search")
def api_search(req: SearchRequest, request: Request, token: str):
    user = _get_user(token)
    t0 = time.time()
    deals = search_route(req.origin.upper(), req.dest.upper(), req.date, req.cabin, req.return_date)
    ms = int((time.time() - t0) * 1000)

    log_search(
        origin=req.origin.upper(),
        trip_type="return" if req.return_date else "oneway",
        cabin=req.cabin,
        outbound_date=req.date,
        return_date=req.return_date,
        groups=None,
        destinations_searched=1,
        results_found=len(deals),
        best_per_xp=deals[0].per_xp if deals else None,
        duration_ms=ms,
        user_email=user["email"],
        ip_address=request.client.host if request.client else None,
    )
    return {"deals": [d.to_dict() for d in deals], "count": len(deals)}


@app.post("/api/hunt/stream")
def api_hunt_stream(req: HuntRequest, request: Request, token: str):
    """SSE streaming hunt — sends progress events as each destination is searched."""
    user = _get_user(token)

    # Resolve destination list
    if req.groups:
        by_id = {g.id: g for g in DEST_GROUPS}
        groups = [by_id[gid] for gid in req.groups if gid in by_id]
    else:
        groups = [g for g in DEST_GROUPS if g.default_on]

    destinations: list[str] = []
    seen: set[str] = set()
    origin = req.origin.upper()
    for g in groups:
        for d in g.destinations:
            if d not in seen and d != origin:
                destinations.append(d)
                seen.add(d)

    def generate():
        t0 = time.time()
        # Track all unique deals, keyed for dedup
        unique: dict[str, FlightDeal] = {}
        total = len(destinations)
        sent_keys: set[str] = set()

        for i, dest in enumerate(destinations):
            city = CITY_NAMES.get(dest, dest)

            new_deals: list[dict] = []
            try:
                deals = search_route(origin, dest, req.date, req.cabin, req.return_date)
                for d in deals:
                    key = f"{d.route}_{d.return_route}_{d.price}"
                    if key not in unique:
                        unique[key] = d
                        if key not in sent_keys:
                            new_deals.append(d.to_dict())
                            sent_keys.add(key)
            except Exception as e:
                log.warning("Hunt %s>%s error: %s", origin, dest, e)

            # Send progress + any new deals found this round
            progress = {
                "type": "progress",
                "current": i + 1,
                "total": total,
                "route": f"{origin} > {city} ({dest})",
                "flights_found": len(unique),
                "new_deals": new_deals,
            }
            yield f"data: {json.dumps(progress)}\n\n"

        sorted_deals = sorted(unique.values(), key=lambda d: d.per_xp)
        ms = int((time.time() - t0) * 1000)

        # Log the search
        group_str = ",".join(req.groups) if req.groups else "defaults"
        log_search(
            origin=origin,
            trip_type="return" if req.return_date else "oneway",
            cabin=req.cabin,
            outbound_date=req.date,
            return_date=req.return_date,
            groups=group_str,
            destinations_searched=total,
            results_found=len(sorted_deals),
            best_per_xp=sorted_deals[0].per_xp if sorted_deals else None,
            duration_ms=ms,
            user_email=user["email"],
            ip_address=request.client.host if request.client else None,
        )

        # Save best deals to leaderboard
        if sorted_deals:
            save_best_deals(
                [d.to_dict() for d in sorted_deals],
                user["email"], req.cabin, req.date,
            )

        # Send done signal (no deals — frontend already has them all)
        result = {
            "type": "done",
            "count": len(sorted_deals),
            "best_per_xp": sorted_deals[0].per_xp if sorted_deals else None,
            "duration_ms": ms,
        }
        yield f"data: {json.dumps(result)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ── Best Deals Leaderboard ─────────────────────────────────

@app.get("/api/best-deals")
def api_best_deals(token: str):
    _get_user(token)
    return get_best_deals(10)


# ── Admin Auth ──────────────────────────────────────────────

@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    user = verify_user(req.email, req.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    if not user["is_admin"]:
        raise HTTPException(403, "Admin access required")
    token = create_session(user["id"])
    return {"token": token, "user": {"email": user["email"], "name": user["name"]}}


@app.post("/api/admin/logout")
def admin_logout(token: str | None = Cookie(None, alias="admin_token")):
    if token:
        delete_session(token)
    return {"ok": True}


@app.get("/api/admin/stats")
def admin_stats(token: str):
    _get_admin(token)
    return get_search_stats()


@app.get("/api/admin/users")
def admin_users(token: str):
    _get_admin(token)
    return list_users()


@app.post("/api/admin/users")
def admin_create_user(req: CreateUserRequest, token: str):
    _get_admin(token)
    try:
        user_id = create_user(req.email, req.name, req.password, req.is_admin)
    except Exception as e:
        raise HTTPException(400, f"Could not create user: {e}")
    return {"id": user_id, "email": req.email, "name": req.name}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, token: str):
    _get_admin(token)
    delete_user(user_id)
    return {"ok": True}


@app.get("/best")
def best_page():
    return FileResponse(
        str(STATIC_DIR / "best.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/admin")
def admin_page():
    return FileResponse(str(STATIC_DIR / "admin.html"))


# ── Static files & SPA fallback ────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(
        str(STATIC_DIR / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


def serve(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    serve()
