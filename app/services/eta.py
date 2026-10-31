"""ETA (gözlənilən gəliş vaxtı) hesablaması.

Marşrut qapalı dövrə kimi modelləşdirilir: 1-ci istiqamətin xətti + 2-ci istiqamətin xətti.
Avtobus həmişə irəli gedir və dövrənin sonunda başlanğıca qayıdır (mövqe mod L).
Orta sürət AYNA-nın rəsmi marşrut müddətindən çıxarılır və dayanacaq gözləmələrini daxil edir.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EtaResult:
    distance_m: float
    stops_between: int
    eta_seconds: int


def distance_ahead(bus_pos: float, stop_pos: float, length_m: float) -> float:
    """Dövrə üzrə irəli məsafə (metr)."""
    if length_m <= 0:
        return 0.0
    return (stop_pos - bus_pos) % length_m


def stops_between(bus_pos: float, stop_pos: float, length_m: float, stop_positions: list[float]) -> int:
    """Yolda keçiləcək ara dayanacaqların sayı (hədəf dayanacaq daxil deyil)."""
    ahead = distance_ahead(bus_pos, stop_pos, length_m)
    eps = 1.0
    return sum(1 for p in stop_positions if eps < distance_ahead(bus_pos, p, length_m) < ahead - eps)


def travel_seconds(distance_m: float, avg_speed_kmh: float) -> int:
    return int(round(distance_m / (max(avg_speed_kmh, 5.0) / 3.6)))


def estimate(bus_pos: float, stop_pos: float, length_m: float, stop_positions: list[float],
             avg_speed_kmh: float) -> EtaResult:
    dist = distance_ahead(bus_pos, stop_pos, length_m)
    return EtaResult(
        distance_m=round(dist, 1),
        stops_between=stops_between(bus_pos, stop_pos, length_m, stop_positions),
        eta_seconds=travel_seconds(dist, avg_speed_kmh),
    )
