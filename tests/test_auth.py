"""Qeydiyyat, giriş (ad və ya e-poçt), rollar və icazələr."""


def test_register_requires_matching_passwords_and_valid_email(anon_client):
    base = {"username": "yeni_user", "password": "secret12", "role": "passenger", "email": "yeni@test.az"}
    assert anon_client.post("/api/auth/register", json={**base, "password_confirm": "other"}).status_code == 422
    assert anon_client.post("/api/auth/register", json={**base, "password_confirm": "secret12", "email": "not-an-email"}).status_code == 422
    r = anon_client.post("/api/auth/register", json={**base, "password_confirm": "secret12"})
    assert r.status_code == 201 and r.json()["registered"] is True
    # qeydiyyat sessiya yaratmır: istifadəçi giriş səhifəsinə yönəlir
    assert anon_client.get("/api/auth/me").json()["user"] is None
    assert anon_client.post("/api/auth/register", json={**base, "password_confirm": "secret12"}).status_code == 422  # təkrar ad


def test_login_with_username_or_email(anon_client):
    anon_client.post("/api/auth/register", json={"username": "ayse", "password": "secret12", "password_confirm": "secret12",
                                                 "role": "operator", "email": "ayse@test.az", "full_name": "Ayşə"})
    assert anon_client.post("/api/auth/login", json={"username": "ayse", "password": "wrong"}).status_code == 401
    r = anon_client.post("/api/auth/login", json={"username": "AYSE@test.az", "password": "secret12"})
    assert r.status_code == 200 and r.json()["home"] == "/operator"
    me = anon_client.get("/api/auth/me").json()
    assert me["user"]["username"] == "ayse" and me["user"]["role"] == "operator"
    anon_client.post("/api/auth/logout")
    assert anon_client.get("/api/auth/me").json()["user"] is None


def test_pages_redirect_by_role(anon_client, client, op_client):
    assert anon_client.get("/", follow_redirects=False).headers["location"] == "/login"
    assert client.get("/", follow_redirects=False).headers["location"] == "/app"
    assert client.get("/operator", follow_redirects=False).status_code == 307   # sərnişin operator panelinə girə bilmir
    assert op_client.get("/", follow_redirects=False).headers["location"] == "/operator"
    assert op_client.get("/operator").status_code == 200
    assert anon_client.get("/login").status_code == 200


def test_operator_api_is_protected(anon_client, client, op_client):
    assert anon_client.get("/api/operator/lines").status_code == 401
    assert client.get("/api/operator/lines").status_code == 403
    assert op_client.get("/api/operator/lines").status_code == 200


def test_report_requires_login_and_stores_user(anon_client, client):
    route = client.get("/api/routes").json()[1]
    assert anon_client.post("/api/reports", json={"route_id": route["id"], "level": "low"}).status_code == 401
    r = client.post("/api/reports", json={"route_id": route["id"], "level": "low"})
    assert r.status_code == 201
