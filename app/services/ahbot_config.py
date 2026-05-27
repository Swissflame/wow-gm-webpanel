from dataclasses import dataclass
from .config_scanner import scan_content, update_value
from .ssh_service import SSHClient, shell_quote


@dataclass
class AhbotField:
    key: str
    value: str
    default: str | None
    label: str
    description: str
    group: str
    type: str
    line: int


GROUPS = [
    ("basis", "Grundbetrieb"),
    ("bot", "Bot-Charakter"),
    ("markt", "Markt & Preise"),
    ("seller", "Verkäufer"),
    ("buyer", "Käufer"),
    ("filter", "Item-Filter"),
    ("quality", "Qualität & Itemlevel"),
    ("debug", "Debug & Protokollierung"),
    ("other", "Weitere Optionen"),
]


META = {
    "AuctionHouseBot.EnableSeller": ("Verkäufer aktiv", "Der AHBot stellt selbst Auktionen ein. Ohne diese Option füllt er das Auktionshaus nicht."),
    "AuctionHouseBot.EnableBuyer": ("Käufer aktiv", "Der AHBot kauft Spielerauktionen nach den eingestellten Regeln auf."),
    "AuctionHouseBot.Account": ("Account-ID des AHBot", "Account-ID aus acore_auth.account, unter der der AHBot-Charakter geführt wird."),
    "AuctionHouseBot.GUID": ("Charakter-GUID des AHBot", "GUID des Charakters aus der characters-Tabelle, der als Auktionshaus-Bot verwendet wird."),
    "AuctionHouseBot.ItemsPerCycle": ("Items pro Zyklus", "Anzahl Items, die der AHBot pro Arbeitszyklus einstellt oder entfernt. Höhere Werte wirken schneller, erzeugen aber mehr Last."),
    "AuctionHouseBot.UseBuyPriceForSeller": ("Verkäufer nutzt Kaufpreis", "Wenn aktiv, nutzt der Verkäufer den BuyPrice statt SellPrice als Preisbasis."),
    "AuctionHouseBot.UseBuyPriceForBuyer": ("Käufer nutzt Kaufpreis", "Wenn aktiv, nutzt der Käufer den BuyPrice statt SellPrice als Preisbasis."),
    "AuctionHouseBot.UseMarketPriceForSeller": ("Marktpreis nutzen", "Wenn aktiv, orientiert sich der Verkäufer am beobachteten Marktpreis."),
    "AuctionHouseBot.MarketResetThreshold": ("Marktpreis-Schwelle", "Anzahl gleicher Auktionen, ab der der Marktpreis als stabil gilt. Niedrig reagiert schnell, hoch glättet Preisschwankungen."),
    "AuctionHouseBot.ConsiderOnlyBotAuctions": ("Nur Bot-Auktionen zählen", "Spielerauktionen werden bei der Bestandssteuerung ignoriert. Nützlich, wenn Spielerhandel den Bot nicht ausbremsen soll."),
    "AuctionHouseBot.DuplicatesCount": ("Maximale doppelte Stapel", "Begrenzt, wie viele gleiche Stapel der Bot gleichzeitig anbietet. 0 bedeutet keine Begrenzung."),
    "AuctionHouseBot.DivisibleStacks": ("Teilbare Stapelgrößen", "Verkauft Stapel in festen Größen passend zur maximalen Stapelgröße, statt zufällig."),
    "AuctionHouseBot.ElapsingTimeClass": ("Auktionsdauer-Klasse", "0 = lang, 1 = mittel, 2 = kurz. Bestimmt, wie lange Bot-Auktionen laufen."),
    "AuctionHouseBot.VendorItems": ("Händler-Items zulassen", "Items einschließen, die regulär bei NPC-Händlern kaufbar sind."),
    "AuctionHouseBot.VendorTradeGoods": ("Händler-Handwerkswaren zulassen", "Handwerkswaren einschließen, die bei NPC-Händlern kaufbar sind."),
    "AuctionHouseBot.LootItems": ("Loot-Items zulassen", "Items einschließen, die durch Loot oder Angeln erhältlich sind."),
    "AuctionHouseBot.LootTradeGoods": ("Loot-Handwerkswaren zulassen", "Handwerkswaren einschließen, die durch Loot oder Angeln erhältlich sind."),
    "AuctionHouseBot.OtherItems": ("Sonstige Items zulassen", "Sonstige nicht klar eingeordnete Items einschließen."),
    "AuctionHouseBot.OtherTradeGoods": ("Sonstige Handwerkswaren zulassen", "Sonstige Trade-Goods einschließen."),
    "AuctionHouseBot.ProfessionItems": ("Berufsitems zulassen", "Items einschließen, die für Berufe benötigt werden."),
    "AuctionHouseBot.No_Bind": ("Nicht gebundene Items", "Nicht gebundene Items dürfen verkauft werden."),
    "AuctionHouseBot.Bind_When_Picked_Up": ("Beim Aufheben gebunden", "BoP-Items dürfen verkauft werden. Meist besser deaktiviert."),
    "AuctionHouseBot.Bind_When_Equipped": ("Beim Anlegen gebunden", "BoE-Items dürfen verkauft werden."),
    "AuctionHouseBot.Bind_When_Use": ("Beim Benutzen gebunden", "Beim Benutzen gebundene Items dürfen verkauft werden."),
    "AuctionHouseBot.Bind_Quest_Item": ("Questitems", "Questitems dürfen verkauft werden. Meist besser deaktiviert."),
    "AuctionHouseBot.DisablePermEnchant": ("Permanente Verzauberungen blockieren", "Items mit permanenter Verzauberung werden ausgeschlossen."),
    "AuctionHouseBot.DisableConjured": ("Herbeigezauberte Items blockieren", "Herbeigezauberte Items werden ausgeschlossen."),
    "AuctionHouseBot.DisableGems": ("Edelsteine blockieren", "Edelsteine werden ausgeschlossen."),
    "AuctionHouseBot.DisableMoney": ("Geld-Items blockieren", "Items, die als Geld/Währung dienen, werden ausgeschlossen."),
    "AuctionHouseBot.DisableMoneyLoot": ("Geld-Loot blockieren", "Items, die Geld enthalten können, werden ausgeschlossen."),
    "AuctionHouseBot.DisableLootable": ("Lootbare Container blockieren", "Items, die andere Items enthalten, werden ausgeschlossen."),
    "AuctionHouseBot.DisableKeys": ("Schlüssel blockieren", "Schlüssel werden ausgeschlossen."),
    "AuctionHouseBot.DisableDuration": ("Zeitlich begrenzte Items blockieren", "Items mit Ablaufdauer werden ausgeschlossen."),
    "AuctionHouseBot.DisableBOP_Or_Quest_NoReqLevel": ("Problematische BoP/Questitems blockieren", "Blockiert BoP- oder Questitems ohne passende Levelanforderung."),
    "AuctionHouseBot.DEBUG": ("Debug aktivieren", "Schreibt allgemeine Debug-Ausgaben des AHBot."),
    "AuctionHouseBot.DEBUG_CONFIG": ("Config-Debug", "Schreibt Debug-Ausgaben beim Einlesen der Konfiguration."),
    "AuctionHouseBot.DEBUG_FILTERS": ("Filter-Debug", "Schreibt Debug-Ausgaben zu Itemfiltern."),
    "AuctionHouseBot.DEBUG_BUYER": ("Käufer-Debug", "Schreibt Debug-Ausgaben des Käufer-Moduls."),
    "AuctionHouseBot.DEBUG_SELLER": ("Verkäufer-Debug", "Schreibt Debug-Ausgaben des Verkäufer-Moduls."),
    "AuctionHouseBot.TRACE_SELLER": ("Verkäufe protokollieren", "Protokolliert durch den Bot verkaufte Items detaillierter."),
    "AuctionHouseBot.TRACE_BUYER": ("Käufe protokollieren", "Protokolliert durch den Bot gekaufte Items detaillierter."),
}


def ahbot_path(cfg: dict, realm: str) -> str:
    base = cfg["server"]["playerbot_path"] if realm == "playerbot" else cfg["server"]["normal_path"]
    return f"{base}/etc/modules/mod_ahbot.conf"


def load_ahbot(cfg: dict, realm: str) -> tuple[str, list[AhbotField]]:
    path = ahbot_path(cfg, realm)
    content = SSHClient(cfg["server"]).read_file(path)
    fields = []
    for item in scan_content(path, content):
        if not item.key.startswith("AuctionHouseBot."):
            continue
        label, desc = describe(item.key, item.description)
        fields.append(AhbotField(
            key=item.key,
            value=item.value,
            default=item.default,
            label=label,
            description=desc,
            group=group_for(item.key),
            type=item.type,
            line=item.line,
        ))
    return path, fields


def grouped_fields(fields: list[AhbotField]) -> list[dict]:
    result = []
    for group_id, label in GROUPS:
        items = [field for field in fields if field.group == group_id]
        if items:
            result.append({"id": group_id, "label": label, "items": items})
    return result


def summarize(fields: list[AhbotField]) -> list[str]:
    values = {field.key: field.value for field in fields}
    enabled = []
    if values.get("AuctionHouseBot.EnableSeller") == "1":
        enabled.append("Verkäufer")
    if values.get("AuctionHouseBot.EnableBuyer") == "1":
        enabled.append("Käufer")
    if not enabled:
        enabled.append("deaktiviert")
    return [
        "Modus: " + ", ".join(enabled),
        f"Bot-Account: {values.get('AuctionHouseBot.Account', '0')} · GUID: {values.get('AuctionHouseBot.GUID', '0')}",
        f"Items pro Zyklus: {values.get('AuctionHouseBot.ItemsPerCycle', '?')}",
        f"Marktpreis: {'aktiv' if values.get('AuctionHouseBot.UseMarketPriceForSeller') == '1' else 'inaktiv'}",
        f"Nur Bot-Auktionen zählen: {'ja' if values.get('AuctionHouseBot.ConsiderOnlyBotAuctions') == '1' else 'nein'}",
    ]


def save_ahbot(cfg: dict, realm: str, values: dict[str, str]) -> tuple[str, list[tuple[str, str, str]]]:
    path, fields = load_ahbot(cfg, realm)
    allowed = {field.key: field.value for field in fields}
    ssh = SSHClient(cfg["server"])
    content = ssh.read_file(path)
    changes = []
    for key, old in allowed.items():
        if key not in values:
            continue
        new = str(values[key]).strip()
        if new == old:
            continue
        content = update_value(content, key, new)
        changes.append((key, old, new))
    if changes:
        backup = f"{path}.wowpanel.bak"
        ssh.run(f"cp {shell_quote(path)} {shell_quote(backup)}", timeout=10)
        ssh.write_file(path, content)
    return path, changes


def reset_ahbot(cfg: dict, realm: str) -> tuple[str, list[tuple[str, str, str]], str]:
    path, fields = load_ahbot(cfg, realm)
    ssh = SSHClient(cfg["server"])
    dist = f"{path}.dist"
    code, _, _ = ssh.run(f"test -f {shell_quote(dist)}", timeout=5)
    backup = f"{path}.wowpanel.bak"
    ssh.run(f"cp {shell_quote(path)} {shell_quote(backup)}", timeout=10)
    if code == 0:
        ssh.run(f"cp {shell_quote(dist)} {shell_quote(path)}", timeout=10)
        return path, [], f"{dist} wiederhergestellt. Backup: {backup}"
    content = ssh.read_file(path)
    changes = []
    for field in fields:
        if field.default is None or field.default == field.value:
            continue
        content = update_value(content, field.key, field.default)
        changes.append((field.key, field.value, field.default))
    if changes:
        ssh.write_file(path, content)
    return path, changes, f"Defaults aus Kommentaren wiederhergestellt. Backup: {backup}"


def group_for(key: str) -> str:
    if any(part in key for part in ["DEBUG", "TRACE"]):
        return "debug"
    if key in {"AuctionHouseBot.EnableSeller", "AuctionHouseBot.EnableBuyer", "AuctionHouseBot.ItemsPerCycle", "AuctionHouseBot.ElapsingTimeClass"}:
        return "basis"
    if key in {"AuctionHouseBot.Account", "AuctionHouseBot.GUID"}:
        return "bot"
    if any(part in key for part in ["Price", "Market", "Duplicates", "Divisible", "ConsiderOnly"]):
        return "markt"
    if key.startswith("AuctionHouseBot.Buyer") or "Buyer" in key:
        return "buyer"
    if key.startswith("AuctionHouseBot.Seller") or "Seller" in key:
        return "seller"
    if any(part in key for part in ["Quality", "ItemLevel", "ItemLvl", "Amount", "Min", "Max"]):
        return "quality"
    if any(part in key for part in ["Vendor", "Loot", "Other", "Profession", "Bind", "Disable", "No_Bind"]):
        return "filter"
    return "other"


def describe(key: str, original: str) -> tuple[str, str]:
    if key in META:
        return META[key]
    label = key.replace("AuctionHouseBot.", "").replace("_", " ")
    return label, translate_description(original) or "AHBot-Einstellung aus der Konfigurationsdatei. Prüfe Wert und Wirkung sorgfältig vor dem Neustart."


def translate_description(text: str) -> str:
    value = " ".join(line.strip() for line in (text or "").splitlines() if line.strip())
    replacements = [
        ("Enable/Disable", "Aktiviert/deaktiviert"),
        ("Debugging output", "Debug-Ausgaben"),
        ("Include", "Schließt ein:"),
        ("Disable", "Blockiert"),
        ("Default", "Standard"),
        ("Number of", "Anzahl"),
        ("auction", "Auktion"),
        ("auctions", "Auktionen"),
        ("items", "Items"),
        ("seller", "Verkäufer"),
        ("buyer", "Käufer"),
        ("player", "Spieler"),
        ("players", "Spieler"),
        ("market price", "Marktpreis"),
    ]
    for old, new in replacements:
        value = value.replace(old, new)
    return value
