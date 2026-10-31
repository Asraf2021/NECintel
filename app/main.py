"""FastAPI tətbiqi: router-lər, səhifələr, statik fayllar və fon tapşırıqları (GPS simulyatoru, analitika)."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import Database
from .routers import auth, operator, passenger
from .routers.auth import current_user
from .seed import seed
from .services.analytics import AnalyticsEngine
from .services.auth import AuthService
from .services.simulator import GeometryCache, GpsSimulator

log = logging.getLogger("smart_transit")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


async def _simulator_loop(app: FastAPI) -> None:
    st = app.state
    tick = 0
    while True:
        await asyncio.sleep(st.settings.tick_seconds)
        try:
            await asyncio.to_thread(st.simulator.tick)
            tick += 1
            if st.settings.sim_reports and tick % 3 == 0:  # hər ~6 saniyədə virtual hesabatlar
                await asyncio.to_thread(st.simulator.generate_reports)
        except Exception:  # fon tapşırığı heç vaxt ölməməlidir
            log.exception("simulyator xətası")


async def _analytics_loop(app: FastAPI) -> None:
    st = app.state
    while True:
        await asyncio.sleep(st.settings.eval_seconds)
        try:
            created = await asyncio.to_thread(st.engine.evaluate)
            for a in created:
                log.warning("XƏBƏRDARLIQ #%s: %s", a["id"], a["message"])
        except Exception:
            log.exception("analitika xətası")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = Database(settings.db_path)
        seed(db, route_limit=settings.seed_route_limit)
        app.state.settings = settings
        app.state.db = db
        app.state.auth = AuthService(db)
        app.state.geometry = GeometryCache(db)
        app.state.engine = AnalyticsEngine(db, settings)
        app.state.simulator = GpsSimulator(db, settings, app.state.geometry, app.state.engine)
        app.state.engine.evaluate()
        tasks: list[asyncio.Task] = []
        if settings.sim_enabled:
            tasks.append(asyncio.create_task(_simulator_loop(app)))
            tasks.append(asyncio.create_task(_analytics_loop(app)))
        log.info("Smart Transit başladı (db=%s, simulyator=%s)", settings.db_path, settings.sim_enabled)
        try:
            yield
        finally:
            for t in tasks:
                t.cancel()
            db.close()

    app = FastAPI(
        title="Smart Transit & Crowdsourcing Engine",
        description="Bakı avtobus marşrutları üçün canlı mövqe, ETA, crowdsourcing yük məlumatı və operator analitikası.",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.include_router(auth.router)
    app.include_router(passenger.router)
    app.include_router(operator.router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def page(name: str) -> FileResponse:
        return FileResponse(os.path.join(STATIC_DIR, name))

    @app.get("/", include_in_schema=False)
    def home(request: Request):
        user = current_user(request)
        if user is None:
            return RedirectResponse("/login")
        return RedirectResponse("/operator" if user["role"] == "operator" else "/app")

    @app.get("/login", include_in_schema=False)
    def login_page():
        return page("login.html")

    @app.get("/app", include_in_schema=False)
    def passenger_app(request: Request):
        if current_user(request) is None:
            return RedirectResponse("/login")
        return page("app.html")

    @app.get("/operator", include_in_schema=False)
    def operator_page(request: Request):
        user = current_user(request)
        if user is None or user["role"] != "operator":
            return RedirectResponse("/login?need=operator")
        return page("operator.html")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return FileResponse(os.path.join(STATIC_DIR, "manifest.webmanifest"), media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok", "simulator": settings.sim_enabled}

    return app


app = create_app()
