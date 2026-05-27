def tr(lang: str, de: str, en: str) -> str:
    return en if lang == "en" else de


BASE_ACTIONS = [
    {
        "id": "weather_fine", "tab": "world", "level": 2, "icon": "☀", "character": "none",
        "de": "Wetter schön", "en": "Weather fine",
        "desc_de": "Setzt das Wetter in der aktuellen Zone auf klar.", "desc_en": "Sets weather in the current zone to clear.",
        "command": "wchange 0 0",
    },
    {
        "id": "weather_rain", "tab": "world", "level": 2, "icon": "☂", "character": "none",
        "de": "Wetter Regen", "en": "Weather rain",
        "desc_de": "Startet Regen in der aktuellen Zone.", "desc_en": "Starts rain in the current zone.",
        "command": "wchange 1 3",
    },
    {
        "id": "weather_snow", "tab": "world", "level": 2, "icon": "*", "character": "none",
        "de": "Wetter Schnee", "en": "Weather snow",
        "desc_de": "Startet Schneefall in der aktuellen Zone.", "desc_en": "Starts snow in the current zone.",
        "command": "wchange 2 3",
    },
    {
        "id": "announce", "tab": "communication", "level": 1, "icon": "!", "character": "none",
        "de": "Ankündigung", "en": "Announcement",
        "desc_de": "Sendet eine globale Nachricht an alle Spieler.", "desc_en": "Sends a global message to all players.",
        "command": "announce {message}", "inputs": [{"name": "message", "type": "text", "de": "Nachricht", "en": "Message", "required": True}],
    },
    {
        "id": "notify", "tab": "communication", "level": 1, "icon": "i", "character": "none",
        "de": "Bildschirmmeldung", "en": "Screen notification",
        "desc_de": "Zeigt online Spielern eine Systemmeldung.", "desc_en": "Shows online players a system notification.",
        "command": "notify {message}", "inputs": [{"name": "message", "type": "text", "de": "Nachricht", "en": "Message", "required": True}],
    },
    {
        "id": "kick", "tab": "characters", "level": 1, "icon": "X", "character": "online",
        "de": "Spieler kicken", "en": "Kick player",
        "desc_de": "Trennt einen online Charakter vom Server.", "desc_en": "Disconnects an online character.",
        "command": "kick {character} {reason}", "inputs": [{"name": "reason", "type": "text", "de": "Grund", "en": "Reason"}],
    },
    {
        "id": "revive", "tab": "characters", "level": 2, "icon": "+", "character": "online",
        "de": "Wiederbeleben", "en": "Revive",
        "desc_de": "Belebt einen online Charakter wieder.", "desc_en": "Revives an online character.",
        "command": "revive {character}",
    },
    {
        "id": "summon", "tab": "teleport", "level": 1, "icon": ">", "character": "online",
        "de": "Zu mir rufen", "en": "Summon to me",
        "desc_de": "Teleportiert einen online Charakter zu dir.", "desc_en": "Teleports an online character to you.",
        "command": "summon {character}",
    },
    {
        "id": "appear", "tab": "teleport", "level": 1, "icon": "<", "character": "online",
        "de": "Zu Spieler gehen", "en": "Appear at player",
        "desc_de": "Teleportiert dich zu einem online Charakter.", "desc_en": "Teleports you to an online character.",
        "command": "appear {character}",
    },
    {
        "id": "tele_name", "tab": "teleport", "level": 2, "icon": "@", "character": "any",
        "de": "Spieler teleportieren", "en": "Teleport player",
        "desc_de": "Teleportiert einen Charakter zu einem Teleport-Ort.", "desc_en": "Teleports a character to a named location.",
        "command": "tele name {character} {location}", "inputs": [{"name": "location", "type": "text", "de": "Teleport-Ort", "en": "Teleport location", "required": True}],
    },
    {
        "id": "level", "tab": "characters", "level": 3, "icon": "L", "character": "any",
        "de": "Level setzen", "en": "Set level",
        "desc_de": "Setzt das Level eines Charakters.", "desc_en": "Sets a character level.",
        "command": "character level {character} {level}", "inputs": [{"name": "level", "type": "number", "de": "Level", "en": "Level", "required": True}],
    },
    {
        "id": "rename", "tab": "characters", "level": 2, "icon": "R", "character": "any",
        "de": "Umbenennung erzwingen", "en": "Force rename",
        "desc_de": "Der Charakter muss beim nächsten Login einen neuen Namen wählen.", "desc_en": "Character must choose a new name on next login.",
        "command": "character rename {character}",
    },
    {
        "id": "customize", "tab": "characters", "level": 2, "icon": "C", "character": "any",
        "de": "Aussehen ändern lassen", "en": "Force customization",
        "desc_de": "Der Charakter kann beim nächsten Login Aussehen/Geschlecht ändern.", "desc_en": "Character can customize appearance on next login.",
        "command": "character customize {character}",
    },
    {
        "id": "send_money", "tab": "items", "level": 2, "icon": "G", "character": "any",
        "de": "Post mit Geld senden", "en": "Send mail with money",
        "desc_de": "Sendet einem Charakter Gold per Post.", "desc_en": "Sends money by mail to a character.",
        "command": "send money {character} \"{subject}\" \"{body}\" {money}",
        "inputs": [
            {"name": "money", "type": "number", "de": "Kupferbetrag", "en": "Copper amount", "required": True},
            {"name": "subject", "type": "text", "de": "Betreff", "en": "Subject", "default": "GM-Post"},
            {"name": "body", "type": "text", "de": "Text", "en": "Body", "default": "Viel Spaß."},
        ],
    },
    {
        "id": "add_item", "tab": "items", "level": 2, "icon": "I", "character": "online",
        "de": "Item geben", "en": "Give item",
        "desc_de": "Gibt dem ausgewählten online Charakter ein Item.", "desc_en": "Gives an item to the selected online character.",
        "command": "additem {item} {count}",
        "inputs": [{"name": "item", "type": "number", "de": "Item-ID", "en": "Item ID", "required": True}, {"name": "count", "type": "number", "de": "Anzahl", "en": "Count", "default": "1"}],
    },
    {
        "id": "saveall", "tab": "server", "level": 3, "icon": "S", "character": "none",
        "de": "Alle speichern", "en": "Save all",
        "desc_de": "Speichert alle Charaktere.", "desc_en": "Saves all characters.",
        "command": "saveall",
    },
    {
        "id": "reload_all", "tab": "server", "level": 3, "icon": "↻", "character": "none",
        "de": "Reload all", "en": "Reload all",
        "desc_de": "Lädt Serverdaten neu. Vorsichtig verwenden.", "desc_en": "Reloads server data. Use carefully.",
        "command": "reload all",
    },
]

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

FAVORITES = {"announce", "revive", "summon", "appear", "send_money", "weather_fine", "weather_rain", "saveall"}


def localized_actions(lang: str, gm_level: int) -> list[dict]:
    actions = []
    for action in BASE_ACTIONS:
        if gm_level < action["level"]:
            continue
        item = action.copy()
        item["label"] = tr(lang, item["de"], item["en"])
        item["description"] = tr(lang, item["desc_de"], item["desc_en"])
        for field in item.get("inputs", []):
            field["label"] = tr(lang, field["de"], field["en"])
        actions.append(item)
    return actions


def event_actions(events: list[dict], lang: str, gm_level: int) -> list[dict]:
    if gm_level < 3:
        return []
    wanted = {
        "darkmoon": ("Dunkelmond-Jahrmarkt", "Darkmoon Faire"),
        "dunkelmond": ("Dunkelmond-Jahrmarkt", "Darkmoon Faire"),
        "brewfest": ("Braufest", "Brewfest"),
        "hallow": ("Schlotternächte", "Hallow's End"),
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
            "id": f"event_start_{event_id}", "tab": "events", "level": 3, "icon": ">", "character": "none",
            "label": f"{display} startet" if lang == "de" else f"Start {display}",
            "description": f"Startet Event-ID {event_id}." if lang == "de" else f"Starts event ID {event_id}.",
            "command": f"event start {event_id}",
        })
        actions.append({
            "id": f"event_stop_{event_id}", "tab": "events", "level": 3, "icon": "X", "character": "none",
            "label": f"{display} endet" if lang == "de" else f"Stop {display}",
            "description": f"Beendet Event-ID {event_id}." if lang == "de" else f"Stops event ID {event_id}.",
            "command": f"event stop {event_id}",
        })
    actions.extend([
        {
            "id": "event_custom_start", "tab": "events", "level": 3, "icon": ">", "character": "none",
            "label": "Event-ID starten" if lang == "de" else "Start event ID",
            "description": "Startet ein beliebiges Event per ID." if lang == "de" else "Starts any event by ID.",
            "command": "event start {event_id}",
            "inputs": [{"name": "event_id", "type": "number", "de": "Event-ID", "en": "Event ID", "required": True, "label": "Event-ID" if lang == "de" else "Event ID"}],
        },
        {
            "id": "event_custom_stop", "tab": "events", "level": 3, "icon": "X", "character": "none",
            "label": "Event-ID beenden" if lang == "de" else "Stop event ID",
            "description": "Beendet ein beliebiges Event per ID." if lang == "de" else "Stops any event by ID.",
            "command": "event stop {event_id}",
            "inputs": [{"name": "event_id", "type": "number", "de": "Event-ID", "en": "Event ID", "required": True, "label": "Event-ID" if lang == "de" else "Event ID"}],
        },
    ])
    return actions


def build_command(action: dict, form: dict) -> str:
    values = {key: str(value).strip() for key, value in form.items()}
    command = action["command"]
    if action.get("character") in {"any", "online"}:
        values["character"] = values.get("character", "")
    for field in action.get("inputs", []):
        values.setdefault(field["name"], field.get("default", ""))
    return command.format(**values).strip()
