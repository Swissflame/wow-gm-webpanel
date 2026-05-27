# Backup und Restore

## Backup

```bash
bash scripts/backup.sh
bash scripts/export_package.sh
```

Zusätzlich empfohlen:

```bash
mysqldump wow_gm_webpanel | gzip > wow_gm_webpanel.sql.gz
```

Für WoW-Datenbanken nur nach ausdrücklicher Entscheidung dumpen:

```bash
mysqldump acore_auth acore_world acore_characters pb_world pb_characters acore_playerbots | gzip > acore-all.sql.gz
```

## Restore auf anderem Webserver

1. Projekt entpacken
2. `scripts/install_ubuntu.sh` ausführen
3. `.env` wiederherstellen oder neu erstellen
4. Panel-Datenbank importieren
5. Webpanel öffnen und Verbindungen testen

Der Reset-Button im Panel setzt nicht ungefragt WoW-Datenbanken zurück.
