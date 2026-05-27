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
from .services.ssh_service import SSHClient, test_port
from .services.config_scanner import scan_remote, update_value
from .services.gm import allowed_commands, record_command

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
    app.add_api_route("/dashboard", dashboard, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/online", online, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/accounts", accounts, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/characters", characters, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/gm", gm_console, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/gm/run", gm_run, methods=["POST"])
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
    context.setdefault("request", request)
    context.setdefault("csrf", csrf_token(request))
    context.setdefault("user", getattr(request.state, "user", None))
    context.setdefault("cfg", all_config(db) if db else {})
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


def dashboard(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(current_user)):
    cfg = all_config(db)
    status = {
        "auth": test_port(cfg["server"]["wow_host"], cfg["realms"]["auth_port"]),
        "normal": test_port(cfg["server"]["wow_host"], cfg["realms"]["normal_world_port"]),
        "playerbot": test_port(cfg["server"]["wow_host"], cfg["realms"]["playerbot_world_port"]),
    }
    try:
        stats = wowdb.dashboard_stats(cfg)
    except Exception as exc:
        stats = {"error": str(exc)}
    return render(request, "dashboard.html", {"title": "Dashboard", "status": status, "stats": stats}, db)


def online(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(0))):
    try:
        players = wowdb.online_players(all_config(db))
    except Exception as exc:
        players, error = [], str(exc)
    else:
        error = None
    return render(request, "online.html", {"title": "Online-Spieler", "players": players, "error": error}, db)


def accounts(request: Request, q: str = "", db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    return render(request, "accounts.html", {"title": "Accounts", "items": wowdb.search_accounts(all_config(db), q), "q": q}, db)


def characters(request: Request, q: str = "", db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    return render(request, "characters.html", {"title": "Charaktere", "items": wowdb.search_characters(all_config(db), q), "q": q}, db)


def gm_console(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1))):
    return render(request, "gm.html", {"title": "GM-Befehle", "commands": allowed_commands(user.gm_level)}, db)


def gm_run(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(1)), csrf: str = Form(...), command: str = Form(...), realm: str = Form("normal")):
    if not verify_csrf(request, csrf):
        raise HTTPException(400, "CSRF")
    allowed = [c["template"].split()[0] for c in allowed_commands(user.gm_level)]
    if command.split()[0] not in allowed and user.gm_level < 3:
        raise HTTPException(403, "Befehl nicht erlaubt")
    result = "SOAP/RA ist noch nicht in der Serverkonfiguration aktiviert. Befehl wurde protokolliert, aber nicht gesendet."
    record_command(db, user.id, realm, command, result)
    log_action(db, user.id, "gm_command", realm, command, request.client.host if request.client else None)
    return RedirectResponse("/gm", status_code=303)


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
    roots = [cfg["server"]["normal_path"] + "/etc", cfg["server"]["normal_path"] + "/etc/modules", cfg["server"]["playerbot_path"] + "/etc", cfg["server"]["playerbot_path"] + "/etc/modules"]
    try:
        options = scan_remote(SSHClient(cfg["server"]), roots)
    except Exception as exc:
        options = [{"file": "SSH", "key": "Fehler", "value": str(exc), "category": "Fehler"}]
    return render(request, "configs.html", {"title": "Configs", "options": options}, db)


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
    try:
        stats = wowdb.auction_stats(all_config(db))
    except Exception as exc:
        stats = {"error": str(exc)}
    return render(request, "ahbot.html", {"title": "AHBot", "stats": stats}, db)


def playerbots(request: Request, db: Session = Depends(get_db), user: PanelUser = Depends(require_level(2))):
    return render(request, "playerbots.html", {"title": "Playerbots"}, db)


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
