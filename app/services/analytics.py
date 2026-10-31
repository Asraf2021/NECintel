"""Analitika mühərriki.

1. Crowdsourcing hesabatlarından (aşağı/orta/yüksək) xətt üzrə yük səviyyəsi hesablanır.
   Real sərnişin hesabatı virtual (simulyator) hesabatdan 3 dəfə ağırdır.
2. GPS məlumatından avtobusların "yığılması" (bunching) və orta sürət çıxarılır.
3. Anomaliya: xəttin səviyyəsi fasiləsiz olaraq >= ANOMALY_MINUTES dəqiqə "high" qalırsa,
   operator panelinə "Ehtiyat əlavə avtobus ayrılmalıdır" tövsiyəsi yaradılır.

Bütün funksiyalar `now` parametrini qəbul edir ki, testlərdə vaxt idarə oluna bilsin.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import Settings
from ..db import Database, from_iso, to_iso, utcnow

LEVELS = ("low", "medium", "high")
LEVEL_SCORE = {"low": 1.0, "medium": 2.0, "high": 3.0}
LEVEL_LABEL_AZ = {"low": "Aşağı", "medium": "Orta", "high": "Yüksək", "no_data": "Məlumat yoxdur"}
SOURCE_WEIGHT = {"passenger": 3.0, "sim_passenger": 1.0, "demo": 1.0}
ALERT_TYPE_RESERVE_BUS = "reserve_bus"
ALERT_MESSAGE_RESERVE_BUS = "Ehtiyat əlavə avtobus ayrılmalıdır"


@dataclass
class LoadSummary:
    level: str          # low | medium | high | no_data
    score: float        # 1.0 .. 3.0 (0 = məlumat yoxdur)
    report_count: int


NO_DATA = LoadSummary(level="no_data", score=0.0, report_count=0)


def score_to_level(score: float, count: int) -> str:
    if count == 0:
        return "no_data"
    if score >= 2.5:
        return "high"
    if score >= 1.75:
        return "medium"
    return "low"


def aggregate_reports(reports: list[dict], now: datetime, window_minutes: int) -> LoadSummary:
    """Pəncərə daxilindəki hesabatların yeniliyə və mənbəyə görə çəkili ortalaması.

    Yeni hesabat çəkisi 1.0, pəncərənin sonundakı 0.5; real sərnişin hesabatı 3× ağırdır.
    """
    window = timedelta(minutes=window_minutes)
    total_w, total = 0.0, 0.0
    count = 0
    for r in reports:
        ts = from_iso(r["created_at"]) if isinstance(r["created_at"], str) else r["created_at"]
        age = now - ts
        if age < timedelta(0) or age > window:
            continue
        w = (1.0 - 0.5 * (age / window)) * SOURCE_WEIGHT.get(r.get("source", "passenger"), 1.0)
        total_w += w
        total += w * LEVEL_SCORE[r["level"]]
        count += 1
    if count == 0:
        return NO_DATA
    score = total / total_w
    return LoadSummary(level=score_to_level(score, count), score=round(score, 2), report_count=count)


def detect_bunching(positions_m: list[float], length_m: float, threshold_ratio: float = 0.3) -> bool:
    """GPS əsaslı: dövrədə iki avtobus gözlənilən intervalın 30%-dən yaxındırsa, yığılma var."""
    if len(positions_m) < 2 or length_m <= 0:
        return False
    expected_gap = length_m / len(positions_m)
    ps = sorted(positions_m)
    gaps = [b - a for a, b in zip(ps, ps[1:])] + [length_m - ps[-1] + ps[0]]
    return min(gaps) < expected_gap * threshold_ratio


class AnalyticsEngine:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    # --- oxuma ------------------------------------------------------------------
    def reports_in_window(self, route_id: str, now: datetime) -> list[dict]:
        since = to_iso(now - timedelta(minutes=self.settings.window_minutes))
        return self.db.query(
            "SELECT level, created_at, source FROM reports WHERE route_id=? AND created_at>=? AND created_at<=?",
            (route_id, since, to_iso(now)),
        )

    def current_load(self, route_id: str, now: datetime | None = None) -> LoadSummary:
        now = now or utcnow()
        return aggregate_reports(self.reports_in_window(route_id, now), now, self.settings.window_minutes)

    def current_loads(self, now: datetime | None = None) -> dict[str, LoadSummary]:
        """Bütün xətlər üçün tək sorğu ilə cari yük (panel və siyahılar üçün)."""
        now = now or utcnow()
        since = to_iso(now - timedelta(minutes=self.settings.window_minutes))
        by_route: dict[str, list[dict]] = {}
        for r in self.db.query(
                "SELECT route_id, level, created_at, source FROM reports WHERE created_at>=? AND created_at<=?",
                (since, to_iso(now))):
            by_route.setdefault(r["route_id"], []).append(r)
        return {rid: aggregate_reports(rows, now, self.settings.window_minutes) for rid, rows in by_route.items()}

    def latest_state(self, route_id: str) -> dict | None:
        return self.db.query_one(
            "SELECT route_id, ts, level, score, report_count FROM line_state WHERE route_id=? ORDER BY ts DESC, id DESC LIMIT 1",
            (route_id,),
        )

    def latest_levels(self) -> dict[str, str]:
        rows = self.db.query(
            "SELECT route_id, level FROM line_state WHERE id IN (SELECT MAX(id) FROM line_state GROUP BY route_id)")
        return {r["route_id"]: r["level"] for r in rows}

    def high_since(self, route_id: str, now: datetime) -> datetime | None:
        """Cari fasiləsiz "high" seriyasının başlanğıc vaxtı (yoxdursa None)."""
        rows = self.db.query(
            "SELECT ts, level FROM line_state WHERE route_id=? AND ts<=? ORDER BY ts DESC, id DESC LIMIT 500",
            (route_id, to_iso(now)),
        )
        start: datetime | None = None
        last_ts: str | None = None
        for row in rows:
            if row["ts"] == last_ts:
                continue  # eyni saniyədə köhnə nümunə: ən son yazılan həlledicidir
            last_ts = row["ts"]
            if row["level"] != "high":
                break
            start = from_iso(row["ts"])
        return start

    def active_alert(self, route_id: str, alert_type: str = ALERT_TYPE_RESERVE_BUS) -> dict | None:
        return self.db.query_one(
            "SELECT * FROM alerts WHERE route_id=? AND type=? AND status='active' ORDER BY id DESC LIMIT 1",
            (route_id, alert_type),
        )

    def active_alerts(self) -> dict[str, dict]:
        rows = self.db.query("SELECT * FROM alerts WHERE status='active' ORDER BY id")
        return {r["route_id"]: r for r in rows}

    # --- qiymətləndirmə ------------------------------------------------------------
    def evaluate(self, now: datetime | None = None) -> list[dict]:
        """Bütün xətləri qiymətləndirir, vəziyyəti yazır, lazım olduqda xəbərdarlıq yaradır.

        Qaytarır: bu çağırışda yaradılmış xəbərdarlıqların siyahısı.
        """
        now = now or utcnow()
        created: list[dict] = []
        loads = self.current_loads(now)
        alerts = self.active_alerts()
        routes = self.db.query("SELECT id, number, name FROM routes")
        self.db.executemany(
            "INSERT INTO line_state(route_id, ts, level, score, report_count) VALUES (?,?,?,?,?)",
            [(r["id"], to_iso(now), loads.get(r["id"], NO_DATA).level, loads.get(r["id"], NO_DATA).score,
              loads.get(r["id"], NO_DATA).report_count) for r in routes],
        )
        for route in routes:
            summary = loads.get(route["id"], NO_DATA)
            alert = alerts.get(route["id"])
            if summary.level == "high" and summary.report_count >= self.settings.min_reports:
                since = self.high_since(route["id"], now)
                if since is not None and (now - since) >= timedelta(minutes=self.settings.anomaly_minutes) and alert is None:
                    minutes = int((now - since).total_seconds() // 60)
                    message = (f"{route['number']} nömrəli marşrut ({route['name']}): yük səviyyəsi {minutes} dəqiqədir "
                               f"\"Yüksək\". {ALERT_MESSAGE_RESERVE_BUS}.")
                    cur = self.db.execute(
                        "INSERT INTO alerts(route_id, type, message, created_at, status) VALUES (?,?,?,?,'active')",
                        (route["id"], ALERT_TYPE_RESERVE_BUS, message, to_iso(now)),
                    )
                    created.append({"id": cur.lastrowid, "route_id": route["id"], "message": message})
            elif alert is not None and summary.level in ("low", "no_data"):
                # Yük düşdü: xəbərdarlıq avtomatik bağlanır
                self.db.execute("UPDATE alerts SET status='resolved', resolved_at=? WHERE id=?",
                                (to_iso(now), alert["id"]))
        return created

    # --- operator əməliyyatları ---------------------------------------------------
    def acknowledge(self, alert_id: int, now: datetime | None = None) -> dict | None:
        now = now or utcnow()
        row = self.db.query_one("SELECT * FROM alerts WHERE id=?", (alert_id,))
        if row is None:
            return None
        if row["status"] == "active":
            self.db.execute("UPDATE alerts SET status='acknowledged', acknowledged_at=? WHERE id=?",
                            (to_iso(now), alert_id))
        return self.db.query_one("SELECT * FROM alerts WHERE id=?", (alert_id,))

    def simulate_sustained_high(self, route_id: str, minutes: int | None = None, now: datetime | None = None) -> list[dict]:
        """Demo: son N dəqiqə üçün "high" hesabatları yaradır və mühərriki həmin vaxtlar üçün işlədir."""
        now = now or utcnow()
        minutes = minutes or (self.settings.anomaly_minutes + 1)
        rows = []
        for m in range(minutes, -1, -1):
            ts = to_iso(now - timedelta(minutes=m))
            rows.extend([(route_id, "high", "demo", ts)] * 3)
        self.db.executemany("INSERT INTO reports(route_id, level, source, created_at) VALUES (?,?,?,?)", rows)
        # Fon mühərrikinin həmin pəncərədə yazdığı köhnə nümunələr seriyanı kəsməsin deyə silinir;
        # geriyə tarixli qiymətləndirmə onları yenidən yaradır.
        self.db.execute("DELETE FROM line_state WHERE route_id=? AND ts>=?",
                        (route_id, to_iso(now - timedelta(minutes=minutes))))
        created: list[dict] = []
        for m in range(minutes, -1, -1):
            created.extend(self.evaluate(now - timedelta(minutes=m)))
        return created
