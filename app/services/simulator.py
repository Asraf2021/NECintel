"""GPS simulyatoru.

Real sistemdə avtobus GPS cihazları koordinat göndərir. Prototipdə avtobuslar marşrut dövrəsi üzrə
hərəkət etdirilir; sürət xəttin yük səviyyəsinə görə azalır (yüksək yük → uzun dayanma).
Virtual sərnişin hesabatları yalnız "izlənən" xətlər üçün yaradılır (source='sim_passenger');
real sərnişin hesabatları source='passenger' ilə ayrılır.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from ..config import Settings
from ..db import Database, to_iso, utcnow
from .analytics import AnalyticsEngine
from .geo import Polyline

SPEED_FACTOR = {"high": 0.7, "medium": 0.88, "low": 1.0, "no_data": 1.0}
CRUISE_FACTOR = 1.3  # orta sürət dayanmaları daxil edir; hərəkətdə sürət bir qədər yüksəkdir


class GeometryCache:
    """Marşrut həndəsəsi yaddaşda saxlanır ki, hər tikdə baza oxunmasın."""

    def __init__(self, db: Database) -> None:
        self.lines: dict[str, Polyline] = {}
        self.stop_positions: dict[str, list[float]] = {}
        self.avg_speed: dict[str, float] = {}
        self.reload(db)

    def reload(self, db: Database) -> None:
        pts_by_route: dict[str, list[tuple[float, float]]] = {}
        for p in db.query("SELECT route_id, lat, lon FROM route_points ORDER BY route_id, seq"):
            pts_by_route.setdefault(p["route_id"], []).append((p["lat"], p["lon"]))
        stops_by_route: dict[str, list[float]] = {}
        for r in db.query("SELECT route_id, position_m FROM route_stops ORDER BY route_id, seq"):
            stops_by_route.setdefault(r["route_id"], []).append(r["position_m"])
        for route in db.query("SELECT id, avg_speed_kmh FROM routes"):
            self.lines[route["id"]] = Polyline.from_points(pts_by_route.get(route["id"], []))
            self.stop_positions[route["id"]] = stops_by_route.get(route["id"], [])
            self.avg_speed[route["id"]] = route["avg_speed_kmh"]


class GpsSimulator:
    def __init__(self, db: Database, settings: Settings, geometry: GeometryCache, engine: AnalyticsEngine,
                 rng: random.Random | None = None) -> None:
        self.db = db
        self.settings = settings
        self.geometry = geometry
        self.engine = engine
        self.rng = rng or random.Random()
        self._dwell_until: dict[str, datetime] = {}

    def tick(self, now: datetime | None = None, dt_seconds: float | None = None) -> int:
        """Bütün avtobusları bir addım irəlilədir. Qaytarır: yenilənən avtobus sayı."""
        now = now or utcnow()
        dt = dt_seconds if dt_seconds is not None else self.settings.tick_seconds
        levels = self.engine.latest_levels()
        updates = []
        for bus in self.db.query("SELECT id, route_id, position_m FROM buses"):
            line = self.geometry.lines.get(bus["route_id"])
            if line is None or line.length_m <= 0:
                continue
            if self._dwell_until.get(bus["id"], now) > now:
                continue  # dayanacaqda gözləyir
            level = levels.get(bus["route_id"], "no_data")
            speed = self.geometry.avg_speed[bus["route_id"]] * CRUISE_FACTOR * SPEED_FACTOR[level] * self.rng.uniform(0.9, 1.1)
            step = speed / 3.6 * dt
            pos = bus["position_m"]
            new_pos = (pos + step) % line.length_m
            # dayanacaq keçildi? → qısa dayanma
            for sp in self.geometry.stop_positions[bus["route_id"]]:
                passed = (pos < sp <= pos + step) or (pos + step >= line.length_m and sp <= new_pos)
                if passed:
                    extra = 1.6 if level == "high" else 1.0
                    self._dwell_until[bus["id"]] = now + timedelta(seconds=self.settings.dwell_seconds * extra)
                    break
            lat, lon = line.point_at(new_pos)
            updates.append((new_pos, round(speed, 1), lat, lon, to_iso(now), bus["id"]))
        if updates:
            self.db.executemany(
                "UPDATE buses SET position_m=?, speed_kmh=?, lat=?, lon=?, updated_at=? WHERE id=?", updates)
        return len(updates)

    def generate_reports(self, now: datetime | None = None, probability: float = 0.35) -> int:
        """Virtual sərnişinlər: izlənən hər xətt üçün müəyyən ehtimalla bir hesabat.

        Səviyyə paylanması marşrutun peak_bias dəyərindən asılıdır (0 → əsasən aşağı, 1 → əsasən yüksək).
        """
        now = now or utcnow()
        created = 0
        rows = []
        for route in self.db.query("SELECT id, peak_bias FROM routes WHERE monitored=1"):
            if self.rng.random() > probability:
                continue
            bias = route["peak_bias"]
            x = self.rng.random()
            level = "high" if x < bias else ("medium" if x < bias + (1 - bias) * 0.5 else "low")
            buses = self.db.query("SELECT id FROM buses WHERE route_id=?", (route["id"],))
            bus_id = self.rng.choice(buses)["id"] if buses else None
            rows.append((route["id"], bus_id, level, "sim_passenger", to_iso(now)))
            created += 1
        if rows:
            self.db.executemany("INSERT INTO reports(route_id, bus_id, level, source, created_at) VALUES (?,?,?,?,?)", rows)
        return created
