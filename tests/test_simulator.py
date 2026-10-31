"""GPS simulyatoru: avtobuslar dövrə üzrə hərəkət edir, sonda başlanğıca qayıdır, hesabatlar yaranır."""
import random
from datetime import timedelta

from app.db import utcnow
from app.services.simulator import GeometryCache, GpsSimulator


def test_buses_move_and_wrap_around(db, settings, engine):
    sim = GpsSimulator(db, settings, GeometryCache(db), engine, rng=random.Random(1))
    before = {b["id"]: b for b in db.query("SELECT * FROM buses")}
    now = utcnow()
    assert sim.tick(now=now, dt_seconds=10) == len(before)
    after = {b["id"]: b for b in db.query("SELECT * FROM buses")}
    moved = [bid for bid in before if abs(after[bid]["position_m"] - before[bid]["position_m"]) > 1]
    assert moved, "ən azı bir avtobus hərəkət etməlidir"
    for bid in before:
        line = sim.geometry.lines[after[bid]["route_id"]]
        assert 0 <= after[bid]["position_m"] < line.length_m

    # çox böyük addım → dövrənin sonundan keçib mövqe mod L qalır
    sim._dwell_until.clear()
    sim.tick(now=now + timedelta(minutes=5), dt_seconds=10_000)
    for b in db.query("SELECT * FROM buses"):
        line = sim.geometry.lines[b["route_id"]]
        assert 0 <= b["position_m"] < line.length_m


def test_generate_reports_only_for_monitored_routes(db, settings, engine):
    sim = GpsSimulator(db, settings, GeometryCache(db), engine, rng=random.Random(7))
    monitored = {r["id"] for r in db.query("SELECT id FROM routes WHERE monitored=1")}
    assert monitored
    total = sum(sim.generate_reports(probability=1.0) for _ in range(40))
    assert total == 40 * len(monitored)
    rows = db.query("SELECT DISTINCT route_id, source FROM reports")
    assert {r["route_id"] for r in rows} == monitored
    assert all(r["source"] == "sim_passenger" for r in rows)
