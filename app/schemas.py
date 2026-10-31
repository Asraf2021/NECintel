"""API giriş/çıxış modelləri (pydantic)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["low", "medium", "high"]


class ReportIn(BaseModel):
    route_id: str = Field(..., min_length=1, max_length=32, description="Marşrut ID (məs. r5)")
    level: Level = Field(..., description="Yük səviyyəsi: low | medium | high")
    bus_id: str | None = Field(None, max_length=32)
    stop_id: str | None = Field(None, max_length=32)


class LoadOut(BaseModel):
    level: str
    label: str
    score: float
    report_count: int


class ReportOut(BaseModel):
    id: int
    route_id: str
    bus_id: str | None
    stop_id: str | None
    level: str
    source: str
    created_at: str
    line_load: LoadOut
