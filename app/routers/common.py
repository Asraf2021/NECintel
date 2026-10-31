"""Router-lər üçün ortaq köməkçilər."""
from __future__ import annotations

from fastapi import Request

from ..services.analytics import LEVEL_LABEL_AZ, LoadSummary


def state(request: Request):
    return request.app.state


def load_dict(summary: LoadSummary) -> dict:
    return {
        "level": summary.level,
        "label": LEVEL_LABEL_AZ.get(summary.level, summary.level),
        "score": summary.score,
        "report_count": summary.report_count,
    }
