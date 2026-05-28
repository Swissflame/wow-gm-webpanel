from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import time
import subprocess

from .database import init_db, get_db
from .models import PanelUser
from .settings import get_settings
from .security import csrf_token, verify_csrf, hash_password, verify_password, verify_azeroth_password
from .services.config_store import bootstrap_defaults, all_config, get_config, set_config
from .services.audit import log_action
from .services import wowdb
from .services.realm import REALMS, selected_realm, realm_cfg
from .services.ssh_service import SSHClient, test_port
from .services.config_scanner import scan_remote, update_value
from .services.gm import allowed_commands, normalize_db_commands, record_command
from .services.gm_actions import TABS, build_command, event_actions, localized_actions
from .services.gm_transport import execute_gm_command
from .services.server_metrics import collect_server_overview
from .services.ahbot_config import grouped_fields, load_ahbot, reset_ahbot, save_ahbot, schedule_realm_restart, summarize
from .services.playerbot_config import grouped_fields as grouped_playerbot_fields, load_playerbot, reset_playerbot, save_playerbot, summarize as summarize_playerbot
from .services.main_config import grouped_main_configs, load_main_configs, save_main_configs, schedule_auth_restart, summarize_main_configs
from .i18n import translate

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))


def create_app() -> FastAPI:
    app = FastAPI(title="WoW GM Webpanel")
    app.add_middleware(SessionMiddleware, secret_key=get_settings().app_secret_key, same_site="lax", https_only=False)
    app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

    @app.on_event("startup")
    def startup():
        Path("instance").mkdir(exist_ok=True)
        init_db()
        with next(get_db()) as db:
            bootstrap_defaults(db)

    app.add_api_route("/", index, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/setup", setup_get, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/setup", setup_post, methods=["POST"])
    app.add_api_route("/login", login_get, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/login", login_post, methods=["POST"])
    app.add_api_route("/logout", logout, methods=["POST"])
    app.add_api_route("/context", context_post, methods=["POST"])
    app.add_api_route("/dashboard", dashboard, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/online", online, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/accounts", accounts, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/accounts/create", account_create, methods=["POST"])
    app.add_api_route("/accounts/{account_id}", account_detail, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/accounts/{account_id}/save", account_save, methods=["POST"])
    app.add_api_route("/accounts/{account_id}/delete", account_delete, methods=["POST"])
    app.add_api_route("/characters", characters, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/characters/{realm}/{guid}", character_detail, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/characters/{realm}/{guid}/save", character_save, methods=["POST"])
    app.add_api_route("/characters/{realm}/{guid}/transfer", character_transfer, methods=["POST"])
    app.add_api_route("/characters/{realm}/{guid}/delete", character_delete, methods=["POST"])
    app.add_api_route("/gm", gm_console, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/gm/favorites", gm_favorites, methods=["POST"])
    app.add_api_route("/gm/run", gm_run, methods=["POST"])
    app.add_api_route("/gm/action", gm_action, methods=["POST"])
    app.add_api_route("/server", server, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/server/action", server_action, methods=["POST"])
    app.add_api_route("/server/extra-info", server_extra_info, methods=["POST"], response_class=HTMLResponse)
    app.add_api_route("/configs", configs, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/configs/save", config_save, methods=["POST"])
    app.add_api_route("/ahbot", ahbot, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/ahbot/save", ahbot_save, methods=["POST"])
    app.add_api_route("/ahbot/reset", ahbot_reset, methods=["POST"])
    app.add_api_route("/playerbots", playerbots, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/playerbots/save", playerbots_save, methods=["POST"])
    app.add_api_route("/playerbots/reset", playerbots_reset, methods=["POST"])
    app.add_api_route("/logs", logs, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/backup", backup, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/settings", settings_page, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/reset", reset_post, methods=["POST"])
    return app

def render(request: Request, name: str, context: dict, db: Session | None = None):
    lang = request.session.get("lang") or (all_config(db).get("language") if db else "de") or "de"
    context.setdefault("request", request)
    context.setdefault("csrf", csrf_token(request))
    context.setdefault("user", getattr(request.state, "user", None))
    context.setdefault("cfg", all_config(db) if db else {})
    context.setdefault("lang", lang)
    context.setdefault("_", lambda text: translate(lang, text))
    context.setdefault("realms", REALMS)
    context.setdefault("selected_realm", selected_realm(request))
    context.setdefault("selected_realm_info", realm_cfg(context["cfg"], selected_realm(request)) if context.get("cfg") else {})
    return templates.TemplateResponse(name, context)


def short_flash(message: str, limit: int = 900) -> str:
    message = " ".join(str(message).split())
    return message if len(message) <= limit else message[:limit] + " ..."


def setup_done(db: Session) -> bool:
    return bool(all_config(db).get("setup_complete"))


def current_user(request: Request, db: Session = Depends(get_db)) -> PanelUser:
    uid = request.session.get("uid")
    if not uid:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    user = db.get(PanelUser, uid)
    if not user or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    request.state.user = user
    return user


def require_level(level: int):
    def dep(user: PanelUser = Depends(current_user)):
        if user.gm_level < level:
            raise HTTPException(status_code=403, detail="Nicht erlaubt")
        return user
    return dep


def index(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse("/dashboard" if setup_done(db) else "/setup", status_code=303)


def setup_get(request: Request, db: Session = Depends(get_db)):
    if setup_done(db) and not request.query_params.get("force"):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "setup.html", {"title": "Setup"}, db)


def setup_post(request: Request, db: Session = Depends(get_db), csrf: str = Form(...), language: str = Form("de"),
               wow_host: str = Form(...), ssh_user: str = Form(...), ssh_password: str = Form(""),
               mysql_host: str = Form(...), mysql_user: str = Form(...), mysql_password: str = Form(""),
               admin_username: str = Form(...), admin_password: str = Form(...)):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    if len(admin_password) < 8:
        return render(request, "setup.html", {"title": "Setup", "error": "Das Admin-Passwort muss mindestens 8 Zeichen lang sein."}, db)
    set_config(db, "language", language)
    set_config(db, "server", {"wow_host": wow_host, "ssh_user": ssh_user, "ssh_password": ssh_password, "ssh_port": 22, "normal_path": "/opt/azeroth-server", "playerbot_path": "/opt/azeroth-playerbots-server"})
    set_config(db, "mysql", {"host": mysql_host, "port": 3306, "user": mysql_user, "password": mysql_password, "auth_db": "acore_auth", "world_db": "acore_world", "characters_db": "acore_characters", "pb_world_db": "pb_world", "pb_characters_db": "pb_characters", "playerbots_db": "acore_playerbots"})
    set_config(db, "realms", {"auth_port": 3724, "normal_world_port": 8085, "playerbot_world_port": 8086})
    user = db.query(PanelUser).filter_by(username=admin_username).first() or PanelUser(username=admin_username)
    user.password_hash = hash_password(admin_password)
    user.gm_level = 4
    user.is_active = True
    db.add(user)
    set_config(db, "setup_complete", True)
    log_action(db, user.id, "setup_complete", "webpanel", ip=request.client.host if request.client else None)
    return RedirectResponse("/login", status_code=303)


def login_get(request: Request, db: Session = Depends(get_db)):
    return render(request, "login.html", {"title": "Login"}, db)


def login_post(request: Request, db: Session = Depends(get_db), csrf: str = Form(...), username: str = Form(...), password: str = Form(...)):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    cfg = all_config(db)
    user = db.query(PanelUser).filter_by(username=username).first()
    ok = user and verify_password(password, user.password_hash)
    if not ok and cfg.get("setup_complete"):
        try:
            account = wowdb.account_by_username(cfg["mysql"], cfg["mysql"]["auth_db"], username)
            if account and verify_azeroth_password(username, password, account):
                level = wowdb.gm_level(cfg["mysql"], cfg["mysql"]["auth_db"], int(account["id"]))
                user = user or PanelUser(username=username, wow_account_id=int(account["id"]))
                user.gm_level = level
                user.is_active = True
                db.add(user)
                db.commit()
                ok = True
        except Exception:
            ok = False
    if not ok or not user:
        return render(request, "login.html", {"title": "Login", "error": "Login fehlgeschlagen"}, db)
    if cfg.get("setup_complete"):
        try:
            account = wowdb.account_by_username(cfg["mysql"], cfg["mysql"]["auth_db"], username)
            if account and (not user.wow_account_id or user.wow_account_id == int(account["id"])):
                user.wow_account_id = int(account["id"])
                user.gm_level = wowdb.gm_level(cfg["mysql"], cfg["mysql"]["auth_db"], int(account["id"]))
                db.add(user)
                db.commit()
        except Exception:
            pass
    request.session["uid"] = user.id
    log_action(db, user.id, "login", ip=request.client.host if request.client else None)
    return RedirectResponse("/dashboard", status_code=303)


def logout(request: Request, user: PanelUser = Depends(current_user)):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


def context_post(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(current_user), csrf: str = Form(...), realm: str = Form("normal"), lang: str = Form("de")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    if realm in REALMS:
        request.session["realm"] = realm
    if lang in {"de", "en"}:
        request.session["lang"] = lang
        set_config(db, "language", lang)
    return RedirectResponse(request.headers.get("referer") or "/dashboard", status_code=303)


def dashboard(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(current_user)):
    cfg = all_config(db)
    realm = selected_realm(request)
    status = {
        "auth": test_port(cfg["server"]["wow_host"], cfg["realms"]["auth_port"]),
        "normal": test_port(cfg["server"]["wow_host"], cfg["realms"]["normal_world_port"]),
        "playerbot": test_port(cfg["server"]["wow_host"], cfg["realms"]["playerbot_world_port"]),
    }
    try:
        stats = wowdb.dashboard_stats(cfg, realm)
    except Exception as exc:
        stats = {"error": str(exc)}
    return render(request, "dashboard.html", {"title": "Dashboard", "status": status, "stats": stats}, db)


def online(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(0))):
    try:
        players = wowdb.online_players(all_config(db), selected_realm(request))
    except Exception as exc:
        players, error = [], str(exc)
    else:
        error = None
    return render(request, "online.html", {"title": "Online-Spieler", "players": players, "error": error}, db)


def accounts(request: Request, q: str = "", include_bots: int = 0, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    try:
        items, error = wowdb.search_accounts(all_config(db), q, include_bots=bool(include_bots)), None
    except Exception as exc:
        items, error = [], str(exc)
    flash = request.session.pop("account_error", None)
    return render(request, "accounts.html", {"title": "Accounts", "items": items, "q": q, "include_bots": include_bots, "error": error, "flash": flash}, db)


def account_detail(request: Request, account_id: int, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    try:
        account, error = wowdb.account_detail(all_config(db), account_id), None
    except Exception as exc:
        account, error = None, str(exc)
    if not account and not error:
        raise HTTPException(404, "Account nicht gefunden")
    flash = request.session.pop("account_flash", None)
    return render(request, "account_detail.html", {"title": "Account", "account": account, "error": error, "flash": flash}, db)


def account_create(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)),
                   csrf: str = Form(...), username: str = Form(...), password: str = Form(...), email: str = Form(""),
                   expansion: int = Form(2), gm_level: int = Form(0)):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    try:
        gm_level = max(0, min(int(gm_level), 4))
        account_id = wowdb.create_account(all_config(db), username, password, email, expansion, gm_level)
        log_action(db, user.id, "account_create", str(account_id), username, request.client.host if request.client else None)
        return RedirectResponse(f"/accounts/{account_id}", status_code=303)
    except Exception as exc:
        request.session["account_error"] = str(exc)
        return RedirectResponse("/accounts", status_code=303)


def account_save(request: Request, account_id: int, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)),
                 csrf: str = Form(...), email: str = Form(""), locked: int = Form(0), expansion: int = Form(2),
                 gm_level: int = Form(0), password: str = Form("")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    try:
        gm_level = max(0, min(int(gm_level), 4))
        wowdb.update_account(all_config(db), account_id, email, locked, expansion, gm_level, password)
        log_action(db, user.id, "account_update", str(account_id), f"locked={locked}, expansion={expansion}, gm={gm_level}", request.client.host if request.client else None)
        request.session["account_flash"] = "Account gespeichert."
    except Exception as exc:
        request.session["account_flash"] = f"Fehler: {exc}"
    return RedirectResponse(f"/accounts/{account_id}", status_code=303)


def account_delete(request: Request, account_id: int, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)),
                   csrf: str = Form(...), confirm: str = Form("")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    account = wowdb.account_detail(all_config(db), account_id)
    if not account:
        raise HTTPException(404, "Account nicht gefunden")
    if confirm.strip().upper() != account["username"].upper():
        request.session["account_flash"] = "Löschen abgebrochen: Accountname wurde nicht korrekt bestätigt."
        return RedirectResponse(f"/accounts/{account_id}", status_code=303)
    username = wowdb.delete_account(all_config(db), account_id)
    log_action(db, user.id, "account_delete", str(account_id), username, request.client.host if request.client else None)
    request.session["account_error"] = f"Account {username} wurde gelöscht."
    return RedirectResponse("/accounts", status_code=303)


def characters(request: Request, q: str = "", db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    try:
        items, error = wowdb.search_characters(all_config(db), q, realm=selected_realm(request)), None
    except Exception as exc:
        items, error = [], str(exc)
    return render(request, "characters.html", {"title": "Charaktere", "items": items, "q": q, "error": error}, db)


def character_detail(request: Request, realm: str, guid: int, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    if realm not in REALMS:
        raise HTTPException(404, "Realm nicht gefunden")
    try:
        character, error = wowdb.character_detail(all_config(db), realm, guid), None
    except Exception as exc:
        character, error = None, str(exc)
    if not character and not error:
        raise HTTPException(404, "Charakter nicht gefunden")
    flash = request.session.pop("character_flash", None)
    return render(request, "character_detail.html", {"title": "Charakter", "character": character, "error": error, "flash": flash}, db)


def character_save(request: Request, realm: str, guid: int, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)),
                   csrf: str = Form(...), account: int = Form(...), name: str = Form(...), level: int = Form(...),
                   money_gold: int = Form(0), map_id: int = Form(...), zone: int = Form(...),
                   x: float = Form(...), y: float = Form(...), z: float = Form(...)):
    if realm not in REALMS:
        raise HTTPException(404, "Realm nicht gefunden")
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    try:
        wowdb.update_character(all_config(db), realm, guid, account, name, level, money_gold, map_id, zone, x, y, z)
        log_action(db, user.id, "character_update", f"{realm}:{guid}", name, request.client.host if request.client else None)
        request.session["character_flash"] = "Charakter gespeichert."
    except Exception as exc:
        request.session["character_flash"] = f"Fehler: {exc}"
    return RedirectResponse(f"/characters/{realm}/{guid}", status_code=303)


def character_transfer(request: Request, realm: str, guid: int, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)),
                       csrf: str = Form(...), action: str = Form("copy"), target_realm: str = Form(...),
                       target_name: str = Form(""), confirm: str = Form("")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    if action not in {"copy", "move"} or target_realm not in REALMS:
        raise HTTPException(400, "Ungültige Transferdaten")
    if target_realm == realm:
        request.session["character_flash"] = "Transfer abgebrochen: Bitte einen anderen Zielrealm auswählen."
        return RedirectResponse(f"/characters/{realm}/{guid}", status_code=303)
    cfg = all_config(db)
    character = wowdb.character_detail(cfg, realm, guid)
    if not character:
        raise HTTPException(404, "Charakter nicht gefunden")
    if confirm.strip().upper() != character["name"].upper():
        request.session["character_flash"] = "Transfer abgebrochen: Bitte den Charakternamen exakt bestätigen."
        return RedirectResponse(f"/characters/{realm}/{guid}", status_code=303)

    notices = []
    if character.get("online"):
        message = f"Charakter {character['name']} wird in 20 Sekunden fuer Kopieren/Verschieben ausgeloggt."
        notify_result = execute_gm_command(db, cfg, realm, f"notify {message}")
        record_command(db, user.id, realm, f"notify {message}", notify_result)
        notices.append(notify_result)
        time.sleep(20)
        kick_result = execute_gm_command(db, cfg, realm, f"kick {character['name']}")
        record_command(db, user.id, realm, f"kick {character['name']}", kick_result)
        notices.append(kick_result)
        for _ in range(35):
            time.sleep(1)
            refreshed = wowdb.character_detail(cfg, realm, guid)
            if not refreshed or not refreshed.get("online"):
                break
        character = wowdb.character_detail(cfg, realm, guid)
        if character and character.get("online"):
            request.session["character_flash"] = "Transfer abgebrochen: Charakter ist nach Warnung/Kick noch online. Bitte kurz später erneut versuchen."
            return RedirectResponse(f"/characters/{realm}/{guid}", status_code=303)

    try:
        result = wowdb.transfer_character(cfg, realm, guid, target_realm, action, target_name.strip() or character["name"])
        log_action(db, user.id, f"character_{action}", f"{realm}:{guid}->{target_realm}:{result['new_guid']}", result["name"], request.client.host if request.client else None)
    except Exception as exc:
        request.session["character_flash"] = short_flash(f"Transfer fehlgeschlagen: {exc}")
        return RedirectResponse(f"/characters/{realm}/{guid}", status_code=303)

    verb = "kopiert" if action == "copy" else "verschoben"
    extra = " Der Charakter wurde vorher ausgeloggt." if notices else ""
    request.session["character_flash"] = short_flash(f"Charakter {result['name']} wurde nach {result['target_realm_label']} {verb}. Neue GUID: {result['new_guid']}.{extra}")
    return RedirectResponse(f"/characters/{target_realm}/{result['new_guid']}", status_code=303)


def character_delete(request: Request, realm: str, guid: int, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)),
                     csrf: str = Form(...), confirm: str = Form("")):
    if realm not in REALMS:
        raise HTTPException(404, "Realm nicht gefunden")
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    character = wowdb.character_detail(all_config(db), realm, guid)
    if not character:
        raise HTTPException(404, "Charakter nicht gefunden")
    if confirm.strip().lower() != character["name"].lower():
        request.session["character_flash"] = "Löschen abgebrochen: Charaktername wurde nicht korrekt bestätigt."
        return RedirectResponse(f"/characters/{realm}/{guid}", status_code=303)
    name = wowdb.delete_character(all_config(db), realm, guid)
    log_action(db, user.id, "character_delete", f"{realm}:{guid}", name, request.client.host if request.client else None)
    request.session["character_flash"] = f"Charakter {name} wurde gelöscht."
    return RedirectResponse("/characters", status_code=303)


def gm_console(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    cfg = all_config(db)
    realm = selected_realm(request)
    lang = request.session.get("lang") or cfg.get("language") or "de"
    try:
        commands = normalize_db_commands(wowdb.gm_commands_from_db(cfg, realm), user.gm_level, lang)
        source_error = None
    except Exception as exc:
        commands = allowed_commands(user.gm_level)
        source_error = str(exc)
    try:
        all_chars = wowdb.character_choices(cfg, realm, online_only=False)
        online_chars = wowdb.character_choices(cfg, realm, online_only=True)
        character_error = None
    except Exception as exc:
        all_chars, online_chars, character_error = [], [], str(exc)
    try:
        events = wowdb.game_events(cfg, realm)
    except Exception:
        events = []
    actions = localized_actions(lang, user.gm_level) + event_actions(events, lang, user.gm_level)
    grouped = {}
    for command in commands:
        grouped.setdefault(command["category"], []).append(command)
    tab_data = []
    for tab_id, de, en in TABS:
        if tab_id in {"favorites", "raw"}:
            items = []
        else:
            items = [a for a in actions if a["tab"] == tab_id]
        tab_data.append({"id": tab_id, "label": en if lang == "en" else de, "actions": items})
    flash = request.session.pop("flash", None)
    active_tab = request.query_params.get("tab") or request.session.pop("gm_active_tab", None) or "favorites"
    if active_tab not in {tab["id"] for tab in tab_data}:
        active_tab = "favorites"
    favorite_ids = get_config(db, f"gm_favorites_{user.id}", []) or []
    return render(request, "gm.html", {
        "title": "GM-Befehle",
        "commands": commands,
        "grouped_commands": grouped,
        "source_error": source_error,
        "character_error": character_error,
        "all_chars": all_chars,
        "online_chars": online_chars,
        "tabs": tab_data,
        "flash": flash,
        "active_tab": active_tab,
        "favorite_ids": favorite_ids,
    }, db)


async def gm_favorites(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(current_user)):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf")):
        raise HTTPException(400, "CSRF")
    favorites = [item for item in str(form.get("favorites", "")).split(",") if item]
    set_config(db, f"gm_favorites_{user.id}", favorites)
    return JSONResponse({"ok": True, "favorites": favorites})


async def gm_action(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    form_data = await request.form()
    form = {key: value for key, value in form_data.items()}
    csrf = form.get("csrf")
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    action_id = form.get("action_id")
    cfg = all_config(db)
    realm = selected_realm(request)
    lang = request.session.get("lang") or cfg.get("language") or "de"
    try:
        events = wowdb.game_events(cfg, realm)
    except Exception:
        events = []
    actions = localized_actions(lang, user.gm_level) + event_actions(events, lang, user.gm_level)
    action = next((item for item in actions if item["id"] == action_id), None)
    if not action:
        raise HTTPException(404, "Aktion nicht gefunden")
    if action.get("character") == "online" and form.get("character"):
        online_names = {row["name"] for row in wowdb.character_choices(cfg, realm, online_only=True)}
        if form["character"] not in online_names:
            raise HTTPException(400, "Dieser Befehl braucht einen online Charakter")
    command = build_command(action, form)
    result = execute_gm_command(db, cfg, realm, command)
    record_command(db, user.id, realm, command, result)
    log_action(db, user.id, "gm_action", realm, f"{action['label']}: {command} -> {result}", request.client.host if request.client else None)
    request.session["flash"] = result
    tab = form.get("active_tab") or action.get("tab") or "favorites"
    request.session["gm_active_tab"] = tab
    return RedirectResponse(f"/gm?tab={tab}", status_code=303)


def gm_run(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1)), csrf: str = Form(...), command: str = Form(...), realm: str = Form("normal"), active_tab: str = Form("raw")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    allowed = [c["template"].split()[0] for c in allowed_commands(user.gm_level)]
    if command.split()[0] not in allowed and user.gm_level < 3:
        raise HTTPException(403, "Befehl nicht erlaubt")
    result = execute_gm_command(db, all_config(db), realm, command)
    record_command(db, user.id, realm, command, result)
    log_action(db, user.id, "gm_command", realm, command, request.client.host if request.client else None)
    request.session["flash"] = result
    request.session["gm_active_tab"] = active_tab or "raw"
    return RedirectResponse(f"/gm?tab={active_tab or 'raw'}", status_code=303)


def server(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(2))):
    cfg = all_config(db)
    overview = collect_server_overview(cfg, selected_realm(request))
    result = request.session.pop("server_result", None)
    return render(request, "server.html", {"title": "Server", "overview": overview, "result": result}, db)


async def server_extra_info(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf")):
        raise HTTPException(400, "CSRF")
    password = str(form.get("password") or "")
    cfg = all_config(db)
    if not verify_reauth_password(user, password, cfg):
        log_action(db, user.id, "server_extra_info_denied", "server", "Falsches Passwort bei zusätzlicher Serverinformation.", request.client.host if request.client else None)
        overview = collect_server_overview(cfg, selected_realm(request))
        return render(request, "server.html", {"title": "Server", "overview": overview, "result": "Passwortbestätigung fehlgeschlagen."}, db)
    extra_info = collect_sensitive_server_info(cfg)
    log_action(db, user.id, "server_extra_info_view", "server", "Zusätzliche Serverinformationen geöffnet.", request.client.host if request.client else None)
    overview = collect_server_overview(cfg, selected_realm(request))
    return render(request, "server.html", {"title": "Server", "overview": overview, "extra_info": extra_info, "result": "Zusätzliche Serverinformationen freigeschaltet."}, db)


def verify_reauth_password(user: PanelUser, password: str, cfg: dict) -> bool:
    if not password:
        return False
    if user.password_hash and verify_password(password, user.password_hash):
        return True
    try:
        account = None
        if user.wow_account_id:
            account = wowdb.account_by_id_for_login(cfg["mysql"], cfg["mysql"]["auth_db"], int(user.wow_account_id))
        account = account or wowdb.account_by_username(cfg["mysql"], cfg["mysql"]["auth_db"], user.username)
        return bool(account and verify_azeroth_password(account["username"], password, account))
    except Exception:
        return False


def collect_sensitive_server_info(cfg: dict) -> list[dict]:
    settings = get_settings()
    sections = [
        {"title": "Webpanel", "rows": [
            ("Basis-URL", settings.app_base_url),
            ("Sprache", cfg.get("language")),
            ("Panel-Datenbank-URL", settings.panel_db_url),
            ("App Secret Key", settings.app_secret_key),
            ("Setup abgeschlossen", cfg.get("setup_complete")),
            ("Webpanel-Dienstbenutzer", "wowpanel"),
            ("Webpanel-Root-Benutzer", "root"),
            ("Webpanel-Root-Passwort", cfg.get("webpanel_root_password") or "nicht im Webpanel gespeichert; Linux kann das Root-Passwort nicht im Klartext auslesen"),
            ("Webpanel-SSH-Benutzer", "nicht im Webpanel gespeichert"),
            ("Webpanel-SSH-Passwort", "nicht im Webpanel gespeichert"),
        ]},
        {"title": "WoW-Server SSH", "rows": [
            ("Host/IP", cfg["server"].get("wow_host")),
            ("SSH-Port", cfg["server"].get("ssh_port")),
            ("SSH-Benutzer", cfg["server"].get("ssh_user")),
            ("SSH-Passwort", cfg["server"].get("ssh_password")),
            ("Root-Benutzer", "root"),
            ("Root-Passwort", cfg["server"].get("root_password") or "nicht separat im Webpanel gespeichert; Linux kann das Root-Passwort nicht im Klartext auslesen"),
            ("Sudo-Passwort des SSH-Benutzers", cfg["server"].get("ssh_password")),
            ("Normal-Realm Pfad", cfg["server"].get("normal_path")),
            ("Playerbot-Realm Pfad", cfg["server"].get("playerbot_path")),
        ]},
        {"title": "WoW-MySQL", "rows": [
            ("Host/IP", cfg["mysql"].get("host")),
            ("Port", cfg["mysql"].get("port")),
            ("Benutzer", cfg["mysql"].get("user")),
            ("Passwort", cfg["mysql"].get("password")),
            ("Root-Benutzer", cfg["mysql"].get("root_user") or "root"),
            ("Root-Passwort", cfg["mysql"].get("root_password") or "nicht im Webpanel gespeichert; MariaDB/MySQL gibt Passwörter nicht im Klartext aus"),
            ("Auth-Datenbank", cfg["mysql"].get("auth_db")),
            ("World-Datenbank Normal", cfg["mysql"].get("world_db")),
            ("Characters-Datenbank Normal", cfg["mysql"].get("characters_db")),
            ("World-Datenbank Playerbot", cfg["mysql"].get("pb_world_db")),
            ("Characters-Datenbank Playerbot", cfg["mysql"].get("pb_characters_db")),
            ("Playerbots-Datenbank", cfg["mysql"].get("playerbots_db")),
        ]},
        {"title": "Ports & Realms", "rows": [
            ("Authserver-Port", cfg["realms"].get("auth_port")),
            ("Normal-Realm World-Port", cfg["realms"].get("normal_world_port")),
            ("Playerbot-Realm World-Port", cfg["realms"].get("playerbot_world_port")),
            ("Normal-Realm SOAP", f"{cfg['gm_transport'].get('normal_host')}:{cfg['gm_transport'].get('normal_port')}"),
            ("Playerbot-Realm SOAP", f"{cfg['gm_transport'].get('playerbot_host')}:{cfg['gm_transport'].get('playerbot_port')}"),
        ]},
        {"title": "GM-Transport / SOAP", "rows": [
            ("Modus", cfg["gm_transport"].get("mode")),
            ("Benutzer", cfg["gm_transport"].get("username")),
            ("Passwort", cfg["gm_transport"].get("password")),
        ]},
        {"title": "SOAP CMS", "rows": [
            ("Zweck", "Externer CMS-/FusionCMS-Zugriff auf AzerothCore SOAP"),
            ("Benutzer", (cfg.get("soap_cms") or {}).get("username") or "nicht eingerichtet"),
            ("Passwort", (cfg.get("soap_cms") or {}).get("password") or "nicht eingerichtet"),
            ("Account-ID", (cfg.get("soap_cms") or {}).get("account_id") or "unbekannt"),
            ("GM-Level", (cfg.get("soap_cms") or {}).get("gm_level") or "3 oder 4 empfohlen"),
            ("Auth-Datenbank", (cfg.get("soap_cms") or {}).get("auth_db") or cfg["mysql"].get("auth_db")),
            ("Normal-Realm SOAP", f"{(cfg.get('soap_cms') or {}).get('normal_host') or cfg['gm_transport'].get('normal_host')}:{(cfg.get('soap_cms') or {}).get('normal_port') or cfg['gm_transport'].get('normal_port')}"),
            ("Playerbot-Realm SOAP", f"{(cfg.get('soap_cms') or {}).get('playerbot_host') or cfg['gm_transport'].get('playerbot_host')}:{(cfg.get('soap_cms') or {}).get('playerbot_port') or cfg['gm_transport'].get('playerbot_port')}"),
            ("Ein Account oder zwei?", "Ein Account reicht, weil beide Worldserver dieselbe acore_auth-Datenbank verwenden."),
            ("Unterschiedliche Ports?", "Ja. Jeder Worldserver hat seinen eigenen SOAP-Port."),
        ]},
        {"title": "Config-Dateien", "rows": [
            ("Authserver", f"{cfg['server'].get('normal_path')}/etc/authserver.conf"),
            ("Worldserver Normal", f"{cfg['server'].get('normal_path')}/etc/worldserver.conf"),
            ("AHBot Normal", f"{cfg['server'].get('normal_path')}/etc/modules/mod_ahbot.conf"),
            ("Worldserver Playerbot", f"{cfg['server'].get('playerbot_path')}/etc/worldserver.conf"),
            ("Playerbots", f"{cfg['server'].get('playerbot_path')}/etc/modules/playerbots.conf"),
            ("AHBot Playerbot", f"{cfg['server'].get('playerbot_path')}/etc/modules/mod_ahbot.conf"),
        ]},
    ]
    sections.extend(remote_wow_config_connection_sections(cfg))
    try:
        sections.append({"title": "Webpanel-Server lokal erkannt", "text": local_sensitive_system_info()})
    except Exception as exc:
        sections.append({"title": "Webpanel-Server lokal erkannt", "text": f"Lokale Abfrage fehlgeschlagen: {exc}"})
    try:
        env_path = Path(".env")
        if env_path.exists():
            sections.append({"title": "Webpanel .env", "text": env_path.read_text(encoding="utf-8", errors="replace")})
        else:
            sections.append({"title": "Webpanel .env", "text": ".env nicht gefunden."})
    except Exception as exc:
        sections.append({"title": "Webpanel .env", "text": f".env konnte nicht gelesen werden: {exc}"})
    try:
        code, out, err = SSHClient(cfg["server"]).run("""
hostname -f 2>/dev/null || hostname
echo __IPS__
ip -o addr show | awk '{print $2 " " $3 " " $4}'
echo __ROUTES__
ip route
echo __LISTEN__
ss -ltnp 2>/dev/null | sed -n '1,80p'
echo __USERS__
getent passwd klaus wowpanel acore 2>/dev/null || true
""", timeout=10)
        sections.append({"title": "Vom WoW-Server erkannt", "text": out if code == 0 else (out + err)})
    except Exception as exc:
        sections.append({"title": "Vom WoW-Server erkannt", "text": f"SSH-Abfrage fehlgeschlagen: {exc}"})
    return sections


def remote_wow_config_connection_sections(cfg: dict) -> list[dict]:
    paths = [
        ("Normal Authserver", f"{cfg['server'].get('normal_path')}/etc/authserver.conf"),
        ("Normal Worldserver", f"{cfg['server'].get('normal_path')}/etc/worldserver.conf"),
        ("Normal AHBot", f"{cfg['server'].get('normal_path')}/etc/modules/mod_ahbot.conf"),
        ("Playerbot Authserver", f"{cfg['server'].get('playerbot_path')}/etc/authserver.conf"),
        ("Playerbot Worldserver", f"{cfg['server'].get('playerbot_path')}/etc/worldserver.conf"),
        ("Playerbots", f"{cfg['server'].get('playerbot_path')}/etc/modules/playerbots.conf"),
        ("Playerbot AHBot", f"{cfg['server'].get('playerbot_path')}/etc/modules/mod_ahbot.conf"),
    ]
    grep = r"grep -nE '^[[:space:]]*([A-Za-z0-9_.]+DatabaseInfo|WorldServerPort|SOAP\\.|Ra\\.|AuctionHouseBot\\.(Account|GUID)|AiPlayerbot\\.CommandServerPort)[[:space:]]*='"
    command_lines = []
    for label, path in paths:
        command_lines.append(f"echo '__FILE__ {shell_escape(label)}|{shell_escape(path)}'")
        command_lines.append(f"if test -f {shell_escape(path)}; then {grep} {shell_escape(path)} || true; else echo 'FEHLT'; fi")
    try:
        code, out, err = SSHClient(cfg["server"]).run("\n".join(command_lines), timeout=12)
        parsed = parse_remote_config_connections(out if code == 0 else out + err)
        raw_text = out if code == 0 else out + err
    except Exception as exc:
        parsed = []
        raw_text = f"SSH-Abfrage fehlgeschlagen: {exc}"
    sections = []
    if parsed:
        for file_info in parsed:
            sections.append({"title": f"WoW-Config: {file_info['label']}", "rows": file_info["rows"]})
    sections.append({"title": "WoW-Config: rohe Verbindungs-/Portzeilen", "text": raw_text})
    return sections


def shell_escape(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def parse_remote_config_connections(text_value: str) -> list[dict]:
    result = []
    current = None
    for raw_line in text_value.splitlines():
        if raw_line.startswith("__FILE__ "):
            meta = raw_line[len("__FILE__ "):]
            label, _, path = meta.partition("|")
            current = {"label": label, "path": path, "rows": [("Datei", path)]}
            result.append(current)
            continue
        if not current or not raw_line.strip() or raw_line.strip() == "FEHLT":
            if current and raw_line.strip() == "FEHLT":
                current["rows"].append(("Status", "Datei fehlt"))
            continue
        _, _, setting = raw_line.partition(":")
        key, sep, value = setting.partition("=")
        if not sep:
            current["rows"].append(("Rohzeile", setting.strip()))
            continue
        key = key.strip()
        value = value.strip().strip('"')
        current["rows"].append((key, value))
        if key.endswith("DatabaseInfo"):
            parts = value.split(";")
            if len(parts) >= 5:
                current["rows"].extend([
                    (f"{key} Host", parts[0]),
                    (f"{key} Port", parts[1]),
                    (f"{key} Benutzer", parts[2]),
                    (f"{key} Passwort", parts[3]),
                    (f"{key} Datenbank", parts[4]),
                ])
    return result


def local_sensitive_system_info() -> str:
    commands = [
        "hostname -f 2>/dev/null || hostname",
        "echo __IPS__",
        "ip -o addr show | awk '{print $2 \" \" $3 \" \" $4}'",
        "echo __ROUTES__",
        "ip route",
        "echo __LISTEN__",
        "ss -ltnp 2>/dev/null | sed -n '1,100p'",
        "echo __USERS__",
        "getent passwd klaus Klaus wowpanel www-data root 2>/dev/null || true",
        "echo __SYSTEMD__",
        "systemctl --no-pager --plain status wow-gm-webpanel nginx mariadb 2>/dev/null | sed -n '1,120p'",
    ]
    result = subprocess.run(["bash", "-lc", "\n".join(commands)], capture_output=True, text=True, timeout=10)
    return (result.stdout or "") + (result.stderr or "")


def server_action(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)), csrf: str = Form(...), target: str = Form(...), action: str = Form(...)):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    cfg = all_config(db)
    paths = {"auth": cfg["server"]["normal_path"] + "/bin/authserver", "normal": cfg["server"]["normal_path"] + "/bin/worldserver", "playerbot": cfg["server"]["playerbot_path"] + "/bin/worldserver"}
    code, out, err = SSHClient(cfg["server"]).service_action(paths[target], action)
    log_action(db, user.id, f"server_{action}", target, out + err, request.client.host if request.client else None)
    request.session["server_result"] = out or err or f"Exit {code}"
    return RedirectResponse("/server", status_code=303)


def configs(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    cfg = all_config(db)
    try:
        options, errors = load_main_configs(cfg)
    except Exception as exc:
        options, errors = [], [{"file": "SSH", "error": str(exc)}]
    logs = db.execute(text("""
        SELECT a.*, u.username
        FROM audit_log a LEFT JOIN panel_users u ON u.id=a.user_id
        WHERE a.action LIKE 'main_config_%'
        ORDER BY a.id DESC LIMIT 80
    """)).mappings().all()
    flash = request.session.pop("config_flash", None)
    return render(request, "configs.html", {
        "title": "Hauptconfigs",
        "options": options,
        "groups": grouped_main_configs(options),
        "summary": summarize_main_configs(options) if options else [],
        "errors": errors,
        "logs": logs,
        "flash": flash,
    }, db)


async def config_save(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf")):
        raise HTTPException(400, "CSRF")
    cfg = all_config(db)
    values = {key: str(value) for key, value in form.items() if str(key).startswith("cfg::")}
    try:
        restart_delay = max(10, int(str(form.get("restart_delay") or "60")))
    except ValueError:
        restart_delay = 60
    try:
        changes, touched_files = save_main_configs(cfg, values)
    except Exception as exc:
        request.session["config_flash"] = f"Speichern fehlgeschlagen: {exc}"
        log_action(db, user.id, "main_config_error", "normal", str(exc), request.client.host if request.client else None)
        return RedirectResponse("/configs", status_code=303)
    if not changes:
        request.session["config_flash"] = "Keine Änderungen gefunden."
        return RedirectResponse("/configs", status_code=303)
    details = "\n".join(f"{path}: {key}: {old} -> {new}" for path, key, old, new in changes)
    log_action(db, user.id, "main_config_change", "normal", details, request.client.host if request.client else None)
    notify = f"Server-Hauptkonfiguration wurde geändert. Bitte ausloggen: Neustart in {restart_delay} Sekunden."
    try:
        notify_result = execute_gm_command(db, cfg, "normal", f"notify {notify}")
    except Exception as exc:
        notify_result = f"GM-Meldung konnte nicht gesendet werden: {exc}"
    restart_results = []
    if any(path.endswith("worldserver.conf") for path in touched_files):
        try:
            restart_results.append(schedule_realm_restart(cfg, "normal", restart_delay))
        except Exception as exc:
            restart_results.append(f"Worldserver-Neustart konnte nicht geplant werden: {exc}")
    if any(path.endswith("authserver.conf") for path in touched_files):
        try:
            restart_results.append(schedule_auth_restart(cfg, restart_delay + 15))
        except Exception as exc:
            restart_results.append(f"Authserver-Neustart konnte nicht geplant werden: {exc}")
    record_command(db, user.id, "normal", f"notify {notify}", notify_result)
    record_command(db, user.id, "normal", f"main config restart {restart_delay}", "\n".join(restart_results))
    log_action(db, user.id, "main_config_apply_restart", "normal", notify_result + "\n" + "\n".join(restart_results), request.client.host if request.client else None)
    request.session["config_flash"] = f"{len(changes)} Änderung(en) gespeichert. {notify_result} {' '.join(restart_results)}"
    return RedirectResponse("/configs", status_code=303)


def ahbot(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(2))):
    cfg = all_config(db)
    realm = selected_realm(request)
    info = realm_cfg(cfg, realm)
    if not info["has_ahbot"]:
        return render(request, "ahbot.html", {"title": "AHBot", "unavailable": True, "stats": {}}, db)
    try:
        stats = wowdb.auction_stats(cfg, realm)
    except Exception as exc:
        stats = {"error": str(exc)}
    try:
        path, fields = load_ahbot(cfg, realm)
        config_error = None
    except Exception as exc:
        path, fields, config_error = "", [], str(exc)
    logs = db.execute(text("""
        SELECT a.*, u.username
        FROM audit_log a LEFT JOIN panel_users u ON u.id=a.user_id
        WHERE a.action LIKE 'ahbot_%'
        ORDER BY a.id DESC LIMIT 80
    """)).mappings().all()
    flash = request.session.pop("ahbot_flash", None)
    return render(request, "ahbot.html", {
        "title": "AHBot",
        "stats": stats,
        "path": path,
        "groups": grouped_fields(fields),
        "summary": summarize(fields) if fields else [],
        "config_error": config_error,
        "logs": logs,
        "flash": flash,
    }, db)


async def ahbot_save(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf")):
        raise HTTPException(400, "CSRF")
    cfg = all_config(db)
    realm = selected_realm(request)
    values = {key: str(value) for key, value in form.items() if key.startswith("AuctionHouseBot.")}
    try:
        restart_delay = max(10, int(str(form.get("restart_delay") or "60")))
    except ValueError:
        restart_delay = 60
    try:
        path, changes = save_ahbot(cfg, realm, values)
    except Exception as exc:
        request.session["ahbot_flash"] = f"Speichern fehlgeschlagen: {exc}"
        log_action(db, user.id, "ahbot_config_error", realm, str(exc), request.client.host if request.client else None)
        return RedirectResponse("/ahbot", status_code=303)
    if changes:
        details = "\n".join(f"{key}: {old} -> {new}" for key, old, new in changes)
        log_action(db, user.id, "ahbot_config_change", path, details, request.client.host if request.client else None)
        notify = f"Serverkonfiguration wurde geändert. Server startet in {restart_delay} Sekunden neu."
        try:
            notify_result = execute_gm_command(db, cfg, realm, f"notify {notify}")
        except Exception as exc:
            notify_result = f"Spielerwarnung konnte nicht per SOAP/RA gesendet werden: {exc}"
        try:
            restart_result = schedule_realm_restart(cfg, realm, restart_delay)
        except Exception as exc:
            restart_result = f"SSH-Neustart konnte nicht geplant werden: {exc}"
        record_command(db, user.id, realm, f"notify {notify}", notify_result)
        record_command(db, user.id, realm, f"ssh restart {restart_delay}", restart_result)
        log_action(db, user.id, "ahbot_apply_restart", realm, f"{notify_result}\n{restart_result}", request.client.host if request.client else None)
        request.session["ahbot_flash"] = f"{len(changes)} Einstellung(en) gespeichert. {notify_result} {restart_result}"
    else:
        request.session["ahbot_flash"] = "Keine Änderungen gefunden."
    return RedirectResponse("/ahbot", status_code=303)


def ahbot_reset(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)), csrf: str = Form(...), confirm: str = Form("")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    if confirm != "ORIGINAL":
        request.session["ahbot_flash"] = "Zurücksetzen abgebrochen: Bitte ORIGINAL als Bestätigung eingeben."
        return RedirectResponse("/ahbot", status_code=303)
    cfg = all_config(db)
    realm = selected_realm(request)
    path, changes, message = reset_ahbot(cfg, realm)
    details = message + ("\n" + "\n".join(f"{key}: {old} -> {new}" for key, old, new in changes) if changes else "")
    log_action(db, user.id, "ahbot_reset_original", path, details, request.client.host if request.client else None)
    request.session["ahbot_flash"] = message
    return RedirectResponse("/ahbot", status_code=303)


def playerbots(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(2))):
    cfg = all_config(db)
    info = realm_cfg(cfg, selected_realm(request))
    if not info["has_playerbots"]:
        return render(request, "playerbots.html", {"title": "Playerbots", "unavailable": True}, db)
    try:
        stats = {
            "characters": wowdb.scalar(cfg["mysql"], cfg["mysql"]["pb_characters_db"], "SELECT COUNT(*) FROM characters"),
            "online": wowdb.scalar(cfg["mysql"], cfg["mysql"]["pb_characters_db"], "SELECT COUNT(*) FROM characters WHERE online=1"),
            "accounts": wowdb.scalar(cfg["mysql"], cfg["mysql"]["auth_db"], "SELECT COUNT(*) FROM account WHERE username LIKE 'BOT%' OR username LIKE 'PLAYERBOT%'"),
        }
        error = None
    except Exception as exc:
        stats, error = {}, str(exc)
    config_error = None
    path = ""
    groups = []
    summary = []
    try:
        path, fields = load_playerbot(cfg)
        groups = grouped_playerbot_fields(fields)
        summary = summarize_playerbot(fields)
    except Exception as exc:
        config_error = str(exc)
    logs = db.execute(text("""
        SELECT a.*, u.username
        FROM audit_log a LEFT JOIN panel_users u ON u.id=a.user_id
        WHERE a.action LIKE 'playerbot_%'
        ORDER BY a.id DESC LIMIT 80
    """)).mappings().all()
    flash = request.session.pop("playerbot_flash", None)
    return render(request, "playerbots.html", {
        "title": "Playerbots",
        "stats": stats,
        "error": error,
        "path": path,
        "groups": groups,
        "summary": summary,
        "config_error": config_error,
        "logs": logs,
        "flash": flash,
    }, db)


async def playerbots_save(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    form = await request.form()
    if not verify_csrf(request, form.get("csrf")):
        raise HTTPException(400, "CSRF")
    cfg = all_config(db)
    values = {key: str(value) for key, value in form.items() if key.startswith(("AiPlayerbot.", "AIPlayerbot.", "Playerbots"))}
    try:
        restart_delay = max(10, int(str(form.get("restart_delay") or "60")))
    except ValueError:
        restart_delay = 60
    try:
        path, changes = save_playerbot(cfg, values)
    except Exception as exc:
        request.session["playerbot_flash"] = f"Speichern fehlgeschlagen: {exc}"
        log_action(db, user.id, "playerbot_config_error", "playerbot", str(exc), request.client.host if request.client else None)
        return RedirectResponse("/playerbots", status_code=303)
    if changes:
        details = "\n".join(f"{key}: {old} -> {new}" for key, old, new in changes)
        log_action(db, user.id, "playerbot_config_change", path, details, request.client.host if request.client else None)
        notify = f"Playerbot-Konfiguration wurde geändert. Playerbot-Realm startet in {restart_delay} Sekunden neu."
        try:
            notify_result = execute_gm_command(db, cfg, "playerbot", f"notify {notify}")
        except Exception as exc:
            notify_result = f"Spielerwarnung konnte nicht per SOAP/RA gesendet werden: {exc}"
        try:
            restart_result = schedule_realm_restart(cfg, "playerbot", restart_delay)
        except Exception as exc:
            restart_result = f"SSH-Neustart konnte nicht geplant werden: {exc}"
        record_command(db, user.id, "playerbot", f"notify {notify}", notify_result)
        record_command(db, user.id, "playerbot", f"ssh restart {restart_delay}", restart_result)
        log_action(db, user.id, "playerbot_apply_restart", "playerbot", f"{notify_result}\n{restart_result}", request.client.host if request.client else None)
        request.session["playerbot_flash"] = f"{len(changes)} Einstellung(en) gespeichert. {notify_result} {restart_result}"
    else:
        request.session["playerbot_flash"] = "Keine Änderungen gefunden."
    return RedirectResponse("/playerbots", status_code=303)


def playerbots_reset(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)), csrf: str = Form(...), confirm: str = Form("")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    if confirm != "ORIGINAL":
        request.session["playerbot_flash"] = "Zurücksetzen abgebrochen: Bitte ORIGINAL als Bestätigung eingeben."
        return RedirectResponse("/playerbots", status_code=303)
    cfg = all_config(db)
    try:
        path, changes, message = reset_playerbot(cfg)
    except Exception as exc:
        request.session["playerbot_flash"] = f"Zurücksetzen fehlgeschlagen: {exc}"
        return RedirectResponse("/playerbots", status_code=303)
    details = message + ("\n" + "\n".join(f"{key}: {old} -> {new}" for key, old, new in changes) if changes else "")
    log_action(db, user.id, "playerbot_reset_original", path, details, request.client.host if request.client else None)
    request.session["playerbot_flash"] = message
    return RedirectResponse("/playerbots", status_code=303)


def logs(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(2))):
    rows = db.execute(text("SELECT a.*, u.username FROM audit_log a LEFT JOIN panel_users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 200")).mappings().all()
    return render(request, "logs.html", {"title": "Logs", "items": rows}, db)


def backup(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    return render(request, "backup.html", {"title": "Backup/Restore"}, db)


def settings_page(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    return render(request, "settings.html", {"title": "Einstellungen"}, db)


def reset_post(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)), csrf: str = Form(...), confirm: str = Form("")):
    if not verify_csrf(request, csrf) or confirm != "ALLES ZURUECKSETZEN":
        raise HTTPException(400, "Bestätigung fehlt")
    set_config(db, "setup_complete", False)
    log_action(db, user.id, "reset_defaults", "webpanel", "Webpanel-Setup zurückgesetzt; WoW-Datenbanken unverändert.", request.client.host if request.client else None)
    request.session.clear()
    return RedirectResponse("/setup?force=1", status_code=303)


app = create_app()
