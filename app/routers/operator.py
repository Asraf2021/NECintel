"""Operator modulu və analitika API: xətt üzrə yük, GPS göstəriciləri, xəbərdarlıqlar."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..db import to_iso, utcnow
from ..services.analytics import NO_DATA, detect_bunching
from .auth import require_role
from .common import load_dict, state


def operator_only(request: Request) -> dict:
    return require_role(request, "operator")

router = APIRouter(prefix="/api/operator", tags=["operator"], dependencies=[Depends(operator_only)])
SEVERITY = {"high": 0, "medium": 1, "low": 2, "no_data": 3}


@router.get("/lines")
def lines(request: Request, only_with_data: bool = Query(False)):
    """Hər xətt üçün yük səviyyəsi, hesabat mənbələri, GPS göstəriciləri və aktiv xəbərdarlıq."""
    st = state(request)
    now = utcnow()
    loads = st.engine.current_loads(now)
    alerts = st.engine.active_alerts()
    buses_by_route: dict[str, list[dict]] = {}
    for b in st.db.query("SELECT route_id, position_m, speed_kmh FROM buses"):
        buses_by_route.setdefault(b["route_id"], []).append(b)
    breakdown: dict[str, dict[str, int]] = {}
    for r in st.db.query(
            "SELECT route_id, source, COUNT(*) AS c FROM reports WHERE created_at>=? GROUP BY route_id, source",
            (to_iso(now - timedelta(minutes=st.settings.window_minutes)),)):
        breakdown.setdefault(r["route_id"], {})[r["source"]] = r["c"]
    out = []
    for route in st.db.query("SELECT * FROM routes"):
        rid = route["id"]
        load = loads.get(rid, NO_DATA)
        if only_with_data and load.level == "no_data":
            continue
        buses = buses_by_route.get(rid, [])
        positions = [b["position_m"] for b in buses]
        avg_speed = round(sum(b["speed_kmh"] for b in buses) / len(buses), 1) if buses else 0.0
        since = st.engine.high_since(rid, now) if load.level == "high" else None
        out.append({
            "id": rid,
            "number": route["number"],
            "name": route["name"],
            "carrier": route["carrier"],
            "color": route["color"],
            "monitored": bool(route["monitored"]),
            "length_m": round(route["length_m"]),
            "load": load_dict(load),
            "report_sources": breakdown.get(rid, {}),
            "bus_count": len(buses),
            "avg_speed_kmh": avg_speed,
            "bunching": detect_bunching(positions, route["length_m"]),
            "high_for_minutes": round((now - since).total_seconds() / 60, 1) if since else 0,
            "anomaly_threshold_minutes": st.settings.anomaly_minutes,
            "active_alert": alerts.get(rid),
        })
    out.sort(key=lambda l: (SEVERITY[l["load"]["level"]], -l["load"]["report_count"],
                            len(l["number"]) if l["number"].isdigit() else 9, l["number"]))
    return out


@router.get("/alerts")
def alerts(request: Request, status: str = Query("active", pattern="^(active|acknowledged|resolved|all)$"),
           limit: int = Query(50, ge=1, le=500)):
    st = state(request)
    if status == "all":
        rows = st.db.query("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    else:
        rows = st.db.query("SELECT * FROM alerts WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit))
    routes = {r["id"]: r for r in st.db.query("SELECT id, number, name, color FROM routes")}
    return [{**a, "route": routes.get(a["route_id"])} for a in rows]


@router.post("/alerts/{alert_id}/ack")
def acknowledge(alert_id: int, request: Request):
    st = state(request)
    row = st.engine.acknowledge(alert_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Xəbərdarlıq tapılmadı")
    return row


@router.get("/history/{route_id}")
def history(route_id: str, request: Request, minutes: int = Query(60, ge=1, le=24 * 60)):
    """Xəttin yük səviyyəsi tarixçəsi (sparkline üçün)."""
    st = state(request)
    if st.db.query_one("SELECT id FROM routes WHERE id=?", (route_id,)) is None:
        raise HTTPException(status_code=404, detail="Marşrut tapılmadı")
    since = to_iso(utcnow() - timedelta(minutes=minutes))
    return st.db.query(
        "SELECT ts, level, score, report_count FROM line_state WHERE route_id=? AND ts>=? ORDER BY ts",
        (route_id, since),
    )


@router.post("/evaluate")
def evaluate_now(request: Request):
    """Analitika mühərrikini dərhal işlədir (adi halda fon tapşırığı edir)."""
    st = state(request)
    return {"created_alerts": st.engine.evaluate()}


@router.post("/demo/high-load/{route_id}")
def demo_high_load(route_id: str, request: Request):
    """Demo: seçilmiş xətt üçün son 11 dəqiqəlik "Yüksək" yük ssenarisini simulyasiya edir."""
    st = state(request)
    if st.db.query_one("SELECT id FROM routes WHERE id=?", (route_id,)) is None:
        raise HTTPException(status_code=404, detail="Marşrut tapılmadı")
    return {"route_id": route_id, "created_alerts": st.engine.simulate_sustained_high(route_id)}
