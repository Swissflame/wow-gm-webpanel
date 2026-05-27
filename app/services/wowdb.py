from contextlib import contextmanager
from datetime import datetime
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..security import azeroth_sha_pass_hash, azeroth_srp6_verifier


def make_url(cfg: dict, database: str) -> str:
    return "mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4".format(
        user=cfg["user"], password=cfg["password"], host=cfg["host"], port=cfg.get("port", 3306), db=database
    )


def engine_for(mysql_cfg: dict, database: str) -> Engine:
    return create_engine(make_url(mysql_cfg, database), pool_pre_ping=True, future=True, connect_args={"connect_timeout": 3})


@contextmanager
def connect(mysql_cfg: dict, database: str):
    engine = engine_for(mysql_cfg, database)
    with engine.connect() as conn:
        yield conn
    engine.dispose()


def scalar(mysql_cfg: dict, database: str, sql: str, params: dict | None = None):
    with connect(mysql_cfg, database) as conn:
        return conn.execute(text(sql), params or {}).scalar()


def rows(mysql_cfg: dict, database: str, sql: str, params: dict | None = None) -> list[dict]:
    with connect(mysql_cfg, database) as conn:
        return [dict(r._mapping) for r in conn.execute(text(sql), params or {})]


def account_by_username(mysql_cfg: dict, auth_db: str, username: str) -> dict | None:
    sql = """
    SELECT id, username, sha_pass_hash, salt, verifier, email, last_ip, last_login, locked, online, expansion
    FROM account WHERE username = :username LIMIT 1
    """
    result = rows(mysql_cfg, auth_db, sql, {"username": username.upper()})
    return result[0] if result else None


def gm_level(mysql_cfg: dict, auth_db: str, account_id: int) -> int:
    value = scalar(mysql_cfg, auth_db, "SELECT COALESCE(MAX(gmlevel), 0) FROM account_access WHERE id=:id", {"id": account_id})
    return int(value or 0)


def dashboard_stats(cfg: dict, realm: str = "normal") -> dict:
    mysql = cfg["mysql"]
    char_db = mysql["pb_characters_db"] if realm == "playerbot" else mysql["characters_db"]
    stats = {}
    stats["accounts"] = scalar(mysql, mysql["auth_db"], "SELECT COUNT(*) FROM account") or 0
    stats["characters"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM characters") or 0
    stats["online"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM characters WHERE online=1") or 0
    stats["auctions"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM auctionhouse") or 0
    stats["pb_characters"] = scalar(mysql, mysql["pb_characters_db"], "SELECT COUNT(*) FROM characters") if realm == "playerbot" else "n/a"
    return stats


def online_players(cfg: dict, realm: str = "normal") -> list[dict]:
    mysql = cfg["mysql"]
    sql = """
    SELECT c.guid, c.name, c.account, a.username, c.level, c.race, c.class, c.zone, c.map,
           ROUND(c.position_x, 2) AS x, ROUND(c.position_y, 2) AS y, ROUND(c.position_z, 2) AS z,
           COALESCE(MAX(aa.gmlevel), 0) AS gm_level
    FROM characters c
    LEFT JOIN {auth_db}.account a ON a.id = c.account
    LEFT JOIN {auth_db}.account_access aa ON aa.id = c.account
    WHERE c.online = 1
    GROUP BY c.guid
    ORDER BY c.name
    """.format(auth_db=mysql["auth_db"])
    char_db = mysql["pb_characters_db"] if realm == "playerbot" else mysql["characters_db"]
    data = rows(mysql, char_db, sql)
    for row in data:
        row["realm"] = "Playerbot" if realm == "playerbot" else "Normal"
    return data


BOT_ACCOUNT_FILTER = "a.username NOT REGEXP '^(RNDBOT|BOT|PLAYERBOT|AHBOT|ACORE_WEBPANEL)'"


def search_accounts(cfg: dict, query: str = "", limit: int = 500, include_bots: bool = False) -> list[dict]:
    mysql = cfg["mysql"]
    bot_clause = "1=1" if include_bots else BOT_ACCOUNT_FILTER
    sql = """
    SELECT a.id, a.username, a.email, a.last_ip, a.last_login, a.locked, a.online,
           a.expansion,
           COALESCE(MAX(aa.gmlevel),0) AS gm_level,
           COALESCE(nc.char_count, 0) AS normal_chars,
           COALESCE(pc.char_count, 0) AS playerbot_chars
    FROM account a
    LEFT JOIN account_access aa ON aa.id = a.id
    LEFT JOIN (SELECT account, COUNT(*) char_count FROM {characters_db}.characters GROUP BY account) nc ON nc.account = a.id
    LEFT JOIN (SELECT account, COUNT(*) char_count FROM {pb_characters_db}.characters GROUP BY account) pc ON pc.account = a.id
    WHERE ({bot_clause}) AND (:q = '' OR a.username LIKE :likeq OR a.email LIKE :likeq)
    GROUP BY a.id
    ORDER BY (COALESCE(nc.char_count,0) + COALESCE(pc.char_count,0)) DESC, a.last_login DESC, a.id DESC
    LIMIT :limit
    """.format(characters_db=mysql["characters_db"], pb_characters_db=mysql["pb_characters_db"], bot_clause=bot_clause)
    return rows(mysql, mysql["auth_db"], sql, {"q": query, "likeq": f"%{query}%", "limit": limit})


def account_detail(cfg: dict, account_id: int) -> dict | None:
    mysql = cfg["mysql"]
    sql = """
    SELECT a.id, a.username, a.email, a.reg_mail, a.joindate, a.last_ip, a.last_attempt_ip,
           a.last_login, a.locked, a.online, a.expansion, a.failed_logins, a.mutetime,
           a.mutereason, a.muteby, a.locale, a.os,
           COALESCE(MAX(aa.gmlevel),0) AS gm_level
    FROM account a
    LEFT JOIN account_access aa ON aa.id = a.id
    WHERE a.id = :id
    GROUP BY a.id
    LIMIT 1
    """
    data = rows(mysql, mysql["auth_db"], sql, {"id": account_id})
    if not data:
        return None
    account = data[0]
    account["access"] = rows(mysql, mysql["auth_db"], "SELECT id, gmlevel, RealmID FROM account_access WHERE id=:id ORDER BY RealmID", {"id": account_id})
    account["bans"] = rows(mysql, mysql["auth_db"], "SELECT bandate, unbandate, bannedby, banreason, active FROM account_banned WHERE id=:id ORDER BY bandate DESC LIMIT 20", {"id": account_id})
    account["characters_normal"] = account_characters(mysql, mysql["characters_db"], account_id, "Normal")
    account["characters_playerbot"] = account_characters(mysql, mysql["pb_characters_db"], account_id, "Playerbot")
    return account


def account_characters(mysql: dict, char_db: str, account_id: int, realm: str) -> list[dict]:
    sql = """
    SELECT guid, name, level, race, class, gender, money, online, zone, map,
           ROUND(position_x,2) AS x, ROUND(position_y,2) AS y, ROUND(position_z,2) AS z
    FROM characters
    WHERE account = :id
    ORDER BY online DESC, level DESC, name
    """
    data = rows(mysql, char_db, sql, {"id": account_id})
    for row in data:
        row["realm"] = realm
    return data


def account_table_columns(mysql_cfg: dict, auth_db: str, table: str = "account") -> set[str]:
    return {row["Field"] for row in rows(mysql_cfg, auth_db, f"DESCRIBE {table}")}


def create_account(cfg: dict, username: str, password: str, email: str = "", expansion: int = 2, gm_level_value: int = 0):
    mysql = cfg["mysql"]
    auth_db = mysql["auth_db"]
    username = username.strip().upper()
    if not username or len(username) > 32:
        raise ValueError("Accountname muss 1 bis 32 Zeichen haben.")
    if len(password) < 6:
        raise ValueError("Passwort muss mindestens 6 Zeichen haben.")
    if account_by_username(mysql, auth_db, username):
        raise ValueError("Dieser Account existiert bereits.")
    columns = account_table_columns(mysql, auth_db)
    salt = os.urandom(32)
    values = {
        "username": username,
        "email": email.strip(),
        "reg_mail": email.strip(),
        "joindate": datetime.utcnow(),
        "last_ip": "127.0.0.1",
        "last_attempt_ip": "127.0.0.1",
        "locked": 0,
        "online": 0,
        "expansion": int(expansion),
        "failed_logins": 0,
        "locale": 0,
        "os": "",
        "salt": salt,
        "verifier": azeroth_srp6_verifier(username, password, salt),
        "sha_pass_hash": azeroth_sha_pass_hash(username, password),
    }
    insert_values = {key: value for key, value in values.items() if key in columns}
    keys = ", ".join(insert_values.keys())
    bind_keys = ", ".join(f":{key}" for key in insert_values)
    with engine_for(mysql, auth_db).begin() as conn:
        result = conn.execute(text(f"INSERT INTO account ({keys}) VALUES ({bind_keys})"), insert_values)
        account_id = int(result.lastrowid)
        _set_account_access(conn, account_id, int(gm_level_value))
    return account_id


def update_account(cfg: dict, account_id: int, email: str, locked: int, expansion: int, gm_level_value: int, password: str = ""):
    mysql = cfg["mysql"]
    auth_db = mysql["auth_db"]
    columns = account_table_columns(mysql, auth_db)
    updates = {
        "email": email.strip(),
        "reg_mail": email.strip(),
        "locked": int(locked),
        "expansion": int(expansion),
    }
    update_values = {key: value for key, value in updates.items() if key in columns}
    update_values["id"] = int(account_id)
    password = (password or "").strip()
    if password:
        account = account_detail(cfg, account_id)
        if not account:
            raise ValueError("Account nicht gefunden.")
        salt = os.urandom(32)
        if "salt" in columns:
            update_values["salt"] = salt
        if "verifier" in columns:
            update_values["verifier"] = azeroth_srp6_verifier(account["username"], password, salt)
        if "sha_pass_hash" in columns:
            update_values["sha_pass_hash"] = azeroth_sha_pass_hash(account["username"], password)
    assignments = ", ".join(f"{key}=:{key}" for key in update_values if key != "id")
    with engine_for(mysql, auth_db).begin() as conn:
        conn.execute(text(f"UPDATE account SET {assignments} WHERE id=:id"), update_values)
        _set_account_access(conn, int(account_id), int(gm_level_value))


def _set_account_access(conn, account_id: int, gm_level_value: int):
    conn.execute(text("DELETE FROM account_access WHERE id=:id AND RealmID=-1"), {"id": account_id})
    if gm_level_value > 0:
        conn.execute(text("INSERT INTO account_access (id, gmlevel, RealmID) VALUES (:id, :gm, -1)"), {"id": account_id, "gm": gm_level_value})


def search_characters(cfg: dict, query: str = "", limit: int = 100, realm: str = "normal") -> list[dict]:
    mysql = cfg["mysql"]
    sql = """
    SELECT guid, account, name, level, race, class, gender, money, online, zone, map,
           ROUND(position_x,2) AS x, ROUND(position_y,2) AS y, ROUND(position_z,2) AS z
    FROM characters
    WHERE (:q = '' OR name LIKE :likeq)
    ORDER BY level DESC, name LIMIT :limit
    """
    char_db = mysql["pb_characters_db"] if realm == "playerbot" else mysql["characters_db"]
    data = rows(mysql, char_db, sql, {"q": query, "likeq": f"%{query}%", "limit": limit})
    for row in data:
        row["realm"] = "Playerbot" if realm == "playerbot" else "Normal"
    return data[:limit]


def character_choices(cfg: dict, realm: str = "normal", online_only: bool = False, limit: int = 500) -> list[dict]:
    mysql = cfg["mysql"]
    char_db = mysql["pb_characters_db"] if realm == "playerbot" else mysql["characters_db"]
    where = "WHERE online = 1" if online_only else ""
    sql = f"""
    SELECT guid, name, level, race, class, online
    FROM characters
    {where}
    ORDER BY online DESC, name
    LIMIT :limit
    """
    return rows(mysql, char_db, sql, {"limit": limit})


def auction_stats(cfg: dict, realm: str = "normal") -> dict:
    mysql = cfg["mysql"]
    char_db = mysql["pb_characters_db"] if realm == "playerbot" else mysql["characters_db"]
    sql = "SELECT COUNT(*) total, MIN(buyoutprice) min_buyout, MAX(buyoutprice) max_buyout, COUNT(itemguid) items FROM auctionhouse"
    return rows(mysql, char_db, sql)[0]


def gm_commands_from_db(cfg: dict, realm: str = "normal") -> list[dict]:
    mysql = cfg["mysql"]
    world_db = mysql["pb_world_db"] if realm == "playerbot" else mysql["world_db"]
    return rows(mysql, world_db, "SELECT name, security, help FROM command ORDER BY security, name")


def game_events(cfg: dict, realm: str = "normal") -> list[dict]:
    mysql = cfg["mysql"]
    world_db = mysql["pb_world_db"] if realm == "playerbot" else mysql["world_db"]
    sql = """
    SELECT eventEntry AS id, description
    FROM game_event
    WHERE description IS NOT NULL AND description <> ''
    ORDER BY description
    """
    return rows(mysql, world_db, sql)
