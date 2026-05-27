def tr(lang: str, de: str, en: str) -> str:
    return en if lang == "en" else de


TABS = [
    ("favorites", "Favoriten", "Favorites"),
    ("characters", "Charaktere", "Characters"),
    ("teleport", "Teleport", "Teleport"),
    ("items", "Items & Post", "Items & Mail"),
    ("communication", "Nachrichten", "Messages"),
    ("world", "Welt & Wetter", "World & Weather"),
    ("events", "Events", "Events"),
    ("server", "Server", "Server"),
    ("raw", "Expertenmodus", "Expert mode"),
]


BASE_ACTIONS = [
    {
        "id": "weather", "tab": "world", "level": 3, "icon": "W", "character": "none",
        "de": "Wetter", "en": "Weather",
        "desc_de": "Setzt Wetterart und Stärke in der aktuellen Zone.", "desc_en": "Sets weather type and intensity in the current zone.",
        "command": "wchange {weather} {grade}",
        "inputs": [
            {"name": "weather", "kind": "select", "de": "Wetter", "en": "Weather", "default": "0",
             "options": [("0", "Schön", "Fine"), ("1", "Regen", "Rain"), ("2", "Schnee", "Snow"), ("3", "Sturm", "Storm"), ("86", "Gewitter", "Thunder"), ("90", "Schwarzer Regen", "Black rain")]},
            {"name": "grade", "kind": "select", "de": "Stärke", "en": "Intensity", "default": "1.0",
             "options": [("0.0", "Aus", "Off"), ("0.25", "Leicht", "Light"), ("0.5", "Mittel", "Medium"), ("0.75", "Stark", "Strong"), ("1.0", "Maximum", "Maximum")]},
        ],
        "buttons": [{"label_de": "Wetter setzen", "label_en": "Set weather", "command": "wchange {weather} {grade}"}],
    },
    {
        "id": "gm_mode", "tab": "characters", "level": 1, "icon": "GM", "character": "none",
        "de": "GM-Modus", "en": "GM mode",
        "desc_de": "Schaltet GM-Status, Sichtbarkeit und Flugmodus.", "desc_en": "Toggles GM status, visibility and fly mode.",
        "buttons": [
            {"label_de": "GM an", "label_en": "GM on", "command": "gm on"},
            {"label_de": "GM aus", "label_en": "GM off", "command": "gm off"},
            {"label_de": "Sichtbar", "label_en": "Visible", "command": "gm visible on"},
            {"label_de": "Unsichtbar", "label_en": "Invisible", "command": "gm visible off"},
            {"label_de": "Fliegen an", "label_en": "Fly on", "command": "gm fly on"},
            {"label_de": "Fliegen aus", "label_en": "Fly off", "command": "gm fly off"},
        ],
    },
    {
        "id": "communication", "tab": "communication", "level": 2, "icon": "!", "character": "none",
        "de": "Nachrichten", "en": "Messages",
        "desc_de": "Sendet Nachrichten an Spieler oder GMs.", "desc_en": "Sends messages to players or GMs.",
        "inputs": [{"name": "message", "kind": "text", "de": "Nachricht", "en": "Message", "required": True}],
        "buttons": [
            {"label_de": "An alle ankündigen", "label_en": "Announce to all", "command": "announce {message}"},
            {"label_de": "Bildschirmmeldung", "label_en": "Screen notification", "command": "notify {message}"},
            {"label_de": "GM-Ankündigung", "label_en": "GM announcement", "command": "gmannounce {message}"},
            {"label_de": "GM-Bildschirmmeldung", "label_en": "GM screen notification", "command": "gmnotify {message}"},
        ],
    },
    {
        "id": "player_control", "tab": "characters", "level": 2, "icon": "C", "character": "any",
        "de": "Charakter verwalten", "en": "Manage character",
        "desc_de": "Häufige Aktionen für online und offline Charaktere.", "desc_en": "Common actions for online and offline characters.",
        "inputs": [{"name": "level", "kind": "number", "de": "Level", "en": "Level", "default": "80"}],
        "buttons": [
            {"label_de": "Wiederbeleben", "label_en": "Revive", "command": "revive {character}", "online_only": True},
            {"label_de": "Kicken", "label_en": "Kick", "command": "kick {character}"},
            {"label_de": "Level setzen", "label_en": "Set level", "command": "character level {character} {level}"},
            {"label_de": "Umbenennung", "label_en": "Rename", "command": "character rename {character}"},
            {"label_de": "Aussehen ändern", "label_en": "Customize", "command": "character customize {character}"},
            {"label_de": "Fraktion ändern", "label_en": "Change faction", "command": "character changefaction {character}"},
            {"label_de": "Volk ändern", "label_en": "Change race", "command": "character changerace {character}"},
        ],
    },
    {
        "id": "teleport_tools", "tab": "teleport", "level": 2, "icon": "T", "character": "any",
        "de": "Teleport", "en": "Teleport",
        "desc_de": "Teleportiert dich oder den gewählten Charakter.", "desc_en": "Teleports you or the selected character.",
        "inputs": [{"name": "location", "kind": "text", "de": "Teleport-Ort", "en": "Teleport location", "default": "$home"}],
        "buttons": [
            {"label_de": "Zu Spieler gehen", "label_en": "Appear at player", "command": "appear {character}"},
            {"label_de": "Zu mir rufen", "label_en": "Summon", "command": "summon {character}"},
            {"label_de": "Spieler zum Ort", "label_en": "Player to location", "command": "teleport name {character} {location}"},
            {"label_de": "Ich zum Ort", "label_en": "Me to location", "command": "teleport {location}"},
            {"label_de": "Spieler zum Ruhestein", "label_en": "Player to hearth", "command": "teleport name {character} $home"},
        ],
    },
    {
        "id": "mail_tools", "tab": "items", "level": 2, "icon": "M", "character": "any",
        "de": "Post senden", "en": "Send mail",
        "desc_de": "Sendet Post, Geld oder Items an einen Charakter.", "desc_en": "Sends mail, money or items to a character.",
        "inputs": [
            {"name": "subject", "kind": "text", "de": "Betreff", "en": "Subject", "default": "GM-Post"},
            {"name": "body", "kind": "text", "de": "Text", "en": "Body", "default": "Viel Spass."},
            {"name": "money", "kind": "number", "de": "Kupferbetrag", "en": "Copper amount", "default": "0"},
            {"name": "item", "kind": "number", "de": "Item-ID", "en": "Item ID"},
            {"name": "count", "kind": "number", "de": "Anzahl", "en": "Count", "default": "1"},
        ],
        "buttons": [
            {"label_de": "Nur Text senden", "label_en": "Send text", "command": "send mail {character} \"{subject}\" \"{body}\""},
            {"label_de": "Geld senden", "label_en": "Send money", "command": "send money {character} \"{subject}\" \"{body}\" {money}"},
            {"label_de": "Item senden", "label_en": "Send item", "command": "send items {character} \"{subject}\" \"{body}\" {item}:{count}"},
        ],
    },
    {
        "id": "item_tools", "tab": "items", "level": 2, "icon": "I", "character": "any",
        "de": "Items direkt", "en": "Direct items",
        "desc_de": "Gibt oder entfernt Items beim ausgewählten Charakter.", "desc_en": "Gives or removes items from the selected character.",
        "inputs": [{"name": "item", "kind": "number", "de": "Item-ID", "en": "Item ID", "required": True}, {"name": "count", "kind": "number", "de": "Anzahl", "en": "Count", "default": "1"}],
        "buttons": [
            {"label_de": "Item geben", "label_en": "Give item", "command": "additem {character} {item} {count}"},
            {"label_de": "Item entfernen", "label_en": "Remove item", "command": "additem {character} {item} -{count}"},
        ],
    },
    {
        "id": "cheats", "tab": "characters", "level": 2, "icon": "CH", "character": "none",
        "de": "Cheats", "en": "Cheats",
        "desc_de": "Schaltet typische GM-Cheats für deinen aktuellen GM-Charakter.", "desc_en": "Toggles common GM cheats for your current GM character.",
        "buttons": [
            {"label_de": "Gottmodus an", "label_en": "God on", "command": "cheat god on"},
            {"label_de": "Gottmodus aus", "label_en": "God off", "command": "cheat god off"},
            {"label_de": "Abklingzeiten aus", "label_en": "Cooldown off", "command": "cheat cooldown on"},
            {"label_de": "Castzeit aus", "label_en": "Cast time off", "command": "cheat casttime on"},
            {"label_de": "Alle Flugpunkte", "label_en": "All taxi nodes", "command": "cheat taxi on"},
            {"label_de": "Wasserlaufen", "label_en": "Waterwalk", "command": "cheat waterwalk on"},
        ],
    },
    {
        "id": "server_tools", "tab": "server", "level": 2, "icon": "S", "character": "none",
        "de": "Server", "en": "Server",
        "desc_de": "Serverinformationen, Speichern und geplante Neustarts.", "desc_en": "Server info, saves and scheduled restarts.",
        "inputs": [{"name": "delay", "kind": "text", "de": "Verzoegerung", "en": "Delay", "default": "60"}],
        "buttons": [
            {"label_de": "Serverinfo", "label_en": "Server info", "command": "server info"},
            {"label_de": "Alle speichern", "label_en": "Save all", "command": "saveall"},
            {"label_de": "Neustart planen", "label_en": "Schedule restart", "command": "server restart {delay}"},
            {"label_de": "Neustart abbrechen", "label_en": "Cancel restart", "command": "server restart cancel"},
            {"label_de": "Reload all", "label_en": "Reload all", "command": "reload all"},
        ],
    },
]


def localized_actions(lang: str, gm_level: int) -> list[dict]:
    actions = []
    for action in BASE_ACTIONS:
        if gm_level < action["level"]:
            continue
        item = {k: v for k, v in action.items() if k not in {"de", "en", "desc_de", "desc_en"}}
        item["label"] = tr(lang, action["de"], action["en"])
        item["description"] = tr(lang, action["desc_de"], action["desc_en"])
        inputs = []
        for field in action.get("inputs", []):
            f = field.copy()
            f["label"] = tr(lang, f.get("de", f["name"]), f.get("en", f["name"]))
            if f.get("options"):
                f["localized_options"] = [(value, tr(lang, de, en)) for value, de, en in f["options"]]
            inputs.append(f)
        item["inputs"] = inputs
        item["buttons"] = [{**button, "label": tr(lang, button["label_de"], button["label_en"])} for button in action.get("buttons", [])]
        actions.append(item)
    return actions


def event_actions(events: list[dict], lang: str, gm_level: int) -> list[dict]:
    if gm_level < 3:
        return []
    wanted = {
        "darkmoon": ("Dunkelmond-Jahrmarkt", "Darkmoon Faire"),
        "dunkelmond": ("Dunkelmond-Jahrmarkt", "Darkmoon Faire"),
        "brewfest": ("Braufest", "Brewfest"),
        "hallow": ("Schlotternaechte", "Hallow's End"),
        "winter veil": ("Winterhauchfest", "Winter Veil"),
        "midsummer": ("Sonnenwendfest", "Midsummer Fire Festival"),
        "noblegarden": ("Nobelgarten", "Noblegarden"),
        "love is in the air": ("Liebe liegt in der Luft", "Love is in the Air"),
        "lunar": ("Mondfest", "Lunar Festival"),
        "pilgrim": ("Pilgerfreuden", "Pilgrim's Bounty"),
        "harvest": ("Erntedankfest", "Harvest Festival"),
    }
    picked = {}
    for event in events:
        lower = event["description"].lower()
        for needle, names in wanted.items():
            if needle in lower and names not in picked:
                picked[names] = event["id"]
                break
    actions = []
    for names, event_id in picked.items():
        display = names[1] if lang == "en" else names[0]
        actions.append({
            "id": f"event_{event_id}", "tab": "events", "level": 3, "icon": "E", "character": "none",
            "label": display,
            "description": f"Event-ID {event_id} starten oder beenden." if lang == "de" else f"Start or stop event ID {event_id}.",
            "inputs": [],
            "buttons": [
                {"label": "Starten" if lang == "de" else "Start", "command": f"event start {event_id}"},
                {"label": "Beenden" if lang == "de" else "Stop", "command": f"event stop {event_id}"},
            ],
        })
    actions.append({
        "id": "event_custom", "tab": "events", "level": 3, "icon": "ID", "character": "none",
        "label": "Event-ID" if lang == "de" else "Event ID",
        "description": "Beliebiges Event per ID starten oder beenden." if lang == "de" else "Start or stop any event by ID.",
        "inputs": [{"name": "event_id", "kind": "number", "label": "Event-ID" if lang == "de" else "Event ID", "required": True}],
        "buttons": [
            {"label": "Starten" if lang == "de" else "Start", "command": "event start {event_id}"},
            {"label": "Beenden" if lang == "de" else "Stop", "command": "event stop {event_id}"},
        ],
    })
    return actions


def build_command(action: dict, form: dict) -> str:
    values = {key: str(value).strip() for key, value in form.items()}
    for field in action.get("inputs", []):
        values.setdefault(field["name"], field.get("default", ""))
    if action.get("character") in {"any", "online"}:
        values["character"] = values.get("character", "")
    command = values.get("command_template") or (action.get("buttons", [{}])[0].get("command") if action.get("buttons") else action.get("command", ""))
    return command.format(**values).strip()
