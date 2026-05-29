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
    columns = account_table_columns(mysql_cfg, auth_db)
    wanted = ["id", "username", "sha_pass_hash", "salt", "verifier", "email", "last_ip", "last_login", "locked", "online", "expansion"]
    selected = [name for name in wanted if name in columns]
    sql = f"SELECT {', '.join(selected)} FROM account WHERE username = :username LIMIT 1"
    result = rows(mysql_cfg, auth_db, sql, {"username": username.upper()})
    return result[0] if result else None


def account_by_id_for_login(mysql_cfg: dict, auth_db: str, account_id: int) -> dict | None:
    columns = account_table_columns(mysql_cfg, auth_db)
    wanted = ["id", "username", "sha_pass_hash", "salt", "verifier", "email", "last_ip", "last_login", "locked", "online", "expansion"]
    selected = [name for name in wanted if name in columns]
    sql = f"SELECT {', '.join(selected)} FROM account WHERE id = :id LIMIT 1"
    result = rows(mysql_cfg, auth_db, sql, {"id": int(account_id)})
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


BOT_ACCOUNT_FILTER = "a.username NOT LIKE '%BOT%' AND a.username <> 'ACORE_WEBPANEL'"


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
        row["realm_key"] = "playerbot" if realm == "Playerbot" else "normal"
    return data


def character_database(mysql: dict, realm: str) -> str:
    return mysql["pb_characters_db"] if realm == "playerbot" else mysql["characters_db"]


ITEM_CLASSES = {
    0: ("Verbrauchbar", {0: "Verbrauchbar", 1: "Trank", 2: "Elixier", 3: "Fläschchen", 4: "Schriftrolle", 5: "Essen & Trinken", 6: "Itemverbesserung", 7: "Bandage", 8: "Sonstiges"}),
    1: ("Taschen", {0: "Tasche", 1: "Seelentasche", 2: "Kräutertasche", 3: "Verzauberertasche", 4: "Ingenieurstasche", 5: "Edelsteintasche", 6: "Bergbautasche", 7: "Lederertasche", 8: "Inschriftlertasche"}),
    2: ("Waffen", {0: "Einhändige Axt", 1: "Zweihändige Axt", 2: "Bogen", 3: "Schusswaffe", 4: "Einhändiger Streitkolben", 5: "Zweihändiger Streitkolben", 6: "Stangenwaffe", 7: "Einhändiges Schwert", 8: "Zweihändiges Schwert", 10: "Stab", 13: "Faustwaffe", 14: "Sonstige Waffe", 15: "Dolch", 16: "Wurfwaffe", 18: "Armbrust", 19: "Zauberstab", 20: "Angel"}),
    3: ("Edelsteine", {0: "Rot", 1: "Blau", 2: "Gelb", 3: "Violett", 4: "Grün", 5: "Orange", 6: "Meta", 7: "Einfach", 8: "Prismatisch"}),
    4: ("Rüstung", {0: "Sonstige Rüstung", 1: "Stoff", 2: "Leder", 3: "Kette", 4: "Platte", 6: "Schild", 7: "Buchband", 8: "Götze", 9: "Totem", 10: "Siegel"}),
    5: ("Reagenzien", {0: "Reagenz"}),
    6: ("Munition", {2: "Pfeile", 3: "Kugeln"}),
    7: ("Handwerkswaren", {0: "Handwerksware", 1: "Teile", 2: "Sprengstoff", 3: "Geräte", 4: "Juwelenschleifen", 5: "Stoff", 6: "Leder", 7: "Metall & Stein", 8: "Fleisch", 9: "Kräuter", 10: "Elementar", 11: "Sonstiges", 12: "Verzaubern", 13: "Materialien", 14: "Rüstungsvz.", 15: "Waffenvz."}),
    8: ("Allgemein", {0: "Allgemein"}),
    9: ("Rezepte", {0: "Buch", 1: "Lederverarbeitung", 2: "Schneiderei", 3: "Ingenieurskunst", 4: "Schmiedekunst", 5: "Kochkunst", 6: "Alchemie", 7: "Erste Hilfe", 8: "Verzauberkunst", 9: "Angeln", 10: "Juwelenschleifen"}),
    10: ("Geld", {0: "Geld"}),
    11: ("Köcher", {2: "Köcher", 3: "Munitionsbeutel"}),
    12: ("Questitems", {0: "Questitem"}),
    13: ("Schlüssel", {0: "Schlüssel", 1: "Dietrich"}),
    14: ("Permanent", {0: "Permanent"}),
    15: ("Verschiedenes", {0: "Plunder", 1: "Reagenz", 2: "Begleiter", 3: "Feiertag", 4: "Sonstiges", 5: "Reittier"}),
    16: ("Glyphen", {1: "Krieger", 2: "Paladin", 3: "Jäger", 4: "Schurke", 5: "Priester", 6: "Todesritter", 7: "Schamane", 8: "Magier", 9: "Hexenmeister", 11: "Druide"}),
}

ITEM_QUALITIES = {
    0: "Schlecht", 1: "Gewöhnlich", 2: "Ungewöhnlich", 3: "Selten",
    4: "Episch", 5: "Legendär", 6: "Artefakt", 7: "Erbstück",
}

INVENTORY_TYPES = {
    0: "-", 1: "Kopf", 2: "Hals", 3: "Schulter", 4: "Hemd", 5: "Brust",
    6: "Taille", 7: "Beine", 8: "Füße", 9: "Handgelenk", 10: "Hände",
    11: "Finger", 12: "Schmuck", 13: "Einhändig", 14: "Schild", 15: "Distanz",
    16: "Rücken", 17: "Zweihändig", 18: "Tasche", 19: "Wappenrock",
    20: "Robe", 21: "Waffenhand", 22: "Schildhand", 23: "In Nebenhand",
    24: "Munition", 25: "Wurfwaffe", 26: "Distanz rechts", 28: "Relikt",
}


def item_class_options() -> list[dict]:
    return [{"id": key, "label": value[0], "subclasses": value[1]} for key, value in sorted(ITEM_CLASSES.items())]


def item_subclass_label(item_class: int, subclass: int) -> str:
    return ITEM_CLASSES.get(int(item_class), (f"Klasse {item_class}", {}))[1].get(int(subclass), f"Unterklasse {subclass}")


def item_class_label(item_class: int) -> str:
    return ITEM_CLASSES.get(int(item_class), (f"Klasse {item_class}", {}))[0]


def item_quality_label(quality: int) -> str:
    return ITEM_QUALITIES.get(int(quality), f"Qualität {quality}")


def inventory_type_label(inventory_type: int) -> str:
    return INVENTORY_TYPES.get(int(inventory_type), str(inventory_type))


def search_items(cfg: dict, filters: dict) -> dict:
    mysql = cfg["mysql"]
    limit = max(25, min(int(filters.get("limit") or 100), 500))
    page = max(1, int(filters.get("page") or 1))
    offset = (page - 1) * limit
    where = []
    params = {"limit": limit, "offset": offset}

    query = str(filters.get("q") or "").strip()
    if query:
        if query.isdigit():
            where.append("(entry = :entry OR name LIKE :likeq)")
            params["entry"] = int(query)
        else:
            where.append("name LIKE :likeq")
        params["likeq"] = f"%{query}%"

    item_class = filters.get("item_class")
    if item_class not in (None, ""):
        where.append("class = :class")
        params["class"] = int(item_class)

    subclass = filters.get("subclass")
    if subclass not in (None, ""):
        where.append("subclass = :subclass")
        params["subclass"] = int(subclass)

    quality = filters.get("quality")
    if quality not in (None, ""):
        where.append("Quality = :quality")
        params["quality"] = int(quality)

    min_level = filters.get("min_level")
    if min_level not in (None, ""):
        where.append("ItemLevel >= :min_level")
        params["min_level"] = int(min_level)

    max_level = filters.get("max_level")
    if max_level not in (None, ""):
        where.append("ItemLevel <= :max_level")
        params["max_level"] = int(max_level)

    clause = "WHERE " + " AND ".join(where) if where else ""
    order = "class, subclass, ItemLevel, RequiredLevel, name"
    if filters.get("sort") == "level_desc":
        order = "ItemLevel DESC, RequiredLevel DESC, class, subclass, name"
    elif filters.get("sort") == "name":
        order = "name, ItemLevel, entry"

    count = scalar(mysql, mysql["world_db"], f"SELECT COUNT(*) FROM item_template {clause}", params) or 0
    sql = f"""
    SELECT entry, name, class, subclass, Quality, ItemLevel, RequiredLevel, InventoryType,
           stackable, ContainerSlots, SellPrice, bonding, description
    FROM item_template
    {clause}
    ORDER BY {order}
    LIMIT :limit OFFSET :offset
    """
    data = rows(mysql, mysql["world_db"], sql, params)
    for row in data:
        row["class_label"] = item_class_label(row["class"])
        row["subclass_label"] = item_subclass_label(row["class"], row["subclass"])
        row["quality_label"] = item_quality_label(row["Quality"])
        row["inventory_label"] = inventory_type_label(row["InventoryType"])
    return {"items": data, "total": int(count), "page": page, "limit": limit, "pages": max(1, (int(count) + limit - 1) // limit)}


def character_detail(cfg: dict, realm: str, guid: int) -> dict | None:
    mysql = cfg["mysql"]
    char_db = character_database(mysql, realm)
    sql = """
    SELECT c.guid, c.account, a.username AS account_name, c.name, c.level, c.race, c.class, c.gender,
           c.money, c.online, c.zone, c.map,
           ROUND(c.position_x,2) AS x, ROUND(c.position_y,2) AS y, ROUND(c.position_z,2) AS z,
           c.totaltime, c.leveltime, c.logout_time, c.at_login, c.xp
    FROM characters c
    LEFT JOIN {auth_db}.account a ON a.id = c.account
    WHERE c.guid = :guid
    LIMIT 1
    """.format(auth_db=mysql["auth_db"])
    data = rows(mysql, char_db, sql, {"guid": int(guid)})
    if not data:
        return None
    char = data[0]
    char["realm_key"] = realm
    char["realm"] = "Playerbot" if realm == "playerbot" else "Normal"
    char["inventory_count"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM character_inventory WHERE guid=:guid", {"guid": int(guid)}) or 0
    char["quest_count"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM character_queststatus WHERE guid=:guid", {"guid": int(guid)}) or 0
    char["spell_count"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM character_spell WHERE guid=:guid", {"guid": int(guid)}) or 0
    char["achievement_count"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM character_achievement WHERE guid=:guid", {"guid": int(guid)}) or 0
    char["mail_count"] = scalar(mysql, char_db, "SELECT COUNT(*) FROM mail WHERE receiver=:guid", {"guid": int(guid)}) or 0
    char["reputations"] = rows(mysql, char_db, "SELECT faction, standing, flags FROM character_reputation WHERE guid=:guid ORDER BY faction LIMIT 50", {"guid": int(guid)})
    char["skills"] = rows(mysql, char_db, "SELECT skill, value, max FROM character_skills WHERE guid=:guid ORDER BY skill LIMIT 80", {"guid": int(guid)})
    return char


def update_character(cfg: dict, realm: str, guid: int, account: int, name: str, level: int, money_gold: int, map_id: int, zone: int, x: float, y: float, z: float):
    mysql = cfg["mysql"]
    char_db = character_database(mysql, realm)
    name = name.strip()
    if not name or len(name) > 12:
        raise ValueError("Charaktername muss 1 bis 12 Zeichen haben.")
    level = max(1, min(int(level), 255))
    money = max(0, int(money_gold)) * 10000
    with engine_for(mysql, char_db).begin() as conn:
        exists = conn.execute(text("SELECT guid FROM characters WHERE guid=:guid"), {"guid": int(guid)}).first()
        if not exists:
            raise ValueError("Charakter nicht gefunden.")
        conn.execute(text("""
            UPDATE characters
            SET account=:account, name=:name, level=:level, money=:money, map=:map, zone=:zone,
                position_x=:x, position_y=:y, position_z=:z
            WHERE guid=:guid
        """), {
            "guid": int(guid), "account": int(account), "name": name, "level": level, "money": money,
            "map": int(map_id), "zone": int(zone), "x": float(x), "y": float(y), "z": float(z),
        })


def delete_character(cfg: dict, realm: str, guid: int) -> str:
    mysql = cfg["mysql"]
    char_db = character_database(mysql, realm)
    with engine_for(mysql, char_db).begin() as conn:
        char = conn.execute(text("SELECT guid, name FROM characters WHERE guid=:guid"), {"guid": int(guid)}).mappings().first()
        if not char:
            raise ValueError("Charakter nicht gefunden.")
        delete_character_rows(conn, int(guid))
        conn.execute(text("DELETE FROM characters WHERE guid=:guid"), {"guid": int(guid)})
    return char["name"]


CHARACTER_GUID_TABLES = {
    "character_account_data": "guid", "character_achievement": "guid", "character_achievement_progress": "guid",
    "character_action": "guid", "character_aura": "guid", "character_banned": "guid",
    "character_battleground_data": "guid", "character_declinedname": "guid",
    "character_equipmentsets": "guid", "character_gifts": "guid", "character_glyphs": "guid",
    "character_homebind": "guid",
    "character_queststatus": "guid", "character_queststatus_daily": "guid",
    "character_queststatus_monthly": "guid", "character_queststatus_rewarded": "guid",
    "character_queststatus_seasonal": "guid", "character_queststatus_weekly": "guid",
    "character_reputation": "guid", "character_skills": "guid",
    "character_spell": "guid", "character_spell_cooldown": "guid", "character_stats": "guid",
    "character_talent": "guid", "character_void_storage": "guid",
}


def transfer_character(cfg: dict, source_realm: str, guid: int, target_realm: str, action: str, target_name: str) -> dict:
    if source_realm not in {"normal", "playerbot"} or target_realm not in {"normal", "playerbot"}:
        raise ValueError("Unbekannter Realm.")
    if action not in {"copy", "move"}:
        raise ValueError("Aktion muss copy oder move sein.")
    target_name = target_name.strip()
    if not target_name or len(target_name) > 12:
        raise ValueError("Zielname muss 1 bis 12 Zeichen haben.")

    mysql = cfg["mysql"]
    source_db = character_database(mysql, source_realm)
    target_db = character_database(mysql, target_realm)
    source_engine = engine_for(mysql, source_db)
    target_engine = engine_for(mysql, target_db)
    try:
        with source_engine.begin() as source, target_engine.begin() as target:
            char = source.execute(text("SELECT * FROM characters WHERE guid=:guid"), {"guid": int(guid)}).mappings().first()
            if not char:
                raise ValueError("Charakter nicht gefunden.")
            if int(char.get("online") or 0) != 0:
                raise ValueError("Charakter ist noch online.")
            existing_name = target.execute(text("SELECT guid FROM characters WHERE name=:name"), {"name": target_name}).first()
            if existing_name:
                raise ValueError(f"Im Zielrealm existiert bereits ein Charakter mit dem Namen {target_name}.")

            new_guid = next_id(target, "characters", "guid")
            item_map = copy_character_items(source, target, int(guid), new_guid)
            mail_map = copy_character_mails(source, target, int(guid), new_guid, item_map)

            char_values = dict(char)
            char_values["guid"] = new_guid
            char_values["name"] = target_name
            char_values["online"] = 0
            insert_row(target, "characters", char_values)

            for table, column in CHARACTER_GUID_TABLES.items():
                copy_rows_with_guid(source, target, table, column, int(guid), new_guid, item_map=item_map, mail_map=mail_map)

            copy_rows_with_guid(source, target, "character_inventory", "guid", int(guid), new_guid, item_map=item_map, mail_map=mail_map)

            if action == "move":
                delete_character_rows(source, int(guid))
                source.execute(text("DELETE FROM characters WHERE guid=:guid"), {"guid": int(guid)})
        return {"new_guid": new_guid, "name": target_name, "target_realm": target_realm, "target_realm_label": "Playerbot-Realm" if target_realm == "playerbot" else "Normal-Realm"}
    finally:
        source_engine.dispose()
        target_engine.dispose()


def next_id(conn, table: str, column: str) -> int:
    value = conn.execute(text(f"SELECT COALESCE(MAX({qname(column)}), 0) + 1 FROM {qname(table)}")).scalar()
    return int(value or 1)


def table_columns(conn, table: str) -> set[str]:
    try:
        return {row["Field"] for row in conn.execute(text(f"DESCRIBE {qname(table)}")).mappings()}
    except Exception:
        return set()


def qname(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def insert_row(conn, table: str, values: dict):
    columns = [column for column in values.keys() if column in table_columns(conn, table)]
    if not columns:
        return
    binds = {column: values[column] for column in columns}
    names = ", ".join(qname(column) for column in columns)
    params = ", ".join(f":{column}" for column in columns)
    conn.execute(text(f"INSERT INTO {qname(table)} ({names}) VALUES ({params})"), binds)


def copy_rows_with_guid(source, target, table: str, column: str, old_guid: int, new_guid: int, item_map: dict[int, int], mail_map: dict[int, int]):
    source_columns = table_columns(source, table)
    target_columns = table_columns(target, table)
    if not source_columns or not target_columns or column not in source_columns:
        return
    rows_to_copy = source.execute(text(f"SELECT * FROM {qname(table)} WHERE {qname(column)}=:guid"), {"guid": old_guid}).mappings().all()
    for row in rows_to_copy:
        values = dict(row)
        values[column] = new_guid
        for item_column in ("item", "bag", "itemguid", "item_guid"):
            if item_column in values and values[item_column] in item_map:
                values[item_column] = item_map[values[item_column]]
        for mail_column in ("mail_id", "mailId", "id"):
            if table != "mail" and mail_column in values and values[mail_column] in mail_map:
                values[mail_column] = mail_map[values[mail_column]]
        insert_row(target, table, values)


def copy_character_items(source, target, old_guid: int, new_guid: int) -> dict[int, int]:
    item_columns = table_columns(source, "item_instance")
    if not item_columns or not table_columns(target, "item_instance"):
        return {}
    item_ids: set[int] = set()
    if table_columns(source, "character_inventory"):
        for row in source.execute(text("SELECT item, bag FROM character_inventory WHERE guid=:guid"), {"guid": old_guid}).mappings():
            for value in (row.get("item"), row.get("bag")):
                if value:
                    item_ids.add(int(value))
    if table_columns(source, "mail") and table_columns(source, "mail_items"):
        for row in source.execute(text("""
            SELECT mi.item_guid
            FROM mail_items mi JOIN mail m ON m.id = mi.mail_id
            WHERE m.receiver=:guid
        """), {"guid": old_guid}).mappings():
            if row.get("item_guid"):
                item_ids.add(int(row["item_guid"]))
    item_map: dict[int, int] = {}
    next_item_guid = next_id(target, "item_instance", "guid")
    for old_item in sorted(item_ids):
        row = source.execute(text("SELECT * FROM item_instance WHERE guid=:guid"), {"guid": old_item}).mappings().first()
        if not row:
            continue
        new_item = next_item_guid
        next_item_guid += 1
        item_map[old_item] = new_item
        values = dict(row)
        values["guid"] = new_item
        if "owner_guid" in values:
            values["owner_guid"] = new_guid
        insert_row(target, "item_instance", values)
    return item_map


def copy_character_mails(source, target, old_guid: int, new_guid: int, item_map: dict[int, int]) -> dict[int, int]:
    if not table_columns(source, "mail") or not table_columns(target, "mail"):
        return {}
    mail_map: dict[int, int] = {}
    next_mail_id = next_id(target, "mail", "id")
    mails = source.execute(text("SELECT * FROM mail WHERE receiver=:guid"), {"guid": old_guid}).mappings().all()
    for mail in mails:
        old_mail = int(mail["id"])
        new_mail = next_mail_id
        next_mail_id += 1
        mail_map[old_mail] = new_mail
        values = dict(mail)
        values["id"] = new_mail
        values["receiver"] = new_guid
        if values.get("sender") == old_guid:
            values["sender"] = new_guid
        insert_row(target, "mail", values)
    if table_columns(source, "mail_items") and table_columns(target, "mail_items"):
        for old_mail, new_mail in mail_map.items():
            rows_to_copy = source.execute(text("SELECT * FROM mail_items WHERE mail_id=:id"), {"id": old_mail}).mappings().all()
            for row in rows_to_copy:
                values = dict(row)
                values["mail_id"] = new_mail
                if values.get("item_guid") in item_map:
                    values["item_guid"] = item_map[values["item_guid"]]
                insert_row(target, "mail_items", values)
    return mail_map


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


def delete_account(cfg: dict, account_id: int) -> str:
    mysql = cfg["mysql"]
    auth_db = mysql["auth_db"]
    with engine_for(mysql, auth_db).begin() as conn:
        account = conn.execute(text("SELECT id, username FROM account WHERE id=:id"), {"id": int(account_id)}).mappings().first()
        if not account:
            raise ValueError("Account nicht gefunden.")
        username = account["username"]
        conn.execute(text("DELETE FROM account_access WHERE id=:id"), {"id": int(account_id)})
        conn.execute(text("DELETE FROM account_banned WHERE id=:id"), {"id": int(account_id)})
        conn.execute(text("DELETE FROM account WHERE id=:id"), {"id": int(account_id)})
    for char_db in [mysql["characters_db"], mysql["pb_characters_db"]]:
        delete_account_characters(mysql, char_db, account_id)
    return username


def delete_account_characters(mysql: dict, char_db: str, account_id: int):
    cleanup = {
        "character_account_data": "guid", "character_achievement": "guid", "character_achievement_progress": "guid",
        "character_action": "guid", "character_aura": "guid", "character_banned": "guid",
        "character_battleground_data": "guid", "character_declinedname": "guid",
        "character_equipmentsets": "guid", "character_gifts": "guid", "character_glyphs": "guid",
        "character_homebind": "guid", "character_instance": "guid", "character_inventory": "guid",
        "character_pet": "owner", "character_queststatus": "guid", "character_queststatus_daily": "guid",
        "character_queststatus_monthly": "guid", "character_queststatus_rewarded": "guid",
        "character_queststatus_seasonal": "guid", "character_queststatus_weekly": "guid",
        "character_reputation": "guid", "character_skills": "guid", "character_social": "guid",
        "character_spell": "guid", "character_spell_cooldown": "guid", "character_stats": "guid",
        "character_talent": "guid", "character_void_storage": "guid", "corpse": "guid",
        "group_member": "memberGuid", "guild_member": "guid", "petition_sign": "playerguid",
    }
    with engine_for(mysql, char_db).begin() as conn:
        guids = [row["guid"] for row in conn.execute(text("SELECT guid FROM characters WHERE account=:id"), {"id": int(account_id)}).mappings()]
        for guid in guids:
            delete_character_rows(conn, int(guid), cleanup)
        conn.execute(text("DELETE FROM characters WHERE account=:id"), {"id": int(account_id)})


def delete_character_rows(conn, guid: int, cleanup: dict | None = None):
    cleanup = cleanup or {
        "character_account_data": "guid", "character_achievement": "guid", "character_achievement_progress": "guid",
        "character_action": "guid", "character_aura": "guid", "character_banned": "guid",
        "character_battleground_data": "guid", "character_declinedname": "guid",
        "character_equipmentsets": "guid", "character_gifts": "guid", "character_glyphs": "guid",
        "character_homebind": "guid", "character_instance": "guid", "character_inventory": "guid",
        "character_pet": "owner", "character_queststatus": "guid", "character_queststatus_daily": "guid",
        "character_queststatus_monthly": "guid", "character_queststatus_rewarded": "guid",
        "character_queststatus_seasonal": "guid", "character_queststatus_weekly": "guid",
        "character_reputation": "guid", "character_skills": "guid", "character_social": "guid",
        "character_spell": "guid", "character_spell_cooldown": "guid", "character_stats": "guid",
        "character_talent": "guid", "character_void_storage": "guid", "corpse": "guid",
        "group_member": "memberGuid", "guild_member": "guid", "petition_sign": "playerguid",
    }
    for table, column in cleanup.items():
        try:
            conn.execute(text(f"DELETE FROM {table} WHERE {column}=:guid"), {"guid": guid})
        except Exception:
            pass
    try:
        conn.execute(text("DELETE mi FROM mail_items mi JOIN mail m ON m.id = mi.mail_id WHERE m.receiver=:guid"), {"guid": guid})
        conn.execute(text("DELETE FROM mail WHERE receiver=:guid"), {"guid": guid})
    except Exception:
        pass


def _set_account_access(conn, account_id: int, gm_level_value: int):
    gm_level_value = max(0, min(int(gm_level_value), 4))
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
        row["realm_key"] = realm
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
