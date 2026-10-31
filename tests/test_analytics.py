"""Analitika mühərriki: yük aqreqasiyası və 10 dəqiqəlik anomaliya qaydası."""
from datetime import datetime, timedelta, timezone

from app.db import to_iso
from app.services.analytics import (ALERT_MESSAGE_RESERVE_BUS, aggregate_reports, detect_bunching,
                                    score_to_level)

T0 = datetime(2026, 10, 31, 8, 0, tzinfo=timezone.utc)


def _report(level, at, source="passenger"):
    return {"level": level, "created_at": to_iso(at), "source": source}


def add_reports(db, route_id, level, at, n=3, source="passenger"):
    db.executemany(
        "INSERT INTO reports(route_id, level, source, created_at) VALUES (?,?,?,?)",
        [(route_id, level, source, to_iso(at)) for _ in range(n)],
    )


def test_score_to_level_thresholds():
    assert score_to_level(0, 0) == "no_data"
    assert score_to_level(1.2, 1) == "low"
    assert score_to_level(2.0, 1) == "medium"
    assert score_to_level(2.6, 1) == "high"


def test_aggregate_ignores_reports_outside_window():
    reports = [_report("high", T0 - timedelta(minutes=30)), _report("low", T0 - timedelta(minutes=1))]
    s = aggregate_reports(reports, T0, window_minutes=10)
    assert s.report_count == 1
    assert s.level == "low"


def test_aggregate_weights_recent_reports_more():
    reports = [_report("high", T0 - timedelta(minutes=9)), _report("low", T0 - timedelta(seconds=10))]
    s = aggregate_reports(reports, T0, window_minutes=10)
    assert s.level == "low"      # yeni "low" köhnə "high"-dan ağırdır
    assert 1.0 < s.score < 2.0


def test_passenger_report_outweighs_simulated():
    """Bir real sərnişin hesabatı iki virtual hesabatdan ağırdır (3×)."""
    reports = [_report("low", T0, "sim_passenger"), _report("low", T0, "sim_passenger"), _report("high", T0, "passenger")]
    s = aggregate_reports(reports, T0, 10)
    assert s.score > 2.0


def test_aggregate_empty():
    s = aggregate_reports([], T0, 10)
    assert s.level == "no_data" and s.report_count == 0


def test_bunching_detection():
    assert detect_bunching([0, 3000, 6000], 9000) is False
    assert detect_bunching([0, 200, 6000], 9000) is True
    assert detect_bunching([100, 8950], 9000) is True        # dövrənin "tikişində" yaxınlıq
    assert detect_bunching([100], 9000) is False


def test_alert_created_after_sustained_high(db, engine, route_ids):
    """10 dəqiqə fasiləsiz "high" → tövsiyə yaradılır; 9 dəqiqədə yox."""
    rid = route_ids[0]
    for m in range(0, 10):
        add_reports(db, rid, "high", T0 + timedelta(minutes=m))
    assert engine.evaluate(T0) == []
    assert engine.evaluate(T0 + timedelta(minutes=5)) == []
    assert engine.evaluate(T0 + timedelta(minutes=9)) == []
    created = engine.evaluate(T0 + timedelta(minutes=10))
    assert len(created) == 1
    assert created[0]["route_id"] == rid
    assert ALERT_MESSAGE_RESERVE_BUS in created[0]["message"]
    assert engine.evaluate(T0 + timedelta(minutes=11)) == []   # təkrar xəbərdarlıq yoxdur
    assert engine.active_alert(rid) is not None


def test_no_alert_when_high_is_interrupted(db, engine, route_ids):
    rid = route_ids[1]
    add_reports(db, rid, "high", T0)
    engine.evaluate(T0)
    add_reports(db, rid, "low", T0 + timedelta(minutes=5), n=6)
    engine.evaluate(T0 + timedelta(minutes=5))          # seriya kəsilir
    add_reports(db, rid, "high", T0 + timedelta(minutes=6), n=10)
    assert engine.evaluate(T0 + timedelta(minutes=10)) == []
    assert engine.active_alert(rid) is None


def test_no_alert_with_too_few_reports(db, engine, route_ids):
    rid = route_ids[2]
    add_reports(db, rid, "high", T0, n=1)
    engine.evaluate(T0)
    add_reports(db, rid, "high", T0 + timedelta(minutes=10), n=1)
    assert engine.evaluate(T0 + timedelta(minutes=10)) == []


def test_alert_auto_resolves_when_load_drops(db, engine, route_ids):
    rid = route_ids[0]
    created = engine.simulate_sustained_high(rid, now=T0)
    assert len(created) == 1
    assert engine.active_alert(rid) is not None
    engine.evaluate(T0 + timedelta(minutes=30))         # pəncərədə hesabat yoxdur → no_data
    assert engine.active_alert(rid) is None
    row = db.query_one("SELECT status FROM alerts WHERE id=?", (created[0]["id"],))
    assert row["status"] == "resolved"


def test_demo_works_with_interleaved_background_samples(db, engine, route_ids):
    """Fon mühərrikinin köhnə nümunələri demo seriyasını kəsməməlidir."""
    rid = route_ids[1]
    for m in range(12, 0, -1):
        engine.evaluate(T0 - timedelta(minutes=m, seconds=20))   # no_data nümunələri
    created = engine.simulate_sustained_high(rid, now=T0)
    assert len(created) == 1
    assert (T0 - engine.high_since(rid, T0)) >= timedelta(minutes=10)


def test_acknowledge(db, engine, route_ids):
    created = engine.simulate_sustained_high(route_ids[2], now=T0)
    row = engine.acknowledge(created[0]["id"], now=T0)
    assert row["status"] == "acknowledged" and row["acknowledged_at"]
    assert engine.acknowledge(99999) is None
