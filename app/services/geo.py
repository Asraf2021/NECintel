"""Coğrafi hesablamalar: haversine məsafəsi və polilayn (dövrə) üzrə mövqe."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

EARTH_RADIUS_M = 6_371_000.0
M_PER_DEG_LAT = 110_540.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki nöqtə arasında məsafə (metr)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@dataclass
class Polyline:
    """Marşrut xətti: nöqtələr, yığılmış məsafə və sürətli proyeksiya üçün lokal metrik koordinatlar."""

    points: list[tuple[float, float]]
    cumulative: list[float]
    _xy: list[tuple[float, float]] = field(default_factory=list, repr=False)
    _k_lon: float = 1.0

    @classmethod
    def from_points(cls, points: list[tuple[float, float]]) -> "Polyline":
        cum = [0.0]
        for (a, b) in zip(points, points[1:]):
            cum.append(cum[-1] + haversine_m(a[0], a[1], b[0], b[1]))
        lat0 = points[0][0] if points else 0.0
        k_lon = M_PER_DEG_LAT * math.cos(math.radians(lat0))
        xy = [(lon * k_lon, lat * M_PER_DEG_LAT) for lat, lon in points]
        return cls(points=list(points), cumulative=cum, _xy=xy, _k_lon=k_lon)

    @property
    def length_m(self) -> float:
        return self.cumulative[-1] if self.cumulative else 0.0

    def point_at(self, position_m: float) -> tuple[float, float]:
        """Xəttin başlanğıcından position_m məsafədəki koordinat (xətti interpolyasiya)."""
        if not self.points:
            raise ValueError("boş polilayn")
        pos = max(0.0, min(position_m, self.length_m))
        lo, hi = 1, len(self.points) - 1
        while lo < hi:  # ikili axtarış: cumulative[i-1] < pos <= cumulative[i]
            mid = (lo + hi) // 2
            if pos <= self.cumulative[mid]:
                hi = mid
            else:
                lo = mid + 1
        i = lo
        seg_len = self.cumulative[i] - self.cumulative[i - 1]
        t = 0.0 if seg_len == 0 else (pos - self.cumulative[i - 1]) / seg_len
        (lat1, lon1), (lat2, lon2) = self.points[i - 1], self.points[i]
        return (lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t)

    def project(self, lat: float, lon: float, start_m: float = 0.0, end_m: float | None = None) -> float:
        """Koordinata ən yaxın xətt nöqtəsinin məsafəsi (metr). GPS → xətt üzrə mövqe.

        start_m/end_m ilə axtarış xəttin bir hissəsi ilə məhdudlaşdırıla bilər (istiqamət üzrə).
        """
        end_m = self.length_m if end_m is None else end_m
        px, py = lon * self._k_lon, lat * M_PER_DEG_LAT
        best_pos, best_d2 = start_m, float("inf")
        for i in range(1, len(self.points)):
            c0, c1 = self.cumulative[i - 1], self.cumulative[i]
            if c1 < start_m or c0 > end_m:
                continue
            (x1, y1), (x2, y2) = self._xy[i - 1], self._xy[i]
            dx, dy = x2 - x1, y2 - y1
            denom = dx * dx + dy * dy
            seg_len = c1 - c0
            # seqmentin yalnız [start_m, end_m] daxilindəki hissəsinə proyeksiya
            t_min = 0.0 if seg_len == 0 or c0 >= start_m else (start_m - c0) / seg_len
            t_max = 1.0 if seg_len == 0 or c1 <= end_m else (end_m - c0) / seg_len
            t = 0.0 if denom == 0 else max(t_min, min(t_max, ((px - x1) * dx + (py - y1) * dy) / denom))
            qx, qy = x1 + dx * t, y1 + dy * t
            d2 = (px - qx) ** 2 + (py - qy) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_pos = self.cumulative[i - 1] + (self.cumulative[i] - self.cumulative[i - 1]) * t
        return max(start_m, min(best_pos, end_m))
