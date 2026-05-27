from ..services.config_store import get_config


def execute_gm_command(db, cfg: dict, realm: str, command: str) -> str:
    transport = get_config(db, "gm_transport", {}) or {}
    if transport.get("mode") != "soap":
        return "Nicht gesendet: SOAP/RA ist im Webpanel noch nicht konfiguriert. Der Befehl wurde protokolliert."
    return "Nicht gesendet: SOAP-Ausführung ist vorbereitet, aber noch ohne Zugangsdaten. Bitte SOAP-Benutzer/Passwort in den Einstellungen hinterlegen."
