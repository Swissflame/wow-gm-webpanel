from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def make_url(cfg: dict, database: str) -> str:
    return "mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4".format(
        user=cfg["user"], password=cfg["password"], host=cfg["host"], port=cfg.get("port", 3306), db=database
    )


def engine_for(mysql_cfg: dict, database: str) -> Engine:
    return create_engine(make_url(mysql_cfg, database), pool_pre_ping=True, future=True)


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


def dashboard_stats(cfg: dict) -> dict:
    mysql = cfg["mysql"]
    stats = {}
    stats["accounts"] = scalar(mysql, mysql["auth_db"], "SELECT COUNT(*) FROM account") or 0
    stats["characters"] = scalar(mysql, mysql["characters_db"], "SELECT COUNT(*) FROM characters") or 0
    stats["online"] = scalar(mysql, mysql["characters_db"], "SELECT COUNT(*) FROM characters WHERE online=1") or 0
    stats["auctions"] = scalar(mysql, mysql["characters_db"], "SELECT COUNT(*) FROM auctionhouse") or 0
    try:
        stats["pb_characters"] = scalar(mysql, mysql["pb_characters_db"], "SELECT COUNT(*) FROM characters") or 0
    except Exception:
        stats["pb_characters"] = "n/a"
    return stats


def online_players(cfg: dict) -> list[dict]:
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
    normal = rows(mysql, mysql["characters_db"], sql)
    for row in normal:
        row["realm"] = "Normal"
    try:
        pb = rows(mysql, mysql["pb_characters_db"], sql)
        for row in pb:
            row["realm"] = "Playerbot"
        normal.extend(pb)
    except Exception:
        pass
    return normal


def search_accounts(cfg: dict, query: str = "", limit: int = 100) -> list[dict]:
    mysql = cfg["mysql"]
    sql = """
    SELECT a.id, a.username, a.email, a.last_ip, a.last_login, a.locked, a.online,
           COALESCE(MAX(aa.gmlevel),0) AS gm_level
    FROM account a
    LEFT JOIN account_access aa ON aa.id = a.id
    WHERE (:q = '' OR a.username LIKE :likeq OR a.email LIKE :likeq)
    GROUP BY a.id
    ORDER BY a.id DESC LIMIT :limit
    """
    return rows(mysql, mysql["auth_db"], sql, {"q": query, "likeq": f"%{query}%", "limit": limit})


def search_characters(cfg: dict, query: str = "", limit: int = 100) -> list[dict]:
    mysql = cfg["mysql"]
    sql = """
    SELECT guid, account, name, level, race, class, gender, money, online, zone, map,
           ROUND(position_x,2) AS x, ROUND(position_y,2) AS y, ROUND(position_z,2) AS z
    FROM characters
    WHERE (:q = '' OR name LIKE :likeq)
    ORDER BY level DESC, name LIMIT :limit
    """
    data = rows(mysql, mysql["characters_db"], sql, {"q": query, "likeq": f"%{query}%", "limit": limit})
    for row in data:
        row["realm"] = "Normal"
    try:
        pb = rows(mysql, mysql["pb_characters_db"], sql, {"q": query, "likeq": f"%{query}%", "limit": limit})
        for row in pb:
            row["realm"] = "Playerbot"
        data.extend(pb)
    except Exception:
        pass
    return data[:limit]


def auction_stats(cfg: dict) -> dict:
    mysql = cfg["mysql"]
    sql = "SELECT COUNT(*) total, MIN(buyoutprice) min_buyout, MAX(buyoutprice) max_buyout, SUM(item_count) items FROM auctionhouse"
    return rows(mysql, mysql["characters_db"], sql)[0]
