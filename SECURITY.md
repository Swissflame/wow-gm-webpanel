# Sicherheit

- `.env`, Dumps, Backups und Logs sind in `.gitignore`
- CSRF-Token für POST-Aktionen
- Sessions sind signiert
- Adminaktionen werden im Audit-Log protokolliert
- GM-Menüs und Aktionen werden nach GM-Level gefiltert
- AzerothCore Login unterstützt aktuelle SRP6-Felder `salt`/`verifier` und alte `sha_pass_hash`

## Empfehlung

- Panel nur im LAN oder hinter VPN betreiben
- HTTPS über Reverse Proxy aktivieren
- Eigenen SSH-Benutzer mit eingeschränkten sudo-Regeln verwenden
- MySQL-Benutzer nur mit nötigen Rechten ausstatten
- Keine Serverpasswörter in Git oder Tickets kopieren

## Eingeschränkte Befehlsausführung

GM-Befehle werden protokolliert. SOAP/RA muss am Worldserver bewusst aktiviert werden, bevor Befehle live gesendet werden. Das verhindert unsichere Konsolenzugriffe.
