"""MilesHunt web server — FastAPI app serving the XP hunter UI."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mileshunt.search import FlightDeal, hunt, search_route
from mileshunt.skyteam import DEST_GROUPS
from mileshunt.xp import BAND_LABELS, XP_TABLE

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="MilesHunt", version="1.0.0")


# ── API models ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    origin: str = "AMS"
    dest: str
    date: str
    cabin: str = "business"


class HuntRequest(BaseModel):
    origin: str = "AMS"
    date: str
    groups: list[str] | None = None
    cabin: str = "business"


# ── API routes ──────────────────────────────────────────────

@app.get("/api/groups")
def api_groups():
    """Return all destination groups."""
    return [
        {
            "id": g.id,
            "label": g.label,
            "description": g.description,
            "destinations": g.destinations,
            "default_on": g.default_on,
        }
        for g in DEST_GROUPS
    ]


@app.get("/api/xp-table")
def api_xp_table():
    """Return the XP reference table."""
    return {"bands": BAND_LABELS, "table": XP_TABLE}


@app.post("/api/search")
def api_search(req: SearchRequest):
    """Search a single route."""
    deals = search_route(req.origin.upper(), req.dest.upper(), req.date, req.cabin)
    return {"deals": [d.to_dict() for d in deals], "count": len(deals)}


@app.post("/api/hunt")
def api_hunt(req: HuntRequest):
    """Hunt across destination groups."""
    deals = hunt(req.date, req.origin.upper(), req.groups, req.cabin)
    return {
        "deals": [d.to_dict() for d in deals],
        "count": len(deals),
        "best_per_xp": deals[0].per_xp if deals else None,
    }


# ── Static files & SPA fallback ────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


def serve(host: str = "0.0.0.0", port: int = 8000):
    """Run the dev server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    serve()
