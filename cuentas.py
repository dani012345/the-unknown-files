"""Acceso por cuenta y sesiones temporales de invitados."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
import re
import secrets

from flask import (
    Blueprint, abort, g, jsonify, make_response, redirect, render_template, request, url_for,
)
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

COOKIE = "uf_session"


def create_accounts_blueprint(database):
    bp = Blueprint("cuentas", __name__)
    users = database["usuarios"]
    sessions = database["sesiones"]
    saves = database["partidas"]
    indexes_ready = False

    def prepare_indexes():
        nonlocal indexes_ready
        if indexes_ready:
            return
        users.create_index("username_key", unique=True)
        users.create_index("email_key", unique=True)
        sessions.create_index("expires_at", expireAfterSeconds=0)
        saves.create_index("expires_at", expireAfterSeconds=0)
        database["saldos"].create_index("expires_at", expireAfterSeconds=0)
        indexes_ready = True

    def new_session(user=None, guest=False, owner=None):
        prepare_indexes()
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        record = {
            "_id": sha256(token.encode()).hexdigest(),
            "csrf": secrets.token_urlsafe(32),
            "user_id": user["_id"] if user else None,
            "guest": guest,
            "owner": user["owner"] if user else owner or secrets.token_hex(32),
            "expires_at": now + timedelta(days=30 if user else 1),
        }
        sessions.insert_one(record)
        return record, token

    def respond(response, token=None, persistent=False):
        response = make_response(response)
        if token:
            response.set_cookie(
                COOKIE, token, httponly=True, samesite="Lax",
                secure=bool(os.environ.get("RENDER")) or request.is_secure,
                max_age=60 * 60 * 24 * 30 if persistent else None,
            )
        response.headers["Cache-Control"] = "no-store"
        return response

    @bp.before_app_request
    def load_identity():
        g.account = None
        g.access_session = None
        token = request.cookies.get(COOKIE, "")
        if len(token) == 43 and re.fullmatch(r"[A-Za-z0-9_-]+", token):
            record = sessions.find_one({
                "_id": sha256(token.encode()).hexdigest(),
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            })
            if record:
                if record["user_id"]:
                    g.account = users.find_one({"_id": record["user_id"]})
                    if g.account is None:
                        return
                    admin_names = {
                        name.strip().casefold()
                        for name in os.environ.get("ADMIN_USERNAMES", "").split(",")
                        if name.strip()
                    }
                    if g.account["username_key"] in admin_names:
                        g.account["role"] = "admin"
                g.access_session = record

    @bp.app_context_processor
    def account_context():
        return {
            "account": g.get("account"),
            "guest": bool(g.get("access_session") and g.access_session["guest"]),
            "access_csrf": g.access_session["csrf"] if g.get("access_session") else "",
            "is_admin": bool(g.get("account") and g.account.get("role") == "admin"),
        }

    def check_csrf():
        if not g.access_session or not secrets.compare_digest(
            request.form.get("csrf", ""), g.access_session["csrf"]
        ):
            abort(400, description="El formulario venció. Abre de nuevo el panel de acceso.")

    def panel(error="", tab="login", status=200):
        record = g.access_session
        token = None
        if record is None:
            record, token = new_session()
            g.access_session = record
        return respond((
            render_template(
                "portada.html", has_progress=False, show_access=True,
                access_error=error, access_tab=tab, form_csrf=record["csrf"],
            ), status
        ), token)

    @bp.get("/acceso")
    def entry():
        if g.account:
            return redirect(url_for("inicio"))
        return panel(tab="register" if request.args.get("modo") == "registro" else "login")

    def enter(user=None, guest=False):
        old_session = g.access_session
        owner = None
        if guest:
            # Conserva el acceso a partidas antiguas de este navegador al entrar
            # explícitamente como invitado.
            legacy = request.cookies.get("uf_player", "")
            if 32 <= len(legacy) <= 100 and re.fullmatch(r"[A-Za-z0-9_-]+", legacy):
                owner = sha256(legacy.encode()).hexdigest()
        record, token = new_session(user, guest, owner)
        if guest:
            saves.update_many(
                {"owner_hash": record["owner"]},
                {"$set": {"expires_at": record["expires_at"]}},
            )
            database["saldos"].update_one(
                {"_id": record["owner"]},
                {"$set": {"expires_at": record["expires_at"]}},
            )
        if old_session:
            sessions.delete_one({"_id": old_session["_id"]})
        response = respond(redirect(url_for("inicio"), code=303), token, bool(user))
        response.delete_cookie("uf_player")
        return response

    @bp.post("/acceso/registro")
    def register():
        check_csrf()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().casefold()
        password = request.form.get("password", "")
        description = request.form.get("description", "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username):
            return panel("Usa de 3 a 30 letras sin acentos, números, puntos, guiones o guiones bajos.", "register", 400)
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            return panel("Escribe un correo válido.", "register", 400)
        if not 8 <= len(password) <= 128:
            return panel("La contraseña debe tener entre 8 y 128 caracteres.", "register", 400)
        if password != request.form.get("password_confirm", ""):
            return panel("Las contraseñas deben coincidir.", "register", 400)
        if len(description) > 300:
            return panel("La descripción admite hasta 300 caracteres.", "register", 400)
        user = {
            "username": username, "username_key": username.casefold(),
            "email": email, "email_key": email,
            "password_hash": generate_password_hash(password),
            "description": description, "role": "player",
            "owner": secrets.token_hex(32), "created_at": datetime.now(timezone.utc),
        }
        prepare_indexes()
        try:
            user["_id"] = users.insert_one(user).inserted_id
        except DuplicateKeyError:
            return panel("Ese usuario o correo ya está registrado. Inicia sesión o usa otros datos.", "register", 409)
        return enter(user=user)

    @bp.post("/acceso/entrar")
    def login():
        check_csrf()
        identifier = request.form.get("identifier", "").strip().casefold()
        password = request.form.get("password", "")
        if len(identifier) > 254 or len(password) > 128:
            return panel("Usuario, correo o contraseña incorrectos.", status=400)
        user = users.find_one({"$or": [
            {"username_key": identifier}, {"email_key": identifier},
        ]})
        if not user or not check_password_hash(user["password_hash"], password):
            return panel("Usuario, correo o contraseña incorrectos.", status=401)
        return enter(user=user)

    @bp.post("/acceso/invitado")
    def guest_entry():
        check_csrf()
        return enter(guest=True)

    @bp.get("/cuenta")
    def profile():
        if not g.account:
            return panel(tab="register")
        return respond(render_template("cuenta.html"))

    @bp.route("/salir", methods=["GET", "POST"])
    def logout():
        if request.method == "GET":
            return respond(render_template("portada.html", show_exit=True, has_progress=False))
        if g.access_session:
            check_csrf()
            sessions.delete_one({"_id": g.access_session["_id"]})
        g.account = None
        g.access_session = None
        if request.accept_mimetypes.best == "application/json":
            response = respond(jsonify(ok=True))
        else:
            response = respond(render_template("portada.html", show_exit=True, exit_closed=True, has_progress=False))
        response.delete_cookie(COOKIE)
        response.delete_cookie("uf_player")
        return response

    return bp
