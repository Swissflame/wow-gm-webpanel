import re


WEB_OUTPUT = "Die Antwort des Worldservers erscheint oben im Webpanel in der Ergebnisbox. Im WoW-Client siehst du nur dann etwas, wenn der Befehl selbst eine Nachricht, Teleportation oder sichtbare Aktion ausloest."
CHAT_OUTPUT = "Die Meldung wird an die betroffenen Spieler im WoW-Chat oder als Bildschirmmeldung ausgegeben. Die SOAP-Antwort erscheint zusaetzlich oben im Webpanel."
TARGET_NOTE = "Das Ingame-GM-Addon nutzt hier oft dein aktuell markiertes Ziel. Im Webpanel gibt es kein Ingame-Target: gib deshalb den Charakternamen ausdruecklich an, falls AzerothCore diese Syntax fuer SOAP unterstuetzt."


MANUAL = {
    "commands": ("Zeigt die fuer deinen GM-Level verfuegbaren Befehle.", ".commands", WEB_OUTPUT),
    "server info": ("Zeigt Worldserver-Version, Uptime, Spielerzahlen und technische Serverdaten.", ".server info", WEB_OUTPUT),
    "server restart": ("Plant einen Neustart des Worldservers nach der angegebenen Zeit.", ".server restart <sekunden>|cancel", CHAT_OUTPUT),
    "server shutdown": ("Plant ein Herunterfahren des Worldservers nach der angegebenen Zeit.", ".server shutdown <sekunden>|cancel", CHAT_OUTPUT),
    "saveall": ("Speichert alle gerade geladenen Charaktere.", ".saveall", WEB_OUTPUT),
    "gm on": ("Aktiviert den GM-Modus fuer den ausfuehrenden GM-Account.", ".gm on", WEB_OUTPUT),
    "gm off": ("Deaktiviert den GM-Modus.", ".gm off", WEB_OUTPUT),
    "gm fly": ("Schaltet GM-Fliegen an oder aus.", ".gm fly on|off", WEB_OUTPUT),
    "gm visible": ("Schaltet deine Sichtbarkeit fuer Spieler an oder aus.", ".gm visible on|off", WEB_OUTPUT),
    "gm chat": ("Schaltet die GM-Markierung im Chat an oder aus.", ".gm chat on|off", WEB_OUTPUT),
    "gm list": ("Listet GM-Accounts bzw. GM-Charaktere.", ".gm list", WEB_OUTPUT),
    "gm ingame": ("Listet aktuell eingeloggte GMs.", ".gm ingame", WEB_OUTPUT),
    "account": ("Zeigt Informationen zu deinem Account und Zugriff an.", ".account", WEB_OUTPUT),
    "account create": ("Erstellt einen neuen WoW-Account.", ".account create <accountname> <passwort>", WEB_OUTPUT),
    "account delete": ("Loescht einen WoW-Account. Vorsicht: nur verwenden, wenn du die Folgen kennst.", ".account delete <accountname>", WEB_OUTPUT),
    "account set gmlevel": ("Setzt den GM-Level eines Accounts fuer einen Realm.", ".account set gmlevel <accountname> <gmlevel> <realmid>", WEB_OUTPUT),
    "account set password": ("Setzt das Passwort eines WoW-Accounts neu.", ".account set password <accountname> <neues_passwort> <neues_passwort>", WEB_OUTPUT),
    "account set addon": ("Setzt die erlaubte Addon-Version/Expansion fuer einen Account.", ".account set addon <accountname> <addon_id>", WEB_OUTPUT),
    "account lock ip": ("Schaltet IP-Lock fuer den eigenen Account an oder aus.", ".account lock ip on|off", WEB_OUTPUT),
    "announce": ("Sendet eine globale Chat-Ankuendigung an alle Spieler.", ".announce <nachricht>", CHAT_OUTPUT),
    "notify": ("Sendet eine Bildschirmmeldung an alle Spieler.", ".notify <nachricht>", CHAT_OUTPUT),
    "gmannounce": ("Sendet eine Chat-Ankuendigung nur an GMs.", ".gmannounce <nachricht>", CHAT_OUTPUT),
    "gmnotify": ("Sendet eine Bildschirmmeldung nur an GMs.", ".gmnotify <nachricht>", CHAT_OUTPUT),
    "gmnameannounce": ("Sendet eine GM-Ankuendigung mit deinem GM-Namen.", ".gmnameannounce <nachricht>", CHAT_OUTPUT),
    "nameannounce": ("Sendet eine Ankuendigung mit Absendernamen.", ".nameannounce <nachricht>", CHAT_OUTPUT),
    "appear": ("Teleportiert dich zu einem online Charakter.", ".appear <charaktername>", WEB_OUTPUT),
    "summon": ("Teleportiert einen online Charakter zu dir.", ".summon <charaktername>", CHAT_OUTPUT),
    "groupsummon": ("Teleportiert einen Charakter und seine Gruppe zu dir.", ".groupsummon <charaktername>", CHAT_OUTPUT),
    "teleport": ("Teleportiert dich zu einem gespeicherten Teleport-Ort.", ".teleport <ort>", WEB_OUTPUT),
    "teleport name": ("Teleportiert einen Charakter zu einem gespeicherten Teleport-Ort.", ".teleport name <charaktername> <ort>", CHAT_OUTPUT),
    "teleport group": ("Teleportiert die Gruppe eines Charakters zu einem Ort.", ".teleport group <charaktername> <ort>", CHAT_OUTPUT),
    "teleport add": ("Speichert deine aktuelle Position als Teleport-Ort.", ".teleport add <ort>", WEB_OUTPUT),
    "teleport del": ("Loescht einen gespeicherten Teleport-Ort.", ".teleport del <ort>", WEB_OUTPUT),
    "go xy": ("Teleportiert dich auf der aktuellen Map zu X/Y.", ".go xy <x> <y>", WEB_OUTPUT),
    "go xyz": ("Teleportiert dich auf der aktuellen Map zu X/Y/Z.", ".go xyz <x> <y> <z>", WEB_OUTPUT),
    "go zonexy": ("Teleportiert dich zu relativen Zonenkoordinaten.", ".go zonexy <x> <y> <zoneid>", WEB_OUTPUT),
    "go taxinode": ("Teleportiert dich zu einem Flugpunkt.", ".go taxinode <taxinode_id>", WEB_OUTPUT),
    "go trigger": ("Teleportiert dich zu einem Area-Trigger.", ".go trigger <trigger_id>", WEB_OUTPUT),
    "revive": ("Belebt einen toten Charakter wieder. Ueber SOAP funktioniert das je nach Core nur mit explizitem Namen oder gar nur mit Ingame-Target.", ".revive <charaktername>", CHAT_OUTPUT),
    "kick": ("Wirft einen Spieler vom Server.", ".kick <charaktername> [grund]", CHAT_OUTPUT),
    "pinfo": ("Zeigt Account-, Charakter- und Verbindungsinformationen.", ".pinfo <charaktername>", WEB_OUTPUT),
    "guid": ("Zeigt die GUID des ausgewaehlten Objekts oder Charakters.", ".guid [charaktername]", WEB_OUTPUT),
    "gps": ("Zeigt Map, Zone und Koordinaten.", ".gps [charaktername]", WEB_OUTPUT),
    "distance": ("Zeigt die Entfernung zum Ziel. Im Webpanel nur eingeschraenkt sinnvoll, weil kein Ingame-Target existiert.", ".distance [charaktername]", WEB_OUTPUT),
    "die": ("Toetet das Ziel oder den angegebenen Charakter.", ".die [charaktername]", CHAT_OUTPUT),
    "recall": ("Teleportiert einen Charakter zur Position vor dem letzten Teleport zurueck.", ".recall [charaktername]", CHAT_OUTPUT),
    "character rename": ("Markiert einen Charakter fuer Umbenennung beim naechsten Login.", ".character rename <charaktername>", CHAT_OUTPUT),
    "character customize": ("Markiert einen Charakter fuer Aussehens-Anpassung beim naechsten Login.", ".character customize <charaktername>", CHAT_OUTPUT),
    "character changerace": ("Markiert einen Charakter fuer Volkswechsel beim naechsten Login.", ".character changerace <charaktername>", CHAT_OUTPUT),
    "character changefaction": ("Markiert einen Charakter fuer Fraktionswechsel beim naechsten Login.", ".character changefaction <charaktername>", CHAT_OUTPUT),
    "character level": ("Setzt oder aendert das Level eines Charakters.", ".character level <charaktername> <level>", CHAT_OUTPUT),
    "character check bank": ("Oeffnet oder prueft die Bank des Zielcharakters. Ueber Web/SOAP meist nur eingeschraenkt nutzbar.", ".character check bank [charaktername]", WEB_OUTPUT),
    "combatstop": ("Beendet den Kampfstatus des Zielcharakters.", ".combatstop [charaktername]", CHAT_OUTPUT),
    "maxskill": ("Setzt die Waffenskills/Berufe des Zielcharakters passend zum Level auf Maximum.", ".maxskill [charaktername]", CHAT_OUTPUT),
    "freeze": ("Friert einen Charakter ein.", ".freeze <charaktername>", CHAT_OUTPUT),
    "unfreeze": ("Hebt Freeze fuer einen Charakter auf.", ".unfreeze <charaktername>", CHAT_OUTPUT),
    "repairitems": ("Repariert alle Items eines Charakters.", ".repairitems [charaktername]", CHAT_OUTPUT),
    "morph": ("Aendert das Aussehen des Zielcharakters auf eine Display-ID.", ".morph <display_id> [charaktername]", CHAT_OUTPUT),
    "demorph": ("Entfernt einen Morph-Effekt.", ".demorph [charaktername]", CHAT_OUTPUT),
    "modify money": ("Aendert das Geld des Zielcharakters in Kupfer.", ".modify money <kupferbetrag> [charaktername]", CHAT_OUTPUT),
    "modify speed": ("Aendert Bewegungsgeschwindigkeit des Zielcharakters.", ".modify speed <typ> <wert> [charaktername]", CHAT_OUTPUT),
    "modify scale": ("Aendert die Groesse des Zielcharakters.", ".modify scale <wert> [charaktername]", CHAT_OUTPUT),
    "honor add": ("Fuegt einem Charakter Ehrenpunkte hinzu.", ".honor add <punkte> [charaktername]", CHAT_OUTPUT),
    "honor update": ("Aktualisiert/speichert Ehre des Zielcharakters.", ".honor update [charaktername]", WEB_OUTPUT),
    "reset": ("Setzt einen Charakterbereich zurueck, z.B. Talente, Spells oder Stats.", ".reset <talents|spells|stats|level|honor> [charaktername]", CHAT_OUTPUT),
    "learn": ("Lehrt dem Zielcharakter einen Spell.", ".learn <spell_id> [charaktername]", CHAT_OUTPUT),
    "unlearn": ("Entfernt einen Spell vom Zielcharakter.", ".unlearn <spell_id> [charaktername]", CHAT_OUTPUT),
    "learn all my pettalents": ("Lehrt alle passenden Pet-Talente.", ".learn all my pettalents", CHAT_OUTPUT),
    "aura": ("Legt eine Aura auf das Ziel.", ".aura <spell_id> [charaktername]", CHAT_OUTPUT),
    "unaura": ("Entfernt eine Aura vom Ziel.", ".unaura <spell_id> [charaktername]", CHAT_OUTPUT),
    "cast": ("Laesst einen Spell wirken. Ziel/Variante haengt vom Unterbefehl ab.", ".cast <spell_id>", CHAT_OUTPUT),
    "cast back": ("Laesst das Ziel einen Spell auf dich zurueckwirken.", ".cast back <spell_id>", CHAT_OUTPUT),
    "cast dist": ("Wirkt einen Spell auf Distanz.", ".cast dist <spell_id> <distanz>", CHAT_OUTPUT),
    "cast self": ("Wirkt einen Spell auf dich selbst.", ".cast self <spell_id>", CHAT_OUTPUT),
    "cast target": ("Wirkt einen Spell auf dein Ziel.", ".cast target <spell_id>", CHAT_OUTPUT),
    "quest add": ("Fuegt dem Zielcharakter eine Quest hinzu.", ".quest add <quest_id> [charaktername]", CHAT_OUTPUT),
    "quest remove": ("Entfernt eine Quest vom Zielcharakter.", ".quest remove <quest_id> [charaktername]", CHAT_OUTPUT),
    "quest complete": ("Markiert eine Quest fuer den Zielcharakter als abgeschlossen.", ".quest complete <quest_id> [charaktername]", CHAT_OUTPUT),
    "damage": ("Fuegt dem Ziel Schaden zu.", ".damage <schaden> [charaktername]", CHAT_OUTPUT),
    "showarea": ("Deckt einem Charakter eine Area-ID auf.", ".showarea <area_id> [charaktername]", CHAT_OUTPUT),
    "hidearea": ("Verbirgt einem Charakter eine Area-ID.", ".hidearea <area_id> [charaktername]", CHAT_OUTPUT),
    "send mail": ("Sendet Post an einen Charakter.", ".send mail <charaktername> \"<betreff>\" \"<text>\"", CHAT_OUTPUT),
    "send money": ("Sendet Geld per Post an einen Charakter. Betrag ist Kupfer.", ".send money <charaktername> \"<betreff>\" \"<text>\" <kupferbetrag>", CHAT_OUTPUT),
    "send items": ("Sendet Items per Post an einen Charakter.", ".send items <charaktername> \"<betreff>\" \"<text>\" <item_id>:<anzahl>", CHAT_OUTPUT),
    "additem": ("Gibt dem Ziel oder angegebenen Charakter ein Item.", ".additem <item_id> [anzahl] oder .additem <charaktername> <item_id> <anzahl>", CHAT_OUTPUT),
    "list item": ("Listet Items anhand Name oder ID.", ".list item <suchtext>", WEB_OUTPUT),
    "lookup item": ("Sucht Item-IDs nach Name.", ".lookup item <name>", WEB_OUTPUT),
    "lookup quest": ("Sucht Quest-IDs nach Name.", ".lookup quest <name>", WEB_OUTPUT),
    "lookup creature": ("Sucht Creature-IDs nach Name.", ".lookup creature <name>", WEB_OUTPUT),
    "lookup object": ("Sucht GameObject-IDs nach Name.", ".lookup object <name>", WEB_OUTPUT),
    "lookup tele": ("Sucht Teleport-Orte.", ".lookup tele <name>", WEB_OUTPUT),
    "lookup area": ("Sucht Area-IDs.", ".lookup area <name>", WEB_OUTPUT),
    "lookup taxi": ("Sucht Flugpunkt-IDs.", ".lookup taxi <name>", WEB_OUTPUT),
    "event start": ("Startet ein Game Event, z.B. Dunkelmond-Jahrmarkt, wenn die Event-ID passt.", ".event start <event_id>", CHAT_OUTPUT),
    "event stop": ("Beendet ein Game Event.", ".event stop <event_id>", CHAT_OUTPUT),
    "event info": ("Zeigt Informationen zu einem Game Event.", ".event info <event_id>", WEB_OUTPUT),
    "event activelist": ("Listet aktive Game Events.", ".event activelist", WEB_OUTPUT),
    "wchange": ("Aendert Wetter in der aktuellen Zone des ausfuehrenden Charakters. Achtung: manche AzerothCore-Builds akzeptieren wchange nicht ueber SOAP.", ".wchange <wetter_id> <staerke 0.0-1.0>", CHAT_OUTPUT),
    "cheat god": ("Schaltet Gottmodus fuer den GM-Charakter an oder aus.", ".cheat god on|off", WEB_OUTPUT),
    "cheat cooldown": ("Schaltet Abklingzeiten fuer den GM-Charakter aus oder wieder an.", ".cheat cooldown on|off", WEB_OUTPUT),
    "cheat casttime": ("Schaltet Zauberzeit fuer den GM-Charakter aus oder wieder an.", ".cheat casttime on|off", WEB_OUTPUT),
    "cheat taxi": ("Schaltet alle Flugpunkte fuer den GM-Charakter frei oder zurueck.", ".cheat taxi on|off", WEB_OUTPUT),
    "cheat waterwalk": ("Schaltet Wasserlaufen fuer den GM-Charakter an oder aus.", ".cheat waterwalk on|off", WEB_OUTPUT),
    "ban account": ("Sperrt einen Account fuer eine Dauer mit Grund.", ".ban account <accountname> <dauer> <grund>", WEB_OUTPUT),
    "ban character": ("Sperrt einen Charakter fuer eine Dauer mit Grund.", ".ban character <charaktername> <dauer> <grund>", WEB_OUTPUT),
    "ban ip": ("Sperrt eine IP-Adresse fuer eine Dauer mit Grund.", ".ban ip <ip> <dauer> <grund>", WEB_OUTPUT),
    "unban account": ("Hebt eine Account-Sperre auf.", ".unban account <accountname>", WEB_OUTPUT),
    "unban character": ("Hebt eine Charakter-Sperre auf.", ".unban character <charaktername>", WEB_OUTPUT),
    "unban ip": ("Hebt eine IP-Sperre auf.", ".unban ip <ip>", WEB_OUTPUT),
    "baninfo account": ("Zeigt Ban-Informationen zu einem Account.", ".baninfo account <accountname>", WEB_OUTPUT),
    "banlist account": ("Listet Accountsperren passend zum Suchtext.", ".banlist account <suchtext>", WEB_OUTPUT),
    "mute": ("Schaltet Chat-Stummschaltung fuer einen Account/Charakter.", ".mute <charaktername> <minuten> <grund>", CHAT_OUTPUT),
    "unmute": ("Hebt eine Chat-Stummschaltung auf.", ".unmute <charaktername>", CHAT_OUTPUT),
    "guild create": ("Erstellt eine Gilde mit dem angegebenen Leiter.", ".guild create <leiter_charakter> \"<gildenname>\"", CHAT_OUTPUT),
    "guild delete": ("Loescht eine Gilde.", ".guild delete \"<gildenname>\"", CHAT_OUTPUT),
    "guild invite": ("Laedt einen Charakter in eine Gilde ein.", ".guild invite <charaktername> \"<gildenname>\"", CHAT_OUTPUT),
    "guild uninvite": ("Entfernt einen Charakter aus seiner Gilde.", ".guild uninvite <charaktername>", CHAT_OUTPUT),
    "guild rank": ("Setzt den Gildenrang eines Charakters.", ".guild rank <charaktername> <rang>", CHAT_OUTPUT),
    "pet create": ("Erstellt ein Pet aus der ausgewaehlten Kreatur. Im Webpanel nur mit Ingame-Target sinnvoll.", ".pet create", CHAT_OUTPUT),
    "pet learn": ("Lehrt dem Pet einen Spell.", ".pet learn <spell_id>", CHAT_OUTPUT),
    "pet unlearn": ("Entfernt dem Pet einen Spell.", ".pet unlearn <spell_id>", CHAT_OUTPUT),
    "dismount": ("Laesst den Zielcharakter absitzen.", ".dismount [charaktername]", CHAT_OUTPUT),
    "reload all": ("Laedt Serverdaten neu. Kann kurz ruckeln; nicht jede Aenderung braucht das.", ".reload all", WEB_OUTPUT),
}

TARGET_BASED = {
    "revive", "save", "cooldown", "guid", "pinfo", "distance", "die", "recall", "gps", "bindsight",
    "unbindsight", "combatstop", "maxskill", "freeze", "unfreeze", "possess", "unpossess", "repairitems",
    "morph", "demorph", "aura", "unaura", "quest add", "quest remove", "quest complete", "damage",
    "showarea", "hidearea", "honor add", "honor update", "reset", "learn", "unlearn", "modify money",
    "modify speed", "modify scale", "pet create", "dismount",
}


def command_help(name: str, db_help: str = "", lang: str = "de") -> dict:
    normalized = " ".join((name or "").strip().lstrip(".").split()).lower()
    key = _best_key(normalized)
    if key:
        summary, syntax, output = MANUAL[key]
    else:
        summary = _translate_help(db_help) if db_help else f"Fuehrt den AzerothCore-Befehl .{normalized} aus."
        syntax = _syntax_from_help(normalized, db_help)
        output = WEB_OUTPUT
    notes = []
    if _best_target_key(normalized):
        notes.append(TARGET_NOTE)
    if normalized.startswith("wchange"):
        notes.append("Auf deinem Server wurde beobachtet, dass wchange ueber SOAP als nicht vorhanden gemeldet werden kann, obwohl der Befehl in der DB steht.")
    if lang == "en":
        return {
            "summary": _english_summary(normalized, db_help),
            "syntax": syntax,
            "output": "The worldserver response is shown in the result box at the top of the web panel. Player-visible commands also appear in game.",
            "notes": " ".join(notes) if notes else "",
            "tooltip": _format_tooltip(_english_summary(normalized, db_help), syntax, "The worldserver response is shown in the result box at the top of the web panel. Player-visible commands also appear in game.", " ".join(notes)),
        }
    tooltip = _format_tooltip(summary, syntax, output, " ".join(notes))
    return {"summary": summary, "syntax": syntax, "output": output, "notes": " ".join(notes), "tooltip": tooltip}


def _best_key(normalized: str) -> str | None:
    candidates = sorted(MANUAL.keys(), key=len, reverse=True)
    for key in candidates:
        if normalized == key or normalized.startswith(f"{key} "):
            return key
    return None


def _best_target_key(normalized: str) -> str | None:
    for key in sorted(TARGET_BASED, key=len, reverse=True):
        if normalized == key or normalized.startswith(f"{key} "):
            return key
    return None


def _format_tooltip(summary: str, syntax: str, output: str, notes: str = "") -> str:
    parts = [
        "Was passiert?\n" + summary,
        "Syntax\n" + syntax,
        "Ausgabe\n" + output,
    ]
    if notes:
        parts.append("Hinweis\n" + notes)
    return "\n\n".join(parts)


def _syntax_from_help(name: str, help_text: str) -> str:
    if help_text:
        match = re.search(r"\.(\S.*)", help_text)
        if match:
            return "." + match.group(1).strip().replace("$", "<").replace("  ", " ")
    return "." + name


def _translate_help(text: str) -> str:
    value = (text or "").strip()
    replacements = [
        ("Syntax:", "Syntax:"),
        ("Usage:", "Anwendung:"),
        ("Displays", "Zeigt"),
        ("Display", "Zeigt"),
        ("Shows", "Zeigt"),
        ("Show", "Zeigt"),
        ("List", "Listet"),
        ("lists", "listet"),
        ("Set", "Setzt"),
        ("Sets", "Setzt"),
        ("Add", "Fuegt hinzu"),
        ("Adds", "Fuegt hinzu"),
        ("Remove", "Entfernt"),
        ("Removes", "Entfernt"),
        ("Teleport", "Teleportiert"),
        ("Teleports", "Teleportiert"),
        ("selected player", "ausgewaehlten Spieler"),
        ("selected unit", "ausgewaehlte Einheit"),
        ("character", "Charakter"),
        ("player", "Spieler"),
        ("account", "Account"),
        ("name", "Name"),
        ("password", "Passwort"),
        ("message", "Nachricht"),
    ]
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def _english_summary(name: str, db_help: str) -> str:
    key = _best_key(name)
    if key:
        return db_help or f"Runs the AzerothCore command .{name}."
    return db_help or f"Runs the AzerothCore command .{name}."
