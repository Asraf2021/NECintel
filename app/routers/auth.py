"""Qeydiyyat / giriş / çıxış. Rol: passenger (sərnişin) və ya operator."""
from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from ..services.auth import SESSION_COOKIE

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=6, max_length=128)
    role: Literal["passenger", "operator"]
    full_name: str | None = Field(None, max_length=80)
    email: str = Field(..., max_length=120)
    password_confirm: str = Field(..., max_length=128)


class LoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=120, description="İstifadəçi adı və ya e-poçt")
    password: str = Field(..., min_length=1, max_length=128)


def current_user(request: Request) -> dict | None:
    return request.app.state.auth.user_by_token(request.cookies.get(SESSION_COOKIE))


def require_user(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Giriş tələb olunur")
    return user


def require_role(request: Request, role: str) -> dict:
    user = require_user(request)
    if user["role"] != role:
        raise HTTPException(status_code=403, detail="Bu bölmə yalnız operatorlar üçündür" if role == "operator" else "İcazə yoxdur")
    return user


def _login_response(request: Request, response: Response, user: dict) -> dict:
    token = request.app.state.auth.create_session(user["id"])
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return {"user": user, "home": "/operator" if user["role"] == "operator" else "/app"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, response: Response):
    if body.password != body.password_confirm:
        raise HTTPException(status_code=422, detail="Şifrələr uyğun gəlmir")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", body.email.strip()):
        raise HTTPException(status_code=422, detail="E-poçt ünvanı düzgün deyil")
    try:
        user = request.app.state.auth.register(body.username, body.password, body.role, body.full_name, body.email)
    except ValueError as exc:
        msg = {"exists": "Bu istifadəçi adı artıq mövcuddur", "email_exists": "Bu e-poçt artıq qeydiyyatdadır",
               "short": "İstifadəçi adı ən az 3, şifrə ən az 6 simvol olmalıdır"}.get(str(exc), "Yanlış məlumat")
        raise HTTPException(status_code=422, detail=msg)
    # Sessiya yaradılmır: istifadəçi giriş səhifəsinə yönləndirilir
    return {"user": user, "registered": True}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    user = request.app.state.auth.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="İstifadəçi adı və ya şifrə yanlışdır")
    return _login_response(request, response, user)


@router.post("/logout")
def logout(request: Request, response: Response):
    request.app.state.auth.delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    user = current_user(request)
    return {"user": user, "home": None if user is None else ("/operator" if user["role"] == "operator" else "/app")}
