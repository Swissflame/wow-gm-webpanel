REALMS = {
    "normal": {"label": "Normal-Realm", "world_db": "world_db", "characters_db": "characters_db", "has_ahbot": True, "has_playerbots": False, "port": "normal_world_port"},
    "playerbot": {"label": "Playerbot-Realm", "world_db": "pb_world_db", "characters_db": "pb_characters_db", "has_ahbot": True, "has_playerbots": True, "port": "playerbot_world_port"},
}


def selected_realm(request) -> str:
    value = request.session.get("realm", "normal")
    return value if value in REALMS else "normal"


def realm_cfg(cfg: dict, realm: str) -> dict:
    info = REALMS.get(realm, REALMS["normal"]).copy()
    mysql = cfg["mysql"]
    info["world_database"] = mysql[info["world_db"]]
    info["characters_database"] = mysql[info["characters_db"]]
    return info
