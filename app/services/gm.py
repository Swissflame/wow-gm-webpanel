from ..models import CommandHistory

CATEGORIES = {
    "account": "Accounts & Sicherheit", "character": "Charaktere", "ban": "Banns", "baninfo": "Banns", "banlist": "Banns",
    "unban": "Banns", "tele": "Teleport", "appear": "Teleport", "summon": "Teleport", "go": "Teleport", "recall": "Teleport",
    "modify": "Charakterwerte", "levelup": "Charakterwerte", "additem": "Items", "lookup": "Suche", "npc": "NPCs",
    "gm": "GM-Modus", "announce": "Kommunikation", "notify": "Kommunikation", "whispers": "Kommunikation",
    "server": "Server", "reload": "Reload", "debug": "Debug", "cheat": "Cheats", "quest": "Quests",
    "achievement": "Achievements", "arena": "PvP", "honor": "PvP", "ticket": "Tickets", "learn": "Spells",
    "unlearn": "Spells", "cast": "Spells", "aura": "Spells", "mail": "Mail", "guild": "Gilden",
}

FALLBACK_COMMANDS = [
    ("commands", 0, ".commands", "List available commands"),
    ("account", 0, ".account", "Display your account access level"),
    ("account password", 0, ".account password $old $new $new", "Change own password"),
    ("gm on", 1, ".gm on", "Enable GM mode"),
    ("gm off", 1, ".gm off", "Disable GM mode"),
    ("gm fly", 1, ".gm fly on/off", "Toggle GM flying"),
    ("appear", 1, ".appear $character", "Teleport to player"),
    ("summon", 1, ".summon $character", "Summon player"),
    ("kick", 1, ".kick $player $reason", "Kick player"),
    ("notify", 1, ".notify $message", "Notify online players"),
    ("announce", 2, ".announce $message", "Global announcement"),
    ("additem", 2, ".additem $item $count", "Add item"),
    ("character rename", 2, ".character rename $name", "Force rename"),
    ("character customize", 2, ".character customize $name", "Force customization"),
    ("character changefaction", 2, ".character changefaction $name", "Force faction change"),
    ("character changerace", 2, ".character changerace $name", "Force race change"),
    ("revive", 2, ".revive $player", "Revive player"),
    ("tele", 2, ".tele $location", "Teleport to location"),
    ("tele name", 2, ".tele name $player $location", "Teleport player to location"),
    ("lookup item", 2, ".lookup item $name", "Search items"),
    ("lookup quest", 2, ".lookup quest $name", "Search quests"),
    ("lookup creature", 2, ".lookup creature $name", "Search creatures"),
    ("ban account", 2, ".ban account $account $time $reason", "Ban account"),
    ("ban character", 2, ".ban character $name $time $reason", "Ban character"),
    ("unban account", 2, ".unban account $account", "Unban account"),
    ("character level", 3, ".character level $name $level", "Set level"),
    ("modify money", 3, ".modify money $amount", "Modify money on selected player"),
    ("modify speed", 3, ".modify speed $rate", "Modify speed"),
    ("learn", 3, ".learn $spell", "Teach spell"),
    ("unlearn", 3, ".unlearn $spell", "Remove spell"),
    ("npc add", 3, ".npc add $entry", "Spawn creature"),
    ("npc delete", 3, ".npc delete", "Delete selected creature"),
    ("quest add", 3, ".quest add $id", "Add quest"),
    ("quest complete", 3, ".quest complete $id", "Complete quest"),
    ("server info", 3, ".server info", "Server information"),
    ("server restart", 3, ".server restart $seconds", "Restart worldserver"),
    ("server shutdown", 3, ".server shutdown $seconds", "Shutdown worldserver"),
    ("reload all", 3, ".reload all", "Reload server data"),
    ("saveall", 3, ".saveall", "Save all players"),
]

COMMANDS = [{"name": n, "level": s, "template": t.lstrip("."), "help": h, "category": CATEGORIES.get(n.split()[0], "Sonstige")} for n, s, t, h in FALLBACK_COMMANDS]


def allowed_commands(gm_level: int):
    return [cmd for cmd in COMMANDS if gm_level >= cmd["level"]]


def normalize_db_commands(rows: list[dict], gm_level: int):
    data = []
    for row in rows:
        level = int(row.get("security") or 0)
        if level > gm_level:
            continue
        name = row.get("name") or ""
        root = name.split()[0] if name else "Sonstige"
        data.append({
            "name": name,
            "level": level,
            "template": name,
            "help": row.get("help") or "",
            "category": CATEGORIES.get(root, root.title()),
        })
    return data


def record_command(db, user_id, realm, command, result):
    db.add(CommandHistory(user_id=user_id, realm=realm, command=command, result=result))
    db.commit()
