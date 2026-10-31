"""HTTP API: sərnişin və operator modulları (AYNA məlumatı, test rejimində 6 marşrut)."""


def _first_route(client):
    return client.get("/api/routes").json()[0]


def test_health_and_pages(client, op_client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/app").status_code == 200
    assert op_client.get("/operator").status_code == 200
    assert client.get("/manifest.webmanifest").status_code == 200 and client.get("/sw.js").status_code == 200


def test_routes_and_stops_seeded(client):
    routes = client.get("/api/routes").json()
    assert len(routes) == 6
    r = routes[0]
    detail = client.get(f"/api/routes/{r['id']}").json()
    assert len(detail["polyline"]) > 50 and detail["buses"] and len(detail["stops"]) > 10
    assert {s["direction"] for s in detail["stops"]} == {1, 2}
    assert client.get("/api/routes/nope").status_code == 404
    assert client.get("/api/routes?q=" + r["number"]).json()[0]["number"] == r["number"]
    stops = client.get("/api/stops?q=m/st").json()
    assert stops and all("m/st" in s["name"] for s in stops) and all(s["routes"] for s in stops)
    names = client.get("/api/stops/names").json()
    assert len(names) > 100 and names == sorted(names)
    near = client.get("/api/stops/nearest?lat=40.3777&lon=49.8469&limit=5").json()
    assert len(near) == 5 and near[0]["distance_m"] <= near[-1]["distance_m"] and all(s["routes"] for s in near)


def test_buses_live_positions(client):
    r = _first_route(client)
    buses = client.get(f"/api/buses?route_id={r['id']}").json()
    assert 3 <= len(buses) <= 10
    b = buses[0]
    assert {"lat", "lon", "speed_kmh", "next_stop", "load_level", "plate", "label"} <= set(b)
    assert b["label"].startswith(r["number"] + " · ")
    assert client.get("/api/buses?route_id=zzz").status_code == 404


def test_eta_for_stop(client):
    r = _first_route(client)
    stop = client.get(f"/api/routes/{r['id']}").json()["stops"][3]
    data = client.get(f"/api/eta?stop_id={stop['id']}").json()
    assert data["stop"]["id"] == stop["id"]
    assert data["arrivals"]
    etas = [a["eta_seconds"] for a in data["arrivals"]]
    assert etas == sorted(etas) and all(0 <= e < 2 * 3600 for e in etas)
    only = client.get(f"/api/eta?stop_id={stop['id']}&route_id={r['id']}").json()
    assert {a["route_id"] for a in only["arrivals"]} == {r["id"]} and len(only["arrivals"]) <= 2
    assert client.get(f"/api/eta?stop_id={stop['id']}&route_id=nope").status_code == 404
    assert client.get("/api/eta?stop_id=none").status_code == 404


def test_trip_planner_direct_and_transfer(client):
    r = _first_route(client)
    stops = [s for s in client.get(f"/api/routes/{r['id']}").json()["stops"] if s["direction"] == 1]
    a, b = stops[1], stops[6]
    data = client.get("/api/trip", params={"from_name": a["name"], "to_name": b["name"]}).json()
    assert data["options"], "birbaşa marşrut tapılmalıdır"
    opt = data["options"][0]
    assert opt["transfers"] == 0 and len(opt["legs"]) == 1
    leg = opt["legs"][0]
    assert leg["from"]["name"] == a["name"] and leg["to"]["name"] == b["name"]
    assert leg["travel_seconds"] > 0 and leg["wait"]["eta_seconds"] >= 0
    assert opt["total_seconds"] == leg["wait"]["eta_seconds"] + leg["travel_seconds"]
    offsets = [s["offset_seconds"] for s in leg["stops"]]
    assert offsets[0] == 0 and offsets == sorted(offsets) and leg["stops"][-1]["name"] == b["name"]
    assert len(data["options"]) <= 3
    # köçürməli variant: 2-ci marşrutun dayanacağı → 1-ci marşrutun dayanacağı (ortaq dayanacaq varsa)
    other = client.get("/api/routes").json()[1]
    o_stops = [s for s in client.get(f"/api/routes/{other['id']}").json()["stops"] if s["direction"] == 1]
    data2 = client.get("/api/trip", params={"from_name": o_stops[0]["name"], "to_name": b["name"]}).json()
    for o in data2["options"]:
        assert o["transfers"] in (0, 1) and len(o["legs"]) == o["transfers"] + 1
        if o["transfers"] == 1:
            l1, l2 = o["legs"]
            assert l1["to"]["name"].lower() == l2["from"]["name"].lower() == o["transfer_stop"].lower()
            assert l2["wait"]["eta_seconds"] >= l1["arrive_seconds"]          # köçürmədə gözləmə mənfi ola bilməz
            assert o["total_seconds"] == l2["arrive_seconds"]
    rev = client.get("/api/trip", params={"from_name": b["name"], "to_name": a["name"]}).json()
    assert all(o["legs"][0]["from"]["name"] == b["name"] for o in rev["options"])
    assert client.get("/api/trip", params={"from_name": a["name"], "to_name": a["name"]}).status_code == 422
    assert client.get("/api/trip", params={"from_name": "yoxdur-xx", "to_name": "yoxdur-yy"}).status_code == 404


def test_route_and_bus_timeline(client):
    r = _first_route(client)
    data = client.get(f"/api/routes/{r['id']}/timeline").json()
    assert data["route"]["id"] == r["id"] and len(data["stops"]) > 10
    assert all(s["next_bus"]["eta_seconds"] >= 0 for s in data["stops"])
    assert data["stops"][0]["leg_seconds"] == 0 and any(s["leg_seconds"] > 0 for s in data["stops"])
    assert client.get("/api/routes/nope/timeline").status_code == 404
    bus = client.get(f"/api/buses?route_id={r['id']}").json()[0]
    bt = client.get(f"/api/buses/{bus['id']}/timeline").json()
    etas = [s["eta_seconds"] for s in bt["stops"]]
    assert bt["bus"]["id"] == bus["id"] and etas == sorted(etas) and len(etas) == len(data["stops"])
    assert client.get("/api/buses/none/timeline").status_code == 404


def test_create_report_and_validation(client):
    r = _first_route(client)
    detail = client.get(f"/api/routes/{r['id']}").json()
    stop, bus = detail["stops"][0], detail["buses"][0]
    res = client.post("/api/reports", json={"route_id": r["id"], "level": "high", "stop_id": stop["id"], "bus_id": bus["id"]})
    assert res.status_code == 201
    body = res.json()
    assert body["source"] == "passenger" and body["line_load"]["report_count"] == 1 and body["line_load"]["level"] == "high"
    assert client.post("/api/reports", json={"route_id": r["id"], "level": "extreme"}).status_code == 422
    assert client.post("/api/reports", json={"route_id": "missing", "level": "low"}).status_code == 404
    other = client.get("/api/routes").json()[1]
    other_bus = client.get(f"/api/routes/{other['id']}").json()["buses"][0]
    assert client.post("/api/reports", json={"route_id": r["id"], "level": "low", "bus_id": other_bus["id"]}).status_code == 422
    assert client.post("/api/reports", json={"route_id": r["id"], "level": "low", "stop_id": "s0"}).status_code == 422
    recent = client.get(f"/api/reports/recent?route_id={r['id']}&source=passenger").json()
    assert recent[0]["id"] == body["id"] and recent[0]["stop_name"] == stop["name"] and recent[0]["plate"] == bus["plate"]


def test_operator_lines_reflect_reports(client, op_client):
    r = client.get("/api/routes").json()[2]
    for _ in range(3):
        client.post("/api/reports", json={"route_id": r["id"], "level": "high"})
    lines = op_client.get("/api/operator/lines").json()
    assert lines[0]["id"] == r["id"]                       # "Yüksək" xətt siyahının başında
    assert lines[0]["load"]["level"] == "high"
    assert lines[0]["report_sources"]["passenger"] == 3
    assert lines[0]["bus_count"] >= 2 and "bunching" in lines[0]
    assert len(op_client.get("/api/operator/lines?only_with_data=true").json()) == 1


def test_demo_creates_alert_and_ack_flow(op_client):
    client = op_client
    r = _first_route(client)
    assert client.get("/api/operator/alerts").json() == []
    res = client.post(f"/api/operator/demo/high-load/{r['id']}").json()
    assert len(res["created_alerts"]) == 1
    alerts = client.get("/api/operator/alerts").json()
    assert len(alerts) == 1 and alerts[0]["status"] == "active" and alerts[0]["route"]["number"] == r["number"]
    assert "Ehtiyat əlavə avtobus" in alerts[0]["message"]
    line = next(l for l in client.get("/api/operator/lines").json() if l["id"] == r["id"])
    assert line["active_alert"]["id"] == alerts[0]["id"]
    assert line["high_for_minutes"] >= 10
    ack = client.post(f"/api/operator/alerts/{alerts[0]['id']}/ack").json()
    assert ack["status"] == "acknowledged"
    assert client.get("/api/operator/alerts").json() == []
    assert client.post("/api/operator/alerts/4242/ack").status_code == 404
    hist = client.get(f"/api/operator/history/{r['id']}?minutes=30").json()
    assert hist and hist[-1]["level"] == "high"
    assert client.post("/api/operator/demo/high-load/none").status_code == 404
