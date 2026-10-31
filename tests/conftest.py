import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import Database
from app.main import create_app
from app.seed import seed
from app.services.analytics import AnalyticsEngine


@pytest.fixture
def settings(tmp_path):
    return Settings.for_tests(str(tmp_path / "test.db"))


@pytest.fixture
def db(settings):
    database = Database(settings.db_path)
    seed(database, route_limit=settings.seed_route_limit)
    yield database
    database.close()


@pytest.fixture
def engine(db, settings):
    return AnalyticsEngine(db, settings)


@pytest.fixture
def route_ids(db):
    """Testlərdə istifadə üçün ilk üç marşrutun ID-ləri (AYNA məlumatından)."""
    return [r["id"] for r in db.query("SELECT id FROM routes ORDER BY id LIMIT 3")]


@pytest.fixture
def anon_client(settings):
    """Giriş etməmiş müştəri."""
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(settings):
    """Sərnişin kimi daxil olmuş müştəri (demo hesab, ayrıca sessiya)."""
    app = create_app(settings)
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"username": "sernisin", "password": "sernisin123"})
        assert r.status_code == 200
        yield c


@pytest.fixture
def op_client(settings):
    """Operator kimi daxil olmuş müştəri (ayrıca sessiya)."""
    app = create_app(settings)
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"username": "operator", "password": "operator123"})
        assert r.status_code == 200
        yield c
