"""Səyahət planlayıcısı: haradan → hara, birbaşa və bir köçürməli variantlar (Google Maps üslubunda top-3).

Dayanacaqlar adına görə eyniləşdirilir (küçənin iki tərəfi eyni dayanacaq sayılır).
Hər variant üçün: gözləmə (ən yaxın avtobusun real ETA-sı), yol vaxtı, köçürmədə gözləmə, ara dayanacaqlar və
hər dayanacağa kumulyativ vaxt.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..db import Database
from . import eta as eta_service

TRANSFER_WALK_SECONDS = 180


@dataclass
class RouteInfo:
    id: str
    number: str
    name: str
    color: str
    length_m: float
    avg_speed_kmh: float
    stops: list[dict] = field(default_factory=list)       # seq sırası ilə
    buses: list[dict] = field(default_factory=list)

    def headway_seconds(self) -> int:
        n = max(1, len(self.buses))
        return eta_service.travel_seconds(self.length_m / n, self.avg_speed_kmh)

    def next_bus(self, position_m: float, not_before: int = 0) -> dict:
        """position_m mövqeyinə `not_before` saniyədən sonra ilk gələn avtobus (ETA saniyə ilə)."""
        etas = sorted(
            (eta_service.travel_seconds(eta_service.distance_ahead(b["position_m"], position_m, self.length_m), self.avg_speed_kmh), b)
            for b in self.buses)
        if not etas:
            return {"bus_id": None, "plate": None, "eta_seconds": not_before}
        for secs, b in etas:
            if secs >= not_before:
                return {"bus_id": b["id"], "plate": b["plate"], "eta_seconds": secs}
        secs, b = etas[0]                       # hamısı keçib: növbəti dövrələr (interval qədər sonra)
        headway = max(60, self.headway_seconds())
        while secs < not_before:
            secs += headway
        return {"bus_id": b["id"], "plate": b["plate"], "eta_seconds": secs}


class TripPlanner:
    def __init__(self, db: Database) -> None:
        self.db = db

    def _load(self) -> tuple[dict[str, RouteInfo], dict[str, list[tuple[str, int]]]]:
        routes = {r["id"]: RouteInfo(r["id"], r["number"], r["name"], r["color"], r["length_m"], r["avg_speed_kmh"])
                  for r in self.db.query("SELECT id, number, name, color, length_m, avg_speed_kmh FROM routes")}
        by_name: dict[str, list[tuple[str, int]]] = {}
        for row in self.db.query(
                "SELECT rs.route_id, rs.seq, rs.direction, rs.position_m, s.id AS stop_id, s.name, s.lat, s.lon "
                "FROM route_stops rs JOIN stops s ON s.id=rs.stop_id ORDER BY rs.route_id, rs.seq"):
            r = routes.get(row["route_id"])
            if r is None:
                continue
            row["key"] = row["name"].strip().lower()
            r.stops.append(row)
            by_name.setdefault(row["key"], []).append((r.id, len(r.stops) - 1))
        for b in self.db.query("SELECT id, route_id, plate, position_m FROM buses"):
            if b["route_id"] in routes:
                routes[b["route_id"]].buses.append(b)
        return routes, by_name

    @staticmethod
    def _leg(route: RouteInfo, i: int, j: int, depart_after: int) -> dict:
        """route.stops[i] → route.stops[j] (eyni istiqamət, i < j)."""
        a, b = route.stops[i], route.stops[j]
        wait = route.next_bus(a["position_m"], depart_after)
        dist = b["position_m"] - a["position_m"]
        travel = eta_service.travel_seconds(dist, route.avg_speed_kmh)
        stops = [{"stop_id": s["stop_id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"],
                  "offset_seconds": eta_service.travel_seconds(s["position_m"] - a["position_m"], route.avg_speed_kmh)}
                 for s in route.stops[i:j + 1]]
        return {
            "route_id": route.id, "route_number": route.number, "route_name": route.name, "route_color": route.color,
            "from": {"stop_id": a["stop_id"], "name": a["name"]}, "to": {"stop_id": b["stop_id"], "name": b["name"]},
            "direction": a["direction"], "distance_m": round(dist), "stops_count": j - i,
            "wait": wait, "depart_seconds": wait["eta_seconds"], "travel_seconds": travel,
            "arrive_seconds": wait["eta_seconds"] + travel, "stops": stops,
        }

    @staticmethod
    def _pairs(route: RouteInfo, from_key: str, to_key: str) -> list[tuple[int, int]]:
        out = []
        for i, a in enumerate(route.stops):
            if a["key"] != from_key:
                continue
            for j in range(i + 1, len(route.stops)):
                b = route.stops[j]
                if b["direction"] != a["direction"]:
                    break
                if b["key"] == to_key:
                    out.append((i, j))
                    break
        return out

    def plan(self, from_name: str, to_name: str, limit: int = 3) -> list[dict]:
        from_key, to_key = from_name.strip().lower(), to_name.strip().lower()
        routes, by_name = self._load()
        if from_key not in by_name or to_key not in by_name:
            return []
        options: list[dict] = []
        from_routes = {rid for rid, _ in by_name[from_key]}
        to_routes = {rid for rid, _ in by_name[to_key]}

        # 1) birbaşa
        for rid in from_routes & to_routes:
            r = routes[rid]
            best = None
            for i, j in self._pairs(r, from_key, to_key):
                leg = self._leg(r, i, j, 0)
                if best is None or leg["arrive_seconds"] < best["arrive_seconds"]:
                    best = leg
            if best:
                options.append({"transfers": 0, "legs": [best], "total_seconds": best["arrive_seconds"]})

        # 2) bir köçürmə: A (from → X) + B (X → to)
        for ra in from_routes:
            A = routes[ra]
            a_starts = [i for i, s in enumerate(A.stops) if s["key"] == from_key]
            for rb in to_routes:
                if rb == ra:
                    continue
                B = routes[rb]
                b_ends = [j for j, s in enumerate(B.stops) if s["key"] == to_key]
                best = None
                for i in a_starts:
                    # A-da from-dan sonra eyni istiqamətdə keçilən dayanacaqlar
                    reach: dict[str, int] = {}
                    for x in range(i + 1, len(A.stops)):
                        if A.stops[x]["direction"] != A.stops[i]["direction"]:
                            break
                        reach.setdefault(A.stops[x]["key"], x)
                    for j in b_ends:
                        for y in range(j - 1, -1, -1):              # B-də to-dan əvvəl eyni istiqamətdə
                            if B.stops[y]["direction"] != B.stops[j]["direction"]:
                                break
                            x = reach.get(B.stops[y]["key"])
                            if x is None or B.stops[y]["key"] == to_key:
                                continue
                            leg1 = self._leg(A, i, x, 0)
                            leg2 = self._leg(B, y, j, leg1["arrive_seconds"] + TRANSFER_WALK_SECONDS)
                            total = leg2["arrive_seconds"]
                            if best is None or total < best["total_seconds"]:
                                best = {"transfers": 1, "legs": [leg1, leg2], "total_seconds": total,
                                        "transfer_stop": B.stops[y]["name"]}
                if best:
                    options.append(best)

        options.sort(key=lambda o: (o["total_seconds"], o["transfers"]))
        # eyni marşrut kombinasiyasını təkrar göstərmə
        seen, unique = set(), []
        for o in options:
            key = tuple(l["route_id"] for l in o["legs"])
            if key in seen:
                continue
            seen.add(key)
            o["stops_count"] = sum(l["stops_count"] for l in o["legs"])
            o["travel_seconds"] = sum(l["travel_seconds"] for l in o["legs"])
            o["wait_seconds"] = o["total_seconds"] - o["travel_seconds"]
            unique.append(o)
        return unique[:limit]
