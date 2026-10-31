"""Sərnişin modulu API: marşrutlar, dayanacaqlar, canlı avtobus mövqeyi, ETA, səyahət planı, yük hesabatı."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from ..db import to_iso, utcnow
from ..schemas import ReportIn, ReportOut
from ..services import eta as eta_service
from ..services.analytics import NO_DATA
from ..services.planner import TripPlanner
from .auth import require_user
from .common import load_dict, state

router = APIRouter(prefix="/api", tags=["passenger"])

ROUTE_COLS = "id, number, name, carrier, color, length_m, duration_min, avg_speed_kmh, monitored"


def _route_stops(db, route_id: str) -> list[dict]:
    return db.query(
        "SELECT s.id, s.code, s.name, s.lat, s.lon, rs.seq, rs.direction, rs.position_m FROM route_stops rs "
        "JOIN stops s ON s.id = rs.stop_id WHERE rs.route_id=? ORDER BY rs.seq",
        (route_id,),
    )


def _next_stop(stops: list[dict], position_m: float, length_m: float) -> dict | None:
    if not stops:
        return None
    return min(stops, key=lambda s: eta_service.distance_ahead(position_m, s["position_m"], length_m) or length_m)


def _bus_dict(bus: dict, route: dict, stops: list[dict], load_level: str) -> dict:
    nxt = _next_stop(stops, bus["position_m"], route["length_m"])
    return {
        "id": bus["id"],
        "plate": bus["plate"],
        "label": f"{route['number']} · {bus['plate']}",
        "route_id": bus["route_id"],
        "route_number": route["number"],
        "route_color": route["color"],
        "lat": round(bus["lat"], 6),
        "lon": round(bus["lon"], 6),
        "speed_kmh": bus["speed_kmh"],
        "position_m": round(bus["position_m"], 1),
        "direction": nxt["direction"] if nxt else 1,
        "next_stop": nxt["name"] if nxt else None,
        "load_level": load_level,
        "updated_at": bus["updated_at"],
    }


@router.get("/routes")
def list_routes(request: Request, q: str | None = Query(None, description="Nömrə və ya ad üzrə axtarış")):
    st = state(request)
    loads = st.engine.current_loads()
    rows = st.db.query(f"SELECT {ROUTE_COLS} FROM routes")
    if q:
        ql = q.strip().lower()
        rows = [r for r in rows if r["number"].lower().startswith(ql) or ql in r["name"].lower()]
    rows.sort(key=lambda r: (len(r["number"]) if r["number"].isdigit() else 9, r["number"]))
    return [{**r, "load": load_dict(loads.get(r["id"], NO_DATA))} for r in rows]


@router.get("/routes/{route_id}")
def get_route(route_id: str, request: Request):
    st = state(request)
    route = st.db.query_one(f"SELECT {ROUTE_COLS} FROM routes WHERE id=?", (route_id,))
    if route is None:
        raise HTTPException(status_code=404, detail="Marşrut tapılmadı")
    stops = _route_stops(st.db, route_id)
    load = st.engine.current_load(route_id)
    pts = st.db.query("SELECT lat, lon FROM route_points WHERE route_id=? ORDER BY seq", (route_id,))
    buses = st.db.query("SELECT * FROM buses WHERE route_id=?", (route_id,))
    return {
        **route,
        "stops": stops,
        "polyline": [[p["lat"], p["lon"]] for p in pts],
        "buses": [_bus_dict(b, route, stops, load.level) for b in buses],
        "load": load_dict(load),
    }


@router.get("/routes/{route_id}/timeline")
def route_timeline(route_id: str, request: Request):
    """Marşrutun hər dayanacağı üçün növbəti avtobusun gəliş vaxtı (istiqamətlər üzrə)."""
    st = state(request)
    route = st.db.query_one(f"SELECT {ROUTE_COLS} FROM routes WHERE id=?", (route_id,))
    if route is None:
        raise HTTPException(status_code=404, detail="Marşrut tapılmadı")
    stops = _route_stops(st.db, route_id)
    buses = st.db.query("SELECT id, plate, position_m FROM buses WHERE route_id=?", (route_id,))
    out = []
    prev_pos = None
    for s in stops:
        best = None
        for b in buses:
            secs = eta_service.travel_seconds(
                eta_service.distance_ahead(b["position_m"], s["position_m"], route["length_m"]), route["avg_speed_kmh"])
            if best is None or secs < best["eta_seconds"]:
                best = {"bus_id": b["id"], "plate": b["plate"], "eta_seconds": secs}
        leg = 0 if prev_pos is None or s["direction"] != prev_dir else eta_service.travel_seconds(
            s["position_m"] - prev_pos, route["avg_speed_kmh"])
        out.append({**s, "next_bus": best, "leg_seconds": leg})
        prev_pos, prev_dir = s["position_m"], s["direction"]
    return {"route": route, "stops": out, "generated_at": to_iso(utcnow())}


@router.get("/buses/{bus_id}/timeline")
def bus_timeline(bus_id: str, request: Request):
    """Konkret avtobusun marşrut üzrə hər dayanacağa gəliş vaxtı (cari mövqedən irəli, dövrə sırası ilə)."""
    st = state(request)
    bus = st.db.query_one("SELECT * FROM buses WHERE id=?", (bus_id,))
    if bus is None:
        raise HTTPException(status_code=404, detail="Avtobus tapılmadı")
    route = st.db.query_one(f"SELECT {ROUTE_COLS} FROM routes WHERE id=?", (bus["route_id"],))
    stops = _route_stops(st.db, bus["route_id"])
    out = []
    for s in stops:
        dist = eta_service.distance_ahead(bus["position_m"], s["position_m"], route["length_m"])
        out.append({**s, "distance_m": round(dist), "eta_seconds": eta_service.travel_seconds(dist, route["avg_speed_kmh"])})
    out.sort(key=lambda s: s["eta_seconds"])
    load = st.engine.current_load(bus["route_id"])
    return {"bus": _bus_dict(bus, route, stops, load.level), "route": route, "stops": out, "generated_at": to_iso(utcnow())}


@router.get("/stops")
def list_stops(request: Request, q: str | None = Query(None, min_length=1), limit: int = Query(30, ge=1, le=200)):
    """Dayanacaq axtarışı (ad üzrə). q verilməzsə ilk `limit` dayanacaq."""
    st = state(request)
    if q:
        rows = st.db.query("SELECT * FROM stops WHERE lower(name) LIKE ? ORDER BY name LIMIT ?",
                           (f"%{q.strip().lower()}%", limit))
    else:
        rows = st.db.query("SELECT * FROM stops ORDER BY name LIMIT ?", (limit,))
    ids = [r["id"] for r in rows]
    links: dict[str, list[dict]] = {}
    if ids:
        marks = ",".join("?" * len(ids))
        for l in st.db.query(
                f"SELECT DISTINCT rs.stop_id, r.id AS route_id, r.number FROM route_stops rs JOIN routes r ON r.id=rs.route_id "
                f"WHERE rs.stop_id IN ({marks})", ids):
            links.setdefault(l["stop_id"], []).append({"route_id": l["route_id"], "number": l["number"]})
    return [{**s, "routes": links.get(s["id"], [])} for s in rows]


@router.get("/stops/nearest")
def nearest_stops(request: Request, lat: float = Query(...), lon: float = Query(...), limit: int = Query(5, ge=1, le=20)):
    """Verilmiş koordinata ən yaxın dayanacaqlar (adlar unikal, keçən marşrutlarla)."""
    st = state(request)
    from ..services.geo import haversine_m
    rows = st.db.query("SELECT id, name, lat, lon FROM stops")
    for r in rows:
        r["distance_m"] = round(haversine_m(lat, lon, r["lat"], r["lon"]))
    rows.sort(key=lambda r: r["distance_m"])
    out, seen = [], set()
    for r in rows:
        if r["name"] in seen:
            continue
        seen.add(r["name"])
        out.append(r)
        if len(out) >= limit:
            break
    ids = [r["id"] for r in out]
    links: dict[str, list[str]] = {}
    if ids:
        marks = ",".join("?" * len(ids))
        for l in st.db.query(f"SELECT DISTINCT rs.stop_id, r.number FROM route_stops rs JOIN routes r ON r.id=rs.route_id "
                             f"WHERE rs.stop_id IN ({marks})", ids):
            links.setdefault(l["stop_id"], []).append(l["number"])
    return [{**r, "routes": sorted(links.get(r["id"], []), key=lambda n: (len(n), n))} for r in out]


@router.get("/stops/names")
def stop_names(request: Request):
    """Bütün unikal dayanacaq adları (axtarış sahəsi üçün)."""
    st = state(request)
    return [r["name"] for r in st.db.query("SELECT DISTINCT name FROM stops ORDER BY name")]


@router.get("/buses")
def list_buses(request: Request, route_id: str | None = Query(None)):
    st = state(request)
    routes = {r["id"]: r for r in st.db.query(f"SELECT {ROUTE_COLS} FROM routes")}
    if route_id is not None and route_id not in routes:
        raise HTTPException(status_code=404, detail="Marşrut tapılmadı")
    buses = st.db.query("SELECT * FROM buses WHERE route_id=?", (route_id,)) if route_id else st.db.query("SELECT * FROM buses")
    loads = st.engine.current_loads()
    stops_cache: dict[str, list[dict]] = {}
    out = []
    for b in buses:
        rid = b["route_id"]
        if rid not in stops_cache:
            stops_cache[rid] = _route_stops(st.db, rid)
        out.append(_bus_dict(b, routes[rid], stops_cache[rid], loads.get(rid, NO_DATA).level))
    return out


@router.get("/eta")
def eta(request: Request, stop_id: str = Query(...), route_id: str | None = Query(None), per_route: int = Query(2, ge=1, le=5)):
    """Seçilmiş dayanacağa yaxınlaşan avtobuslar və gözlənilən gəliş vaxtı."""
    st = state(request)
    stop = st.db.query_one("SELECT * FROM stops WHERE id=?", (stop_id,))
    if stop is None:
        raise HTTPException(status_code=404, detail="Dayanacaq tapılmadı")
    links = st.db.query(
        "SELECT rs.route_id, rs.position_m, rs.direction, r.number, r.color, r.name, r.length_m, r.avg_speed_kmh "
        "FROM route_stops rs JOIN routes r ON r.id=rs.route_id WHERE rs.stop_id=?",
        (stop_id,),
    )
    if route_id:
        links = [l for l in links if l["route_id"] == route_id]
        if not links:
            raise HTTPException(status_code=404, detail="Bu marşrut bu dayanacaqdan keçmir")
    loads = st.engine.current_loads()
    arrivals = []
    for link in links:
        rid = link["route_id"]
        stop_positions = st.geometry.stop_positions[rid]
        per = []
        for bus in st.db.query("SELECT * FROM buses WHERE route_id=?", (rid,)):
            res = eta_service.estimate(bus["position_m"], link["position_m"], link["length_m"], stop_positions,
                                       link["avg_speed_kmh"])
            per.append({
                "bus_id": bus["id"],
                "plate": bus["plate"],
                "label": f"{link['number']} · {bus['plate']}",
                "route_id": rid,
                "route_number": link["number"],
                "route_name": link["name"],
                "route_color": link["color"],
                "direction": link["direction"],
                "eta_seconds": res.eta_seconds,
                "eta_minutes": round(res.eta_seconds / 60, 1),
                "distance_m": res.distance_m,
                "stops_between": res.stops_between,
                "load_level": loads.get(rid, NO_DATA).level,
                "lat": round(bus["lat"], 6),
                "lon": round(bus["lon"], 6),
            })
        per.sort(key=lambda a: a["eta_seconds"])
        arrivals.extend(per[:per_route])
    arrivals.sort(key=lambda a: a["eta_seconds"])
    return {"stop": stop, "generated_at": to_iso(utcnow()), "arrivals": arrivals}


@router.get("/trip")
def trip(request: Request, from_name: str = Query(..., min_length=1), to_name: str = Query(..., min_length=1),
         limit: int = Query(3, ge=1, le=10)):
    """Haradan–hara: birbaşa və bir köçürməli ən yaxşı variantlar (gözləmə + yol, hər dayanacağa vaxt)."""
    st = state(request)
    if from_name.strip().lower() == to_name.strip().lower():
        raise HTTPException(status_code=422, detail="Başlanğıc və son dayanacaq eyni ola bilməz")
    known = {r["name"].lower() for r in st.db.query("SELECT name FROM stops WHERE lower(name) IN (?, ?)",
                                                      (from_name.strip().lower(), to_name.strip().lower()))}
    if from_name.strip().lower() not in known or to_name.strip().lower() not in known:
        raise HTTPException(status_code=404, detail="Dayanacaq tapılmadı")
    loads = st.engine.current_loads()
    options = TripPlanner(st.db).plan(from_name, to_name, limit)
    for o in options:
        for leg in o["legs"]:
            leg["load"] = load_dict(loads.get(leg["route_id"], NO_DATA))
    return {"from_name": from_name, "to_name": to_name, "generated_at": to_iso(utcnow()), "options": options}


@router.post("/reports", status_code=status.HTTP_201_CREATED, response_model=ReportOut)
def create_report(body: ReportIn, request: Request):
    """Sərnişin yük hesabatı: low | medium | high. Giriş tələb olunur."""
    st = state(request)
    user = require_user(request)
    route = st.db.query_one("SELECT id FROM routes WHERE id=?", (body.route_id,))
    if route is None:
        raise HTTPException(status_code=404, detail="Marşrut tapılmadı")
    if body.bus_id:
        bus = st.db.query_one("SELECT id FROM buses WHERE id=? AND route_id=?", (body.bus_id, body.route_id))
        if bus is None:
            raise HTTPException(status_code=422, detail="Avtobus bu marşruta aid deyil")
    if body.stop_id:
        stop = st.db.query_one("SELECT stop_id FROM route_stops WHERE stop_id=? AND route_id=?",
                               (body.stop_id, body.route_id))
        if stop is None:
            raise HTTPException(status_code=422, detail="Dayanacaq bu marşruta aid deyil")
    now = utcnow()
    cur = st.db.execute(
        "INSERT INTO reports(route_id, bus_id, stop_id, user_id, level, source, created_at) VALUES (?,?,?,?,?,'passenger',?)",
        (body.route_id, body.bus_id, body.stop_id, user["id"], body.level, to_iso(now)),
    )
    row = st.db.query_one("SELECT * FROM reports WHERE id=?", (cur.lastrowid,))
    return {**row, "line_load": load_dict(st.engine.current_load(body.route_id, now))}


@router.get("/reports/recent")
def recent_reports(request: Request, route_id: str | None = Query(None), source: str | None = Query(None),
                   limit: int = Query(20, ge=1, le=200)):
    st = state(request)
    sql = ("SELECT rep.*, r.number AS route_number, r.color AS route_color, s.name AS stop_name, b.plate "
           "FROM reports rep JOIN routes r ON r.id=rep.route_id LEFT JOIN stops s ON s.id=rep.stop_id "
           "LEFT JOIN buses b ON b.id=rep.bus_id WHERE 1=1")
    params: list = []
    if route_id:
        sql += " AND rep.route_id=?"; params.append(route_id)
    if source:
        sql += " AND rep.source=?"; params.append(source)
    sql += " ORDER BY rep.id DESC LIMIT ?"; params.append(limit)
    return st.db.query(sql, params)
