"""MilesHunt web server — FastAPI app serving the XP hunter UI and admin backend."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mileshunt.airports import CITY_NAMES
from mileshunt.db import (
    create_session, create_user, delete_session, delete_user,
    get_search_stats, get_session_user, init_db, list_users,
    log_search, verify_user,
)
from mileshunt.search import hunt, search_route
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
    """Validate admin session token, raise 401/403 if invalid."""
    if not token:
        raise HTTPException(401, "Not authenticated")
    user = get_session_user(token)
    if not user:
        raise HTTPException(401, "Session expired")
    if not user["is_admin"]:
        raise HTTPException(403, "Admin access required")
    return user


# ── Public API ──────────────────────────────────────────────

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


@app.post("/api/search")
def api_search(req: SearchRequest, request: Request):
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
        ip_address=request.client.host if request.client else None,
    )

    return {"deals": [d.to_dict() for d in deals], "count": len(deals)}


@app.post("/api/hunt")
def api_hunt(req: HuntRequest, request: Request):
    t0 = time.time()
    deals = hunt(req.date, req.origin.upper(), req.groups, req.cabin, req.return_date)
    ms = int((time.time() - t0) * 1000)

    group_str = ",".join(req.groups) if req.groups else "defaults"
    log_search(
        origin=req.origin.upper(),
        trip_type="return" if req.return_date else "oneway",
        cabin=req.cabin,
        outbound_date=req.date,
        return_date=req.return_date,
        groups=group_str,
        destinations_searched=len(set(d for g in DEST_GROUPS for d in g.destinations if not req.groups or g.id in req.groups)),
        results_found=len(deals),
        best_per_xp=deals[0].per_xp if deals else None,
        duration_ms=ms,
        ip_address=request.client.host if request.client else None,
    )

    return {
        "deals": [d.to_dict() for d in deals],
        "count": len(deals),
        "best_per_xp": deals[0].per_xp if deals else None,
    }


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


# ── Admin: Stats ────────────────────────────────────────────

@app.get("/api/admin/stats")
def admin_stats(token: str):
    _get_admin(token)
    return get_search_stats()


# ── Admin: Users ────────────────────────────────────────────

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


# ── Admin Page ──────────────────────────────────────────────

@app.get("/admin")
def admin_page():
    return FileResponse(str(STATIC_DIR / "admin.html"))


# ── Static files & SPA fallback ────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


def serve(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    serve()
