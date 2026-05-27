TRANSLATIONS = {
    "de": {
        "Dashboard": "Dashboard", "Server": "Server", "Online Players": "Online-Spieler",
        "Accounts": "Accounts", "Characters": "Charaktere", "GM Commands": "GM-Befehle",
        "Configs": "Configs", "Logs": "Logs", "Backup/Restore": "Backup/Restore",
        "Settings": "Einstellungen", "Logout": "Logout", "Realm": "Realm", "Language": "Sprache",
        "Setup": "Setup", "Connection problem": "Verbindungsproblem",
        "No data available": "Keine Daten verfügbar", "Search": "Suchen",
        "Save": "Speichern", "Command": "Befehl", "Run": "Ausführen",
        "Normal Realm": "Normal-Realm", "Playerbot Realm": "Playerbot-Realm",
        "All realms": "Alle Realms", "Feature unavailable": "Funktion für diesen Realm nicht verfügbar",
    },
    "en": {
        "Dashboard": "Dashboard", "Server": "Server", "Online Players": "Online Players",
        "Accounts": "Accounts", "Characters": "Characters", "GM Commands": "GM Commands",
        "Configs": "Configs", "Logs": "Logs", "Backup/Restore": "Backup/Restore",
        "Settings": "Settings", "Logout": "Logout", "Realm": "Realm", "Language": "Language",
        "Setup": "Setup", "Connection problem": "Connection problem",
        "No data available": "No data available", "Search": "Search",
        "Save": "Save", "Command": "Command", "Run": "Run",
        "Normal Realm": "Normal Realm", "Playerbot Realm": "Playerbot Realm",
        "All realms": "All realms", "Feature unavailable": "Feature unavailable for this realm",
    },
}


def translate(lang: str, text: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["de"]).get(text, text)
