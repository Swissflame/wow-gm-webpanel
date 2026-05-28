# Konfiguration

Der Setup-Wizard speichert die Webpanel-Konfiguration in der lokalen Panel-Datenbank. `.env` enthält nur App-Secret und Panel-Datenbankverbindung.

## Configscanner

Der Scanner liest per SSH alle `.conf` Dateien unter:

- `/opt/azeroth-server/etc`
- `/opt/azeroth-server/etc/modules`
- `/opt/azeroth-playerbots-server/etc`
- `/opt/azeroth-playerbots-server/etc/modules`

Kommentare direkt oberhalb eines Schlüssels werden als Beschreibung angezeigt. Typen werden heuristisch erkannt: Boolean, Zahl, Text, Pfad, Passwort.

Vor jeder Änderung wird eine Backup-Datei mit `.wowpanel.bak` erstellt. GM-Level 3 und 4 dürfen Konfigurationen ändern; Level 4 wird als höchste Admin-/Console-Stufe unterstützt.

## Server-Neustart

Serveraktionen laufen per SSH. Für produktive Nutzung sollten `systemd` Units für `authserver` und `worldserver` eingerichtet und die SSH-Rechte auf genau diese Befehle beschränkt werden.
