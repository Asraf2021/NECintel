"""ETA, coğrafiya və AYNA məlumatının idxalı."""
import pytest

from app.seed import build_route, load_ayna
from app.services.eta import distance_ahead, estimate, stops_between, travel_seconds
from app.services.geo import Polyline, haversine_m


def test_haversine_known_distance():
    # Sahil → 28 May təxminən 0.9 km
    d = haversine_m(40.3725, 49.8420, 40.3795, 49.8468)
    assert 800 < d < 1000


def test_polyline_length_and_point_at():
    line = Polyline.from_points([(40.0, 49.0), (40.0, 49.01), (40.01, 49.01)])
    assert line.length_m > 0
    assert line.point_at(0) == (40.0, 49.0)
    assert line.point_at(line.length_m) == (40.01, 49.01)
    mid = line.point_at(line.cumulative[1] / 2)
    assert mid[0] == pytest.approx(40.0) and 49.0 < mid[1] < 49.01


def test_polyline_project_gps_to_position_and_range():
    line = Polyline.from_points([(40.0, 49.0), (40.0, 49.02), (40.0, 49.0)])   # ora və geri
    half = line.length_m / 2
    assert line.project(40.0005, 49.01, 0, half) == pytest.approx(half / 2, rel=0.02)
    assert line.project(40.0005, 49.01, half, None) == pytest.approx(half * 1.5, rel=0.02)


def test_distance_ahead_wraps_around_loop():
    assert distance_ahead(100, 500, 1000) == 400
    assert distance_ahead(600, 500, 1000) == 900      # dövrənin sonundan keçib qayıdır
    assert distance_ahead(500, 500, 1000) == 0


def test_stops_between_counts_intermediate_only():
    stops = [0, 250, 500, 750]
    assert stops_between(100, 750, 1000, stops) == 2          # 250, 500
    assert stops_between(600, 250, 1000, stops) == 2          # 750, 0


def test_estimate_scales_with_speed():
    slow = estimate(0, 3000, 5000, [0, 1500, 3000], avg_speed_kmh=10)
    fast = estimate(0, 3000, 5000, [0, 1500, 3000], avg_speed_kmh=40)
    assert slow.stops_between == 1
    assert slow.eta_seconds > fast.eta_seconds > 0
    assert fast.eta_seconds == travel_seconds(3000, 40)


def test_ayna_data_builds_loop_routes():
    routes = load_ayna()
    assert len(routes) >= 150
    r1 = next(r for r in routes if r["number"] == "1")
    built = build_route(r1)
    assert built is not None
    assert 15_000 < built["line"].length_m < 40_000            # 1 nömrəli marşrut ~26 km dövrə
    assert 12 <= built["avg_speed_kmh"] <= 35
    positions = [p for _, _, _, p in built["route_stops"]]
    assert positions == sorted(positions)                      # dayanacaqlar dövrə üzrə artan sırada
    dirs = {d for _, _, d, _ in built["route_stops"]}
    assert dirs == {1, 2}
