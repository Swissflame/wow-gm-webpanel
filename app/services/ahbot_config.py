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
    "AuctionHouseBot.LootItems": ("Beute-Items zulassen", "Items einschließen, die durch Beute, Drops oder Sammeln erhältlich sind."),
    "AuctionHouseBot.LootTradeGoods": ("Beute-Handwerkswaren zulassen", "Handwerkswaren einschließen, die durch Beute, Drops oder Sammeln erhältlich sind."),
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
    "AuctionHouseBot.DisableWarriorItems": ("Krieger-Items blockieren", "Items, die speziell für Krieger gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisablePaladinItems": ("Paladin-Items blockieren", "Items, die speziell für Paladine gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableHunterItems": ("Jäger-Items blockieren", "Items, die speziell für Jäger gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableRogueItems": ("Schurken-Items blockieren", "Items, die speziell für Schurken gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisablePriestItems": ("Priester-Items blockieren", "Items, die speziell für Priester gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableDKItems": ("Todesritter-Items blockieren", "Items, die speziell für Todesritter gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableShamanItems": ("Schamanen-Items blockieren", "Items, die speziell für Schamanen gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableMageItems": ("Magier-Items blockieren", "Items, die speziell für Magier gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableWarlockItems": ("Hexenmeister-Items blockieren", "Items, die speziell für Hexenmeister gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableUnusedClassItems": ("Ungenutzte Klassenitems blockieren", "Items für die ungenutzte Klassen-ID 10 werden ausgeschlossen."),
    "AuctionHouseBot.DisableDruidItems": ("Druiden-Items blockieren", "Items, die speziell für Druiden gedacht sind, werden ausgeschlossen."),
    "AuctionHouseBot.DisableItemsBelowLevel": ("Items unter Itemlevel blockieren", "Verhindert Auktionen normaler Items unter diesem Itemlevel. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableItemsAboveLevel": ("Items über Itemlevel blockieren", "Verhindert Auktionen normaler Items über diesem Itemlevel. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsBelowLevel": ("Handwerkswaren unter Itemlevel blockieren", "Verhindert Auktionen von Trade-Goods unter diesem Itemlevel. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsAboveLevel": ("Handwerkswaren über Itemlevel blockieren", "Verhindert Auktionen von Trade-Goods über diesem Itemlevel. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableItemsBelowGUID": ("Items unter Entry-ID blockieren", "Verhindert Auktionen normaler Items mit Entry-ID unter diesem Wert. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableItemsAboveGUID": ("Items über Entry-ID blockieren", "Verhindert Auktionen normaler Items mit Entry-ID über diesem Wert. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsBelowGUID": ("Handwerkswaren unter Entry-ID blockieren", "Verhindert Auktionen von Trade-Goods mit Entry-ID unter diesem Wert. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsAboveGUID": ("Handwerkswaren über Entry-ID blockieren", "Verhindert Auktionen von Trade-Goods mit Entry-ID über diesem Wert. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableItemsBelowReqLevel": ("Items unter benötigtem Level blockieren", "Verhindert Auktionen normaler Items unter dieser benötigten Charakterstufe. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableItemsAboveReqLevel": ("Items über benötigtem Level blockieren", "Verhindert Auktionen normaler Items über dieser benötigten Charakterstufe. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsBelowReqLevel": ("Handwerkswaren unter benötigtem Level blockieren", "Verhindert Auktionen von Trade-Goods unter dieser benötigten Charakterstufe. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsAboveReqLevel": ("Handwerkswaren über benötigtem Level blockieren", "Verhindert Auktionen von Trade-Goods über dieser benötigten Charakterstufe. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableItemsBelowReqSkillRank": ("Items unter Skillrang blockieren", "Verhindert Auktionen normaler Items unter diesem benötigten Skillrang. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableItemsAboveReqSkillRank": ("Items über Skillrang blockieren", "Verhindert Auktionen normaler Items über diesem benötigten Skillrang. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsBelowReqSkillRank": ("Handwerkswaren unter Skillrang blockieren", "Verhindert Auktionen von Trade-Goods unter diesem benötigten Skillrang. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.DisableTGsAboveReqSkillRank": ("Handwerkswaren über Skillrang blockieren", "Verhindert Auktionen von Trade-Goods über diesem benötigten Skillrang. 0 schaltet diese Grenze aus."),
    "AuctionHouseBot.SellerWhiteList": ("Verkäufer-Whitelist", "Kommagetrennte Item-Entry-IDs, die der Verkäufer trotz sonstiger Filter anbieten darf. Leer bedeutet keine Whitelist."),
    "AuctionHouseBot.DEBUG": ("Debug aktivieren", "Schreibt allgemeine Debug-Ausgaben des AHBot."),
    "AuctionHouseBot.DEBUG_CONFIG": ("Config-Debug", "Schreibt Debug-Ausgaben beim Einlesen der Konfiguration."),
    "AuctionHouseBot.DEBUG_FILTERS": ("Filter-Debug", "Schreibt Debug-Ausgaben zu Itemfiltern."),
    "AuctionHouseBot.DEBUG_BUYER": ("Käufer-Debug", "Schreibt Debug-Ausgaben des Käufer-Moduls."),
    "AuctionHouseBot.DEBUG_SELLER": ("Verkäufer-Debug", "Schreibt Debug-Ausgaben des Verkäufer-Moduls."),
    "AuctionHouseBot.TRACE_SELLER": ("Verkäufe protokollieren", "Protokolliert durch den Bot verkaufte Items detaillierter."),
    "AuctionHouseBot.TRACE_BUYER": ("Käufe protokollieren", "Protokolliert durch den Bot gekaufte Items detaillierter."),
}


BOOLEAN_KEYS = {
    "AuctionHouseBot.DEBUG", "AuctionHouseBot.DEBUG_CONFIG", "AuctionHouseBot.DEBUG_FILTERS",
    "AuctionHouseBot.DEBUG_BUYER", "AuctionHouseBot.DEBUG_SELLER", "AuctionHouseBot.TRACE_SELLER",
    "AuctionHouseBot.TRACE_BUYER", "AuctionHouseBot.EnableSeller", "AuctionHouseBot.EnableBuyer",
    "AuctionHouseBot.UseBuyPriceForSeller", "AuctionHouseBot.UseBuyPriceForBuyer",
    "AuctionHouseBot.UseMarketPriceForSeller", "AuctionHouseBot.ConsiderOnlyBotAuctions",
    "AuctionHouseBot.DivisibleStacks", "AuctionHouseBot.VendorItems", "AuctionHouseBot.VendorTradeGoods",
    "AuctionHouseBot.LootItems", "AuctionHouseBot.LootTradeGoods", "AuctionHouseBot.OtherItems",
    "AuctionHouseBot.OtherTradeGoods", "AuctionHouseBot.ProfessionItems", "AuctionHouseBot.No_Bind",
    "AuctionHouseBot.Bind_When_Picked_Up", "AuctionHouseBot.Bind_When_Equipped",
    "AuctionHouseBot.Bind_When_Use", "AuctionHouseBot.Bind_Quest_Item",
    "AuctionHouseBot.DisablePermEnchant", "AuctionHouseBot.DisableConjured",
    "AuctionHouseBot.DisableGems", "AuctionHouseBot.DisableMoney", "AuctionHouseBot.DisableMoneyLoot",
    "AuctionHouseBot.DisableLootable", "AuctionHouseBot.DisableKeys", "AuctionHouseBot.DisableDuration",
    "AuctionHouseBot.DisableBOP_Or_Quest_NoReqLevel", "AuctionHouseBot.DisableWarriorItems",
    "AuctionHouseBot.DisablePaladinItems", "AuctionHouseBot.DisableHunterItems",
    "AuctionHouseBot.DisableRogueItems", "AuctionHouseBot.DisablePriestItems",
    "AuctionHouseBot.DisableDKItems", "AuctionHouseBot.DisableShamanItems",
    "AuctionHouseBot.DisableMageItems", "AuctionHouseBot.DisableWarlockItems",
    "AuctionHouseBot.DisableUnusedClassItems", "AuctionHouseBot.DisableDruidItems",
}

NUMBER_KEYS = {
    "AuctionHouseBot.MarketResetThreshold", "AuctionHouseBot.Account", "AuctionHouseBot.GUID",
    "AuctionHouseBot.ItemsPerCycle", "AuctionHouseBot.DuplicatesCount",
    "AuctionHouseBot.DisableItemsBelowLevel", "AuctionHouseBot.DisableItemsAboveLevel",
    "AuctionHouseBot.DisableTGsBelowLevel", "AuctionHouseBot.DisableTGsAboveLevel",
    "AuctionHouseBot.DisableItemsBelowGUID", "AuctionHouseBot.DisableItemsAboveGUID",
    "AuctionHouseBot.DisableTGsBelowGUID", "AuctionHouseBot.DisableTGsAboveGUID",
    "AuctionHouseBot.DisableItemsBelowReqLevel", "AuctionHouseBot.DisableItemsAboveReqLevel",
    "AuctionHouseBot.DisableTGsBelowReqLevel", "AuctionHouseBot.DisableTGsAboveReqLevel",
    "AuctionHouseBot.DisableItemsBelowReqSkillRank", "AuctionHouseBot.DisableItemsAboveReqSkillRank",
    "AuctionHouseBot.DisableTGsBelowReqSkillRank", "AuctionHouseBot.DisableTGsAboveReqSkillRank",
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
            type=field_type(item.key, item.type),
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


def schedule_realm_restart(cfg: dict, realm: str, delay: int) -> str:
    base = cfg["server"]["playerbot_path"] if realm == "playerbot" else cfg["server"]["normal_path"]
    workdir = f"{base}/bin"
    script = f"/tmp/wowpanel_restart_{realm}.sh"
    content = f"""#!/usr/bin/env bash
sleep {int(delay)}
for pid in $(pgrep -x worldserver || true); do
  if [ "$(readlink -f /proc/$pid/cwd 2>/dev/null)" = {shell_quote(workdir)} ]; then
    kill -TERM "$pid" || true
  fi
done
sleep 5
cd {shell_quote(workdir)}
nohup ./worldserver >/tmp/worldserver_{realm}.wowpanel.log 2>&1 &
"""
    marker = "WOWPANEL_RESTART"
    command = f"cat > {shell_quote(script)} <<'{marker}'\n{content}{marker}\nchmod +x {shell_quote(script)}\nnohup bash {shell_quote(script)} >/tmp/wowpanel_restart_{realm}.log 2>&1 &"
    code, out, err = SSHClient(cfg["server"]).run(command, timeout=10)
    if code != 0:
        raise RuntimeError(err or out or "Neustart konnte nicht geplant werden.")
    return f"SSH-Neustart für {realm} in {delay} Sekunden geplant."


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
    if any(part in key for part in ["Quality", "ItemLevel", "ItemLvl", "Amount", "Min", "Max", "Below", "Above", "ReqLevel", "ReqSkill"]):
        return "quality"
    if any(part in key for part in ["Vendor", "Loot", "Other", "Profession", "Bind", "Disable", "No_Bind"]):
        return "filter"
    return "other"


def describe(key: str, original: str) -> tuple[str, str]:
    if key in META:
        return META[key]
    label = key.replace("AuctionHouseBot.", "").replace("_", " ")
    return label, translate_description(original) or "AHBot-Einstellung aus der Konfigurationsdatei. Prüfe Wert und Wirkung sorgfältig vor dem Neustart."


def field_type(key: str, detected: str) -> str:
    if key == "AuctionHouseBot.ElapsingTimeClass":
        return "enum_duration"
    if key in BOOLEAN_KEYS:
        return "boolean"
    if key in NUMBER_KEYS:
        return "number"
    if key == "AuctionHouseBot.SellerWhiteList":
        return "text"
    return detected


def translate_description(text: str) -> str:
    value = " ".join(line.strip() for line in (text or "").splitlines() if line.strip())
    replacements = [
        ("Enable/Disable", "Aktiviert/deaktiviert"),
        ("Debugging output", "Debug-Ausgaben"),
        ("Include", "Erlaubt"),
        ("Disable", "Blockiert"),
        ("Default", "Standard"),
        ("Number of", "Anzahl"),
        ("auction", "Auktion"),
        ("auctions", "Auktionen"),
        ("fished for", "gesammelt werden"),
        ("looted", "erbeutet"),
        ("loot", "Beute"),
        ("Items", "Items"),
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
