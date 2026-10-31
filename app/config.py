"""Tətbiq parametrləri. Hamısı mühit dəyişənləri ilə dəyişdirilə bilər (.env.example-a bax)."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int_or_none(name: str) -> int | None:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else None


@dataclass
class Settings:
    # Verilənlər bazası
    db_path: str = os.getenv("DB_PATH", "data/transit.db")
    seed_route_limit: int | None = _env_int_or_none("SEED_ROUTE_LIMIT")   # None = AYNA-dan bütün marşrutlar

    # Analitika
    window_minutes: int = int(os.getenv("LOAD_WINDOW_MINUTES", "10"))      # yük səviyyəsi üçün pəncərə
    anomaly_minutes: int = int(os.getenv("ANOMALY_MINUTES", "10"))         # "Yüksək" davam etməli olduğu müddət
    min_reports: int = int(os.getenv("ANOMALY_MIN_REPORTS", "3"))          # pəncərədə minimum hesabat sayı
    eval_seconds: float = float(os.getenv("ANALYTICS_EVAL_SECONDS", "15")) # mühərrikin qiymətləndirmə intervalı

    # GPS simulyatoru
    sim_enabled: bool = _env_bool("SIM_ENABLED", True)
    sim_reports: bool = _env_bool("SIM_REPORTS", True)                     # virtual sərnişin hesabatları
    tick_seconds: float = float(os.getenv("SIM_TICK_SECONDS", "2"))
    dwell_seconds: int = int(os.getenv("DWELL_SECONDS", "20"))

    @classmethod
    def for_tests(cls, db_path: str) -> "Settings":
        return cls(db_path=db_path, sim_enabled=False, sim_reports=False, seed_route_limit=6)
