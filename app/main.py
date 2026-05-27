from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path

from .database import init_db, get_db
from .models import PanelUser
from .settings import get_settings
from .security import csrf_token, verify_csrf, hash_password, verify_password, verify_azeroth_password
from .services.config_store import bootstrap_defaults, all_config, set_config
from .services.audit import log_action
from .services import wowdb
from .services.realm import REALMS, selected_realm, realm_cfg
from .services.ssh_service import SSHClient, test_port
from .services.config_scanner import scan_remote, update_value
from .services.gm import allowed_commands, normalize_db_commands, record_command
from .services.gm_actions import TABS, build_command, event_actions, localized_actions
from .services.gm_transport import execute_gm_command
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
    app.add_api_route("/characters", characters, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/gm", gm_console, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/gm/run", gm_run, methods=["POST"])
    app.add_api_route("/gm/action", gm_action, methods=["POST"])
    app.add_api_route("/server", server, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/server/action", server_action, methods=["POST"])
    app.add_api_route("/configs", configs, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/configs/save", config_save, methods=["POST"])
    app.add_api_route("/ahbot", ahbot, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/playerbots", playerbots, methods=["GET"], response_class=HTMLResponse)
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
    user.gm_level = 3
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
        wowdb.update_account(all_config(db), account_id, email, locked, expansion, gm_level, password)
        log_action(db, user.id, "account_update", str(account_id), f"locked={locked}, expansion={expansion}, gm={gm_level}", request.client.host if request.client else None)
        request.session["account_flash"] = "Account gespeichert."
    except Exception as exc:
        request.session["account_flash"] = f"Fehler: {exc}"
    return RedirectResponse(f"/accounts/{account_id}", status_code=303)


def characters(request: Request, q: str = "", db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    try:
        items, error = wowdb.search_characters(all_config(db), q, realm=selected_realm(request)), None
    except Exception as exc:
        items, error = [], str(exc)
    return render(request, "characters.html", {"title": "Charaktere", "items": items, "q": q, "error": error}, db)


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
    }, db)


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
    return render(request, "server.html", {"title": "Server"}, db)


def server_action(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)), csrf: str = Form(...), target: str = Form(...), action: str = Form(...)):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    cfg = all_config(db)
    paths = {"auth": cfg["server"]["normal_path"] + "/bin/authserver", "normal": cfg["server"]["normal_path"] + "/bin/worldserver", "playerbot": cfg["server"]["playerbot_path"] + "/bin/worldserver"}
    code, out, err = SSHClient(cfg["server"]).service_action(paths[target], action)
    log_action(db, user.id, f"server_{action}", target, out + err, request.client.host if request.client else None)
    return render(request, "server.html", {"title": "Server", "result": out or err or f"Exit {code}"}, db)


def configs(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3))):
    cfg = all_config(db)
    realm = selected_realm(request)
    base = cfg["server"]["playerbot_path"] if realm == "playerbot" else cfg["server"]["normal_path"]
    roots = [base + "/etc", base + "/etc/modules"]
    try:
        options = scan_remote(SSHClient(cfg["server"]), roots)
    except Exception as exc:
        options = [{"file": "SSH", "key": "Fehler", "value": str(exc), "category": "Fehler"}]
    grouped = {}
    for option in options:
        if option.get("key") == "__error__":
            group = "Fehler"
        elif "ahbot" in option.get("file", "").lower():
            group = "AHBot"
        elif "playerbot" in option.get("file", "").lower():
            group = "Playerbots"
        elif "authserver" in option.get("file", "").lower():
            group = "Authserver"
        elif "worldserver" in option.get("file", "").lower():
            key = option.get("key", "").lower()
            if any(word in key for word in ["soap", "ra.", "console"]):
                group = "Remotezugriff"
            elif any(word in key for word in ["rate", "xp", "drop", "skill"]):
                group = "Raten & Gameplay"
            elif any(word in key for word in ["visibility", "map", "vmap", "mmap", "dbc"]):
                group = "Karten & Daten"
            else:
                group = "Worldserver"
        else:
            group = option.get("category") or "Sonstige"
        grouped.setdefault(group, {}).setdefault(option.get("file", "Unbekannt"), []).append(option)
    return render(request, "configs.html", {"title": "Configs", "options": options, "grouped_options": grouped}, db)


def config_save(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(3)), csrf: str = Form(...), path: str = Form(...), key: str = Form(...), value: str = Form(...)):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    ssh = SSHClient(all_config(db)["server"])
    content = ssh.read_file(path)
    backup = f"{path}.wowpanel.bak"
    ssh.run(f"cp {path} {backup}", timeout=10)
    ssh.write_file(path, update_value(content, key, value))
    log_action(db, user.id, "config_change", path, f"{key} geändert; Backup: {backup}", request.client.host if request.client else None)
    return RedirectResponse("/configs", status_code=303)


def ahbot(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(2))):
    info = realm_cfg(all_config(db), selected_realm(request))
    if not info["has_ahbot"]:
        return render(request, "ahbot.html", {"title": "AHBot", "unavailable": True, "stats": {}}, db)
    try:
        stats = wowdb.auction_stats(all_config(db), selected_realm(request))
    except Exception as exc:
        stats = {"error": str(exc)}
    return render(request, "ahbot.html", {"title": "AHBot", "stats": stats}, db)


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
    return render(request, "playerbots.html", {"title": "Playerbots", "stats": stats, "error": error}, db)


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
