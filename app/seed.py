"""Başlanğıc məlumatlar: AYNA açıq API-sindən idxal olunmuş real Bakı marşrutları (app/data/ayna.json).

Hər marşrut qapalı dövrə kimi saxlanılır: 1-ci istiqamətin həndəsəsi + 2-ci istiqamətin həndəsəsi.
Dayanacaqlar öz istiqamətinin xətt hissəsinə proyeksiya olunur. Avtobuslar dövrə üzrə bərabər paylanır.
"""
from __future__ import annotations

import json
import os
import random

from .db import Database, to_iso, utcnow
from .services.geo import Polyline

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ayna.json")

PALETTE = ["#1d4ed8", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#be123c", "#4d7c0f",
           "#9333ea", "#0f766e", "#b45309", "#1e40af", "#c2410c", "#15803d", "#a21caf", "#334155"]

# Virtual sərnişin hesabatları yalnız bu "izlənən" xətlər üçün yaradılır (demo üçün pik meyli ilə)
MONITORED: dict[str, float] = {
    "1": 0.35, "5": 0.80, "65": 0.45, "88": 0.25, "2": 0.30, "3": 0.70, "6": 0.40,
    "18": 0.35, "61": 0.50, "125": 0.30, "14": 0.45, "35": 0.75,
}

PLATE_LETTERS = ["AA", "AB", "AC", "AD", "AE", "AH", "AK", "AL", "AM", "AN", "BA", "BB", "BC", "BD", "BE", "BH"]


def is_seeded(db: Database) -> bool:
    row = db.query_one("SELECT COUNT(*) AS c FROM routes")
    return bool(row and row["c"] > 0)


def load_ayna(path: str = DATA_FILE) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["routes"]


def _monotonic(positions: list[float], lo: float, hi: float) -> list[float]:
    """Proyeksiya ardıcıllığı pozularsa (paralel küçələr), mövqeləri artan sıraya salır."""
    out: list[float] = []
    for p in positions:
        p = max(lo, min(p, hi))
        if out and p <= out[-1]:
            p = min(out[-1] + 1.0, hi)
        out.append(p)
    return out


def build_route(raw: dict) -> dict | None:
    """AYNA qeydindən dövrə həndəsəsi və dayanacaq mövqeləri hazırlayır."""
    d1, d2 = raw["directions"].get("1") or raw["directions"].get(1) or {}, raw["directions"].get("2") or raw["directions"].get(2) or {}
    pts1 = [tuple(p) for p in d1.get("points") or []]
    pts2 = [tuple(p) for p in d2.get("points") or []]
    stops1, stops2 = d1.get("stops") or [], d2.get("stops") or []
    if not pts1 and stops1:
        pts1 = [(s["lat"], s["lon"]) for s in stops1]
    if not pts2:
        pts2 = list(reversed(pts1)) if not stops2 else [(s["lat"], s["lon"]) for s in stops2]
    if len(pts1) < 2 and len(pts2) < 2:
        return None
    loop_pts = pts1 + pts2 + [pts1[0]] if pts1 else pts2
    line = Polyline.from_points(loop_pts)
    len1 = Polyline.from_points(pts1).length_m if len(pts1) >= 2 else 0.0
    rs: list[tuple[int, str, int, float]] = []  # (seq, stop_id, direction, position)
    pos1 = _monotonic([line.project(s["lat"], s["lon"], 0.0, len1) for s in stops1], 0.0, len1)
    pos2 = _monotonic([line.project(s["lat"], s["lon"], len1, line.length_m) for s in stops2], len1, line.length_m)
    seq = 0
    for s, p in zip(stops1, pos1):
        rs.append((seq, f"s{s['id']}", 1, p)); seq += 1
    for s, p in zip(stops2, pos2):
        rs.append((seq, f"s{s['id']}", 2, p)); seq += 1
    duration = raw.get("duration_min") or 0
    avg_speed = 18.0
    if duration and line.length_m > 0:
        avg_speed = max(12.0, min(35.0, (line.length_m / 1000) / (2 * duration / 60)))
    return {"line": line, "route_stops": rs, "stops": stops1 + stops2, "duration_min": duration,
            "avg_speed_kmh": round(avg_speed, 1)}


def seed(db: Database, data_file: str = DATA_FILE, route_limit: int | None = None) -> None:
    """Boş bazanı AYNA məlumatı ilə doldurur. Artıq doludursa heç nə etmir."""
    if is_seeded(db):
        return
    routes = load_ayna(data_file)
    if route_limit:
        wanted = set(MONITORED)
        routes = [r for r in routes if r["number"] in wanted][:route_limit] or routes[:route_limit]
    rng = random.Random(42)
    now = to_iso(utcnow())
    with db.transaction() as conn:
        for idx, raw in enumerate(routes):
            built = build_route(raw)
            if built is None:
                continue
            rid = f"r{raw['id']}"
            number = raw["number"]
            name = f"{raw.get('first_point') or '?'} – {raw.get('last_point') or '?'}"
            monitored = number in MONITORED
            conn.execute(
                "INSERT INTO routes(id, number, name, carrier, color, peak_bias, monitored, length_m, duration_min, avg_speed_kmh) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (rid, number, name, raw.get("carrier"), PALETTE[idx % len(PALETTE)], MONITORED.get(number, 0.2),
                 int(monitored), built["line"].length_m, built["duration_min"], built["avg_speed_kmh"]),
            )
            conn.executemany("INSERT INTO route_points(route_id, seq, lat, lon) VALUES (?,?,?,?)",
                             [(rid, i, lat, lon) for i, (lat, lon) in enumerate(built["line"].points)])
            conn.executemany("INSERT OR IGNORE INTO stops(id, code, name, lat, lon) VALUES (?,?,?,?,?)",
                             [(f"s{s['id']}", s.get("code"), s["name"], s["lat"], s["lon"]) for s in built["stops"]])
            conn.executemany("INSERT INTO route_stops(route_id, seq, stop_id, direction, position_m) VALUES (?,?,?,?,?)",
                             [(rid, seq, sid, d, p) for seq, sid, d, p in built["route_stops"]])
            length = built["line"].length_m
            bus_count = max(3, min(10, round(length / 3500)))   # ≈ 3.5 km-dən bir avtobus → 10-12 dəq interval
            for k in range(bus_count):
                pos = length * (k + 0.5) / bus_count
                lat, lon = built["line"].point_at(pos)
                plate = f"{rng.randint(10, 99)}-{rng.choice(PLATE_LETTERS)}-{rng.randint(100, 999)}"
                conn.execute(
                    "INSERT INTO buses(id, route_id, plate, position_m, speed_kmh, lat, lon, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (f"{rid}-b{k + 1}", rid, plate, pos, built["avg_speed_kmh"], lat, lon, now),
                )
