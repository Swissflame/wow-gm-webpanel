# wow-gm-webpanel

Webbasiertes GM-/Admin-Panel für private AzerothCore 3.3.5a Server mit Normal-Realm, Playerbot-Realm und AHBot.

## Funktionen

- Setup-Wizard für Sprache, WoW-Server, SSH, MySQL und Admin-Konto
- Login über Webpanel-Konto oder AzerothCore `account` mit `salt`/`verifier` beziehungsweise altem `sha_pass_hash`
- GM-Level aus `acore_auth.account_access`
- Dashboard, Online-Spieler, Accounts, Charaktere, GM-Befehle, Serversteuerung
- Configscanner für alle `.conf` unter Normal- und Playerbot-Serverpfaden
- AHBot- und Playerbot-Ansichten
- Audit-Log, CSRF-Schutz, Session-Schutz
- Reset auf Standard ohne ungefragtes Zurücksetzen der WoW-Datenbanken

## Schnellstart

```bash
sudo bash scripts/install_ubuntu.sh
```

Danach im Browser `http://SERVER-IP/` öffnen und den Setup-Wizard ausfüllen.

## Stack

FastAPI, Jinja2, SQLAlchemy, MariaDB/MySQL, Nginx, systemd, Paramiko.
