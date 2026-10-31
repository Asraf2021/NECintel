"""AYNA (Azərbaycan Yerüstü Nəqliyyat Agentliyi) açıq xəritə API-sindən real marşrut məlumatının idxalı.

Mənbə: https://map.ayna.gov.az/  →  https://map-api.ayna.gov.az/api/bus/getBusList, /api/bus/getBusById?id=N

Nəticə app/data/ayna.json faylına yazılır və seed.py tərəfindən istifadə olunur.
İşə salmaq: python -m app.import_ayna
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

BASE = "https://map-api.ayna.gov.az/api"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ayna.json")


def fetch_route(client: httpx.Client, route_id: int) -> dict | None:
    r = client.get(f"{BASE}/bus/getBusById", params={"id": route_id})
    if r.status_code != 200 or not r.text:
        return None
    raw = r.json()
    directions: dict[int, dict] = {}
    for d in (1, 2):
        stops = [s for s in raw.get("stops") or [] if s.get("directionTypeId") == d and s.get("stop")]
        geom = next((g for g in raw.get("routes") or [] if g.get("directionTypeId") == d), None)
        points = [[round(p["lat"], 6), round(p["lng"], 6)] for p in (geom or {}).get("flowCoordinates") or []]
        directions[d] = {
            "stops": [{
                "id": s["stop"]["id"],
                "code": s["stop"].get("code"),
                "name": (s["stop"].get("name") or s.get("stopName") or "").strip(),
                "lat": float(s["stop"]["latitude"]),
                "lon": float(s["stop"]["longitude"]),
            } for s in stops],
            "points": points,
        }
    return {
        "id": raw["id"],
        "number": str(raw["number"]).strip(),
        "carrier": raw.get("carrier"),
        "first_point": (raw.get("firstPoint") or "").strip(),
        "last_point": (raw.get("lastPoint") or "").strip(),
        "length_km": raw.get("routLength"),
        "duration_min": raw.get("durationMinuts"),
        "tariff": raw.get("tariffStr"),
        "directions": directions,
    }


def main() -> None:
    with httpx.Client(timeout=30) as client:
        routes = client.get(f"{BASE}/bus/getBusList").json()
        print(f"{len(routes)} marşrut tapıldı", flush=True)
        out = []
        for i, r in enumerate(routes, 1):
            for attempt in range(3):
                try:
                    data = fetch_route(client, r["id"])
                    break
                except Exception as exc:  # şəbəkə xətası: təkrar cəhd
                    print(f"  {r['number']}: xəta {exc}, cəhd {attempt + 1}", flush=True)
                    time.sleep(1.5)
                    data = None
            if data and (data["directions"][1]["stops"] or data["directions"][2]["stops"]):
                out.append(data)
            if i % 20 == 0:
                print(f"  {i}/{len(routes)}", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": "https://map.ayna.gov.az/", "routes": out}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out)} marşrut yazıldı → {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
