import html
import re
import httpx
from ..services.config_store import get_config


def execute_gm_command(db, cfg: dict, realm: str, command: str) -> str:
    transport = get_config(db, "gm_transport", {}) or {}
    if transport.get("mode") != "soap":
        return "Nicht gesendet: SOAP/RA ist im Webpanel noch nicht konfiguriert. Der Befehl wurde protokolliert."
    username = transport.get("username")
    password = transport.get("password")
    if not username or not password:
        return "Nicht gesendet: SOAP ist aktiv, aber Benutzer/Passwort fehlen in der Webpanel-Konfiguration."

    host = transport.get("playerbot_host" if realm == "playerbot" else "normal_host") or cfg["server"]["wow_host"]
    port = int(transport.get("playerbot_port" if realm == "playerbot" else "normal_port") or 7878)
    soap_command = command if command.startswith(".") else f".{command}"
    body = f"""<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="urn:AC" xmlns:xsd="http://www.w3.org/1999/XMLSchema" xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<SOAP-ENV:Body><ns1:executeCommand><command>{html.escape(soap_command)}</command></ns1:executeCommand></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
    try:
        response = httpx.post(
            f"http://{host}:{port}/",
            content=body.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "urn:AC#executeCommand"},
            auth=(username, password),
            timeout=8,
        )
        if response.status_code == 401:
            return "SOAP-Fehler: Zugangsdaten wurden abgelehnt."
        response.raise_for_status()
    except Exception as exc:
        return f"SOAP-Fehler: {exc}"

    match = re.search(r"<result>(.*?)</result>", response.text, re.S)
    if match:
        return html.unescape(match.group(1)).strip() or "Befehl ausgeführt."
    return response.text.strip()[:2000] or "Befehl ausgeführt."
