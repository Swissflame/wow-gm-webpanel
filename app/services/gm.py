from ..models import CommandHistory
from .gm_help import command_help

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

FALLBACK_COMMANDS += [
    ("account create", 3, ".account create $account $password", "Create account"),
    ("account delete", 3, ".account delete $account", "Delete account"),
    ("account set gmlevel", 3, ".account set gmlevel $account $level $realmid", "Set account GM level"),
    ("account set password", 3, ".account set password $account $password $password", "Set account password"),
    ("account set addon", 3, ".account set addon $account $addon", "Set account addon expansion"),
    ("account lock ip", 1, ".account lock ip on/off", "Toggle account IP lock"),
    ("gm visible", 1, ".gm visible on/off", "Toggle GM visibility"),
    ("gm chat", 1, ".gm chat on/off", "Toggle GM chat badge"),
    ("gm list", 1, ".gm list", "List GMs"),
    ("gm ingame", 1, ".gm ingame", "List online GMs"),
    ("gmannounce", 2, ".gmannounce $message", "GM announcement"),
    ("gmnotify", 2, ".gmnotify $message", "GM notification"),
    ("gmnameannounce", 2, ".gmnameannounce $message", "GM named announcement"),
    ("nameannounce", 2, ".nameannounce $message", "Named announcement"),
    ("cheat taxi", 2, ".cheat taxi on/off", "Toggle taxi cheat"),
    ("cheat waterwalk", 2, ".cheat waterwalk on/off", "Toggle waterwalk"),
    ("cheat casttime", 2, ".cheat casttime on/off", "Toggle cast time cheat"),
    ("cheat cooldown", 2, ".cheat cooldown on/off", "Toggle cooldown cheat"),
    ("cast", 3, ".cast $spell", "Cast spell"),
    ("cast back", 3, ".cast back $spell", "Cast spell back"),
    ("cast dist", 3, ".cast dist $spell $distance", "Cast spell by distance"),
    ("cast self", 3, ".cast self $spell", "Cast spell on self"),
    ("cast target", 3, ".cast target $spell", "Cast spell on target"),
    ("teleport add", 3, ".teleport add $name", "Add teleport"),
    ("teleport del", 3, ".teleport del $name", "Delete teleport"),
    ("list item", 2, ".list item $name", "List items"),
    ("lookup taxi", 2, ".lookup taxi $name", "Lookup taxi nodes"),
    ("lookup area", 2, ".lookup area $name", "Lookup areas"),
    ("go taxinode", 3, ".go taxinode $id", "Go to taxi node"),
    ("go trigger", 3, ".go trigger $id", "Go to trigger"),
    ("go xy", 3, ".go xy $x $y", "Go to coordinates"),
    ("go xyz", 3, ".go xyz $x $y $z", "Go to coordinates"),
    ("go zonexy", 3, ".go zonexy $x $y $zone", "Go to zone coordinates"),
    ("pet create", 3, ".pet create", "Create pet from selected creature"),
    ("pet learn", 3, ".pet learn $spell", "Teach pet spell"),
    ("pet unlearn", 3, ".pet unlearn $spell", "Unteach pet spell"),
    ("learn all my pettalents", 3, ".learn all my pettalents", "Teach all pet talents"),
    ("character check bank", 3, ".character check bank", "Check character bank"),
    ("dismount", 2, ".dismount", "Dismount target"),
    ("modify scale", 3, ".modify scale $value", "Modify scale"),
    ("save", 1, ".save", "Save selected player"),
    ("cooldown", 2, ".cooldown", "Clear cooldowns"),
    ("guid", 1, ".guid", "Show GUID"),
    ("pinfo", 1, ".pinfo $character", "Show player info"),
    ("distance", 1, ".distance", "Show distance"),
    ("die", 2, ".die", "Kill target"),
    ("recall", 2, ".recall $character", "Recall character"),
    ("morph", 2, ".morph $display", "Morph target"),
    ("demorph", 2, ".demorph", "Remove morph"),
    ("gps", 1, ".gps", "Show GPS"),
    ("combatstop", 2, ".combatstop", "Stop combat"),
    ("maxskill", 2, ".maxskill", "Max skills"),
    ("freeze", 2, ".freeze $character", "Freeze character"),
    ("unfreeze", 2, ".unfreeze $character", "Unfreeze character"),
    ("repairitems", 2, ".repairitems", "Repair items"),
    ("groupsummon", 2, ".groupsummon $character", "Summon group"),
    ("teleport group", 2, ".teleport group $character $location", "Teleport group"),
    ("guild create", 2, ".guild create $leader $name", "Create guild"),
    ("guild delete", 3, ".guild delete $name", "Delete guild"),
    ("guild invite", 2, ".guild invite $character $guild", "Invite to guild"),
    ("guild uninvite", 2, ".guild uninvite $character", "Remove from guild"),
    ("guild rank", 2, ".guild rank $character $rank", "Set guild rank"),
    ("mute", 2, ".mute $character $minutes $reason", "Mute account"),
    ("unmute", 2, ".unmute $character", "Unmute account"),
    ("damage", 3, ".damage $amount", "Damage target"),
    ("showarea", 3, ".showarea $area", "Show area"),
    ("hidearea", 3, ".hidearea $area", "Hide area"),
    ("honor add", 2, ".honor add $points", "Add honor"),
    ("honor update", 2, ".honor update", "Update honor"),
    ("event start", 3, ".event start $id", "Start event"),
    ("event stop", 3, ".event stop $id", "Stop event"),
    ("event info", 2, ".event info $id", "Show event info"),
    ("event activelist", 2, ".event activelist", "List active events"),
    ("wchange", 3, ".wchange $weather $grade", "Change weather"),
]

COMMANDS = []
for n, s, t, h in FALLBACK_COMMANDS:
    help_info = command_help(n, h)
    COMMANDS.append({
        "name": n,
        "level": s,
        "template": t.lstrip("."),
        "help": h,
        "help_summary": help_info["summary"],
        "help_syntax": help_info["syntax"],
        "help_output": help_info["output"],
        "help_notes": help_info["notes"],
        "help_tooltip": help_info["tooltip"],
        "category": CATEGORIES.get(n.split()[0], "Sonstige"),
    })


def allowed_commands(gm_level: int):
    return [cmd for cmd in COMMANDS if gm_level >= cmd["level"]]


def normalize_db_commands(rows: list[dict], gm_level: int, lang: str = "de"):
    data = []
    for row in rows:
        level = int(row.get("security") or 0)
        if level > gm_level:
            continue
        name = row.get("name") or ""
        root = name.split()[0] if name else "Sonstige"
        help_info = command_help(name, row.get("help") or "", lang)
        data.append({
            "name": name,
            "level": level,
            "template": name,
            "help": row.get("help") or "",
            "help_summary": help_info["summary"],
            "help_syntax": help_info["syntax"],
            "help_output": help_info["output"],
            "help_notes": help_info["notes"],
            "help_tooltip": help_info["tooltip"],
            "category": CATEGORIES.get(root, root.title()),
        })
    return data


def record_command(db, user_id, realm, command, result):
    db.add(CommandHistory(user_id=user_id, realm=realm, command=command, result=result))
    db.commit()
