# Installation

## Voraussetzungen

- Ubuntu/Debian Container oder VM
- Root- oder sudo-Rechte
- Netzwerkzugriff vom Webpanel zum AzerothCore-MySQL und per SSH zum WoW-Server
- Kein Docker erforderlich

## Automatisch installieren

```bash
sudo bash scripts/install_ubuntu.sh
```

Das Skript installiert Python, Nginx, MariaDB, erstellt die lokale Panel-Datenbank, richtet systemd ein und startet das Panel auf Port 80.

## Erstsetup

1. Browser öffnen: `http://<panel-server-ip>/`
2. Sprache wählen
3. WoW-Server-IP eintragen
4. SSH-Daten eintragen
5. MySQL-Daten des WoW-Servers eintragen
6. Admin-Benutzer anlegen
7. Speichern

Empfohlene Werte für dein Setup:

- WoW-Server: `192.168.1.118`
- SSH-Benutzer: `klaus`
- MySQL-Benutzer: `acore`
- Auth-DB: `acore_auth`
- World-DB: `acore_world`
- Characters-DB: `acore_characters`
- Playerbot-DBs: `pb_world`, `pb_characters`, `acore_playerbots`

Passwörter werden nicht committet. Sie werden in `.env` oder in der Panel-Datenbank gespeichert.
