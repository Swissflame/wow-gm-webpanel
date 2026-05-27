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
    except Exception as exc:
        return f"SOAP-Fehler: {exc}"

    match = re.search(r"<result>(.*?)</result>", response.text, re.S)
    if match:
        result = html.unescape(match.group(1)).strip()
        if "does not exist" in result:
            return f"SOAP-Fehler: {result}. Der Befehl ist in der Datenbank vorhanden, aber in der Worldserver-Konsole/SOAP nicht ausführbar oder die Syntax ist für SOAP anders."
        return result or "Befehl ausgeführt."
    fault = re.search(r"<faultstring>(.*?)</faultstring>", response.text, re.S)
    if fault:
        return f"SOAP-Fehler: {html.unescape(fault.group(1)).strip()}"
    if response.status_code >= 400:
        return f"SOAP-Fehler HTTP {response.status_code}: {response.text.strip()[:1200]}"
    return response.text.strip()[:2000] or "Befehl ausgeführt."
