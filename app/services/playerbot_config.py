from dataclasses import dataclass
import re

from .config_scanner import scan_content, update_value
from .ssh_service import SSHClient, shell_quote


@dataclass
class PlayerbotField:
    key: str
    value: str
    default: str | None
    label: str
    description: str
    group: str
    type: str
    line: int
    important: bool
    sensitive: bool


GROUPS = [
    ("uebersicht", "Grundbetrieb & Bot-Anzahl"),
    ("accounts", "Accounts, Login & Autologin"),
    ("gruppen", "Gruppen, Einladen & Beschwoeren"),
    ("ausruestung", "Ausrüstung, Loot & Wartung"),
    ("kampf", "Kampf, Reaktion & Distanzen"),
    ("quests", "Quests, Leveln & RPG-Verhalten"),
    ("random", "RandomBots: Level, Fraktionen & Aktivität"),
    ("pvp", "PvP, Schlachtfelder & Arena"),
    ("reise", "Reisen, Teleport & Zonen"),
    ("chat", "Chat, Antworten & Broadcasts"),
    ("premade", "Premade-Skillungen, Talente & Glyphen"),
    ("datenbank", "Playerbot-Datenbank & Updates"),
    ("debug", "Debug, Logs & Diagnose"),
    ("sonstige", "Weitere Spezialoptionen"),
]


IMPORTANT_KEYS = {
    "AiPlayerbot.Enabled", "AiPlayerbot.RandomBotAutologin", "AiPlayerbot.MinRandomBots",
    "AiPlayerbot.MaxRandomBots", "AiPlayerbot.RandomBotAccountCount", "AiPlayerbot.MaxAddedBots",
    "AiPlayerbot.DisabledWithoutRealPlayer", "AiPlayerbot.BotAutologin",
    "AiPlayerbot.AllowAccountBots", "AiPlayerbot.AllowGuildBots", "AiPlayerbot.IterationsPerTick",
    "AiPlayerbot.GlobalCooldown", "AiPlayerbot.ReactDelay", "AiPlayerbot.DynamicReactDelay",
    "AiPlayerbot.SightDistance", "AiPlayerbot.FollowDistance", "AiPlayerbot.AutoEquipUpgradeLoot",
    "AiPlayerbot.AutoDoQuests", "AiPlayerbot.RandomBotJoinLfg", "AiPlayerbot.RandomBotJoinBG",
    "AiPlayerbot.EnableBroadcasts", "AiPlayerbot.RandomBotLoginAtStartup",
}


BOOLEAN_HINTS = (
    "Enabled", "Enable", "Disabled", "Disable", "Allow", "Auto", "RandomBotAutologin",
    "Autologin", "Delete", "Invite", "Summon", "Revive", "Repair", "Show", "Equip",
    "LootRoll", "Sync", "Drop", "Apply", "Avoid", "Fleeing", "Maintenance", "Cheats",
    "Fishing", "Join", "Trading", "Prefer", "Persistence", "ActiveAlone", "Learn",
    "Pick", "Talk", "Emote", "Greet", "Broadcast", "PerfMon", "LogInGroupOnly",
)


FORCE_NUMBER_PREFIXES = (
    "AiPlayerbot.Min", "AiPlayerbot.Max", "AiPlayerbot.RandomBotMin", "AiPlayerbot.RandomBotMax",
    "AiPlayerbot.RandomBotCount", "AiPlayerbot.Periodic", "AiPlayerbot.Iterations",
    "AiPlayerbot.GlobalCooldown", "AiPlayerbot.ReactDelay", "AiPlayerbot.DynamicReactDelay",
    "AiPlayerbot.PassiveDelay", "AiPlayerbot.RepeatDelay", "AiPlayerbot.ErrorDelay",
    "AiPlayerbot.RpgDelay", "AiPlayerbot.SitDelay", "AiPlayerbot.ReturnDelay",
    "AiPlayerbot.LootDelay", "AiPlayerbot.FarDistance", "AiPlayerbot.SightDistance",
    "AiPlayerbot.SpellDistance", "AiPlayerbot.ShootDistance", "AiPlayerbot.HealDistance",
    "AiPlayerbot.LootDistance", "AiPlayerbot.FleeDistance", "AiPlayerbot.AggroDistance",
    "AiPlayerbot.TooCloseDistance", "AiPlayerbot.MeleeDistance", "AiPlayerbot.FollowDistance",
    "AiPlayerbot.WhisperDistance", "AiPlayerbot.ContactDistance", "AiPlayerbot.AoeRadius",
    "AiPlayerbot.RpgDistance", "AiPlayerbot.GrindDistance", "AiPlayerbot.ReactDistance",
    "AiPlayerbot.CriticalHealth", "AiPlayerbot.LowHealth", "AiPlayerbot.MediumHealth",
    "AiPlayerbot.AlmostFullHealth", "AiPlayerbot.LowMana", "AiPlayerbot.MediumMana",
    "AiPlayerbot.HighMana", "AiPlayerbot.RandomChangeMultiplier", "AiPlayerbot.CommandServerPort",
    "PlayerbotsDatabase.WorkerThreads", "PlayerbotsDatabase.SynchThreads",
)


META = {
    "AiPlayerbot.Enabled": ("Playerbot-System aktiv", "Hauptschalter für das Playerbot-Modul. Wenn deaktiviert, werden keine Playerbot-Funktionen geladen: keine zufälligen Bots, keine Accountbots und keine Bot-Kommandos. Änderung braucht einen Neustart des Playerbot-Realms."),
    "AiPlayerbot.RandomBotAutologin": ("RandomBots automatisch einloggen", "Wenn aktiv, loggt der Server zufällige Bots selbstständig ein. Spieler sehen dadurch eine belebtere Welt. Deaktiviert bleiben RandomBots offline, bis sie anderweitig gestartet werden."),
    "AiPlayerbot.MinRandomBots": ("Minimale RandomBots", "Untergrenze für die Anzahl zufälliger Bots im Spiel. Höher füllt die Welt stärker, erhöht aber CPU-, RAM- und Datenbanklast."),
    "AiPlayerbot.MaxRandomBots": ("Maximale RandomBots", "Obergrenze für zufällige Bots. Dieser Wert begrenzt, wie voll der Playerbot-Realm werden kann. Zu hoch kann den Worldserver deutlich belasten."),
    "AiPlayerbot.RandomBotAccountCount": ("RandomBot-Accounts", "Anzahl Accounts, die für RandomBots genutzt oder erzeugt werden. Mehr Accounts verteilen Bots sauberer, erzeugen aber mehr Accountdaten."),
    "AiPlayerbot.DeleteRandomBotAccounts": ("RandomBot-Accounts löschen", "Darf nur bewusst aktiviert werden: alte RandomBot-Accounts können entfernt werden. Nicht einschalten, wenn du Bot-Accounts behalten oder prüfen möchtest."),
    "AiPlayerbot.DisabledWithoutRealPlayer": ("Bots ohne echten Spieler abschalten", "Wenn aktiv, fahren Bots herunter, wenn kein echter Spieler online ist. Spart Leistung, lässt die Welt aber leer wirken, solange niemand spielt."),
    "AiPlayerbot.DisabledWithoutRealPlayerLoginDelay": ("Login-Verzögerung ohne echte Spieler", "Wartezeit, bevor Bots bei fehlenden echten Spielern reagieren. Höher verhindert ständiges Ein-/Ausloggen bei kurzen Verbindungswechseln."),
    "AiPlayerbot.DisabledWithoutRealPlayerLogoutDelay": ("Logout-Verzögerung ohne echte Spieler", "Wartezeit, bevor Bots ohne echte Spieler ausgeloggt werden. Höher hält die Welt länger belebt, kostet aber weiter Ressourcen."),
    "AiPlayerbot.MaxAddedBots": ("Maximal hinzufügbare Bots", "Begrenzt, wie viele Bots ein Spieler zusätzlich in Gruppe oder Umgebung holen kann. Niedriger verhindert Bot-Überfüllung, höher erlaubt größere Solo-Gruppen."),
    "AiPlayerbot.BotAutologin": ("Accountbots automatisch einloggen", "Erlaubt Bots, die an Accounts gebunden sind, automatisch einzuloggen. Praktisch für feste Begleiter, kann aber Startlast erhöhen."),
    "AiPlayerbot.AllowAccountBots": ("Accountbots erlauben", "Spieler dürfen Bots aus ihrem Account nutzen. Deaktiviert verhindert private Account-Begleiter."),
    "AiPlayerbot.AllowGuildBots": ("Gildenbots erlauben", "Erlaubt Bots aus der Gilde. Gut für kleine Gruppenserver, weil Gildenmitglieder gemeinsame Bots nutzen können."),
    "AiPlayerbot.AllowTrustedAccountBots": ("Vertrauens-Accountbots erlauben", "Erlaubt Bots von vertrauten Accounts. Komfortabel, aber nur sinnvoll, wenn Vertrauen und Rechte sauber geregelt sind."),
    "AiPlayerbot.GroupInvitationPermission": ("Gruppeneinladungs-Recht", "Legt fest, wer Bots in Gruppen einladen darf. Strenger reduziert Missbrauch; lockerer macht Botgruppen bequemer."),
    "AiPlayerbot.KeepAltsInGroup": ("Twinks in Gruppe behalten", "Bots oder Twinks bleiben beim Wechseln/Steuern eher in der Gruppe. Praktisch für feste Botgruppen."),
    "AiPlayerbot.SummonWhenGroup": ("Bots in Gruppe beschwören", "Bots können zum Spieler geholt werden, wenn sie in der Gruppe sind. Komfortabel, aber weniger reiserealistisch."),
    "AiPlayerbot.AllowSummonInCombat": ("Beschwören im Kampf erlauben", "Erlaubt Bot-Beschwörung während Kampf. Sehr bequem, kann aber Kämpfe und Bossmechaniken stark vereinfachen."),
    "AiPlayerbot.AllowSummonWhenMasterIsDead": ("Beschwören wenn Meister tot ist", "Erlaubt Summon, obwohl der führende Spieler tot ist. Kann Supportfälle lösen, ist aber weniger blizzlike."),
    "AiPlayerbot.AllowSummonWhenBotIsDead": ("Tote Bots beschwören", "Erlaubt, tote Bots zum Spieler zu holen. Zusammen mit Wiederbelebung kann das Botgruppen stark vereinfachen."),
    "AiPlayerbot.ReviveBotWhenSummoned": ("Bots beim Beschwören wiederbeleben", "Wenn aktiv, werden tote Bots beim Summon wiederbelebt. Sehr komfortabel, nimmt aber Todesfolgen aus dem Botspiel."),
    "AiPlayerbot.BotRepairWhenSummon": ("Bots reparieren beim Beschwören", "Bots reparieren beim Herbeirufen ihre Ausrüstung. Reduziert Wartung, kann aber Reparaturwege und Kosten aushebeln."),
    "AiPlayerbot.AutoEquipUpgradeLoot": ("Loot-Upgrades automatisch anlegen", "Bots legen bessere Beute automatisch an. Aktiviert macht Bots stärker und wartungsärmer; deaktiviert behalten sie Ausrüstung länger."),
    "AiPlayerbot.EquipUpgradeThreshold": ("Schwelle für Ausrüstungs-Upgrades", "Mindestverbesserung, ab der Bots ein Item als Upgrade anlegen. Niedriger wechselt häufiger, höher nur bei klaren Verbesserungen."),
    "AiPlayerbot.FreeMethodLoot": ("Freie Lootmethode", "Steuert, wie locker Bots Beute annehmen oder verteilen. Falsch gesetzte Werte können Lootverhalten in Gruppen überraschend verändern."),
    "AiPlayerbot.LootNeedRollLevel": ("Bedarf-Wurf ab Qualitätsstufe", "Ab welcher Itemqualität Bots Bedarf würfeln dürfen. Niedriger macht Bots gieriger auf Items, höher zurückhaltender."),
    "AiPlayerbot.LootGreedRollLevel": ("Gier-Wurf ab Qualitätsstufe", "Ab welcher Itemqualität Bots Gier würfeln. Beeinflusst, wie viel Beute Bots in Gruppen aufnehmen."),
    "AiPlayerbot.IterationsPerTick": ("KI-Schritte pro Tick", "Wie viele Bot-KI-Schritte pro Server-Tick verarbeitet werden. Höher macht Bots reaktionsfreudiger, kann aber CPU-Last stark erhöhen."),
    "AiPlayerbot.GlobalCooldown": ("Bot-Global-Cooldown", "Grundpause zwischen Botaktionen. Niedriger macht Bots schneller und stärker, höher ruhiger und weniger belastend."),
    "AiPlayerbot.ReactDelay": ("Reaktionsverzögerung", "Zeit, bis Bots auf Ereignisse reagieren. Niedriger wirkt menschlich schneller, erhöht aber Last und Botstärke."),
    "AiPlayerbot.DynamicReactDelay": ("Dynamische Reaktionsverzögerung", "Passt Reaktion je nach Situation an. Aktiviert kann Bots natürlicher und weniger gleichförmig machen."),
    "AiPlayerbot.SightDistance": ("Sichtdistanz", "Distanz, in der Bots Ziele, Spieler und Ereignisse beachten. Höher wirkt intelligenter, kostet aber mehr Such- und KI-Arbeit."),
    "AiPlayerbot.FollowDistance": ("Folgedistanz", "Abstand, den Bots beim Folgen halten. Niedriger klebt dichter am Spieler, höher wirkt natürlicher, kann aber in engen Wegen stören."),
    "AiPlayerbot.CriticalHealth": ("Kritische Gesundheit", "Prozentwert, ab dem Bots Gesundheit als kritisch bewerten. Höher lässt sie früher defensiv reagieren oder heilen."),
    "AiPlayerbot.LowMana": ("Niedriges Mana", "Prozentwert, ab dem Bots Mana sparen oder trinken möchten. Höher macht Caster vorsichtiger, niedriger aggressiver."),
    "AiPlayerbot.AutoPickReward": ("Questbelohnung automatisch wählen", "Bots wählen Questbelohnungen selbst. Praktisch bei vielen Bots, kann aber nicht immer die perfekte Belohnung treffen."),
    "AiPlayerbot.SyncQuestWithPlayer": ("Bot-Quests mit Spieler synchronisieren", "Bots versuchen, Quests an den Spieler anzugleichen. Gut für gemeinsames Leveln, kann aber zusätzliche Questlogik erzeugen."),
    "AiPlayerbot.SyncQuestForPlayer": ("Spielerquests für Bots übernehmen", "Bots nehmen passende Spielerquests auf. Macht Gruppenquesten flüssiger, verändert aber Bot-Questfortschritt automatisch."),
    "AiPlayerbot.DropObsoleteQuests": ("Veraltete Quests aufgeben", "Bots geben alte oder nicht mehr passende Quests auf. Hält Questlogs sauber, kann aber bewusst behaltene Quests entfernen."),
    "AiPlayerbot.AutoDoQuests": ("Bots erledigen Quests automatisch", "RandomBots erledigen selbstständig Quests. Belebt die Welt und levelt Bots, erhöht aber KI- und Datenbankaktivität."),
    "AiPlayerbot.RandomBotJoinLfg": ("RandomBots im Dungeonfinder", "RandomBots dürfen sich für Dungeonfinder anmelden. Belebt Instanzen, kann aber Gruppen mit Bots füllen."),
    "AiPlayerbot.RandomBotJoinBG": ("RandomBots im PvP", "RandomBots dürfen Schlachtfelder nutzen. Belebt PvP, kann aber Balance und Warteschlangen stark verändern."),
    "AiPlayerbot.RandomBotAutoJoinBG": ("RandomBots automatisch ins Schlachtfeld", "Bots melden sich selbstständig für Battlegrounds an. Aktiviert macht PvP lebendiger, kostet aber zusätzliche KI-Last."),
    "AiPlayerbot.RandomBotLoginAtStartup": ("RandomBots beim Serverstart einloggen", "Bots werden direkt beim Start hochgefahren. Welt ist sofort belebter, der Start dauert aber länger und Lastspitzen steigen."),
    "AiPlayerbot.EnableBroadcasts": ("Bot-Broadcasts aktiv", "Bots schreiben automatische Meldungen in Kanäle. Das wirkt lebendig, kann aber schnell wie Spam aussehen."),
    "AiPlayerbot.CommandPrefix": ("Bot-Befehlspräfix", "Zeichenfolge, mit der Bot-Kommandos beginnen. Spieler nutzen sie im Chat, um Bots zu steuern."),
    "AiPlayerbot.CommandSeparator": ("Bot-Befehlstrenner", "Trenner für mehrere Bot-Kommandos. Nur ändern, wenn du das Chat-Befehlssystem bewusst anders bedienen willst."),
    "PlayerbotsDatabaseInfo": ("Playerbot-Datenbankverbindung", "Verbindungsdaten für die Playerbot-Datenbank. Falsch gesetzt verhindert Start oder Playerbot-Datenzugriff."),
    "PlayerbotsDatabase.WorkerThreads": ("Playerbot-Datenbank-Threads", "Parallele Arbeits-Threads für die Playerbot-Datenbank. Höher kann mehr Last verarbeiten, belastet aber DB und CPU."),
    "PlayerbotsDatabase.SynchThreads": ("Synchrone Playerbot-DB-Threads", "Threads für synchrone Datenbankarbeit. Zu niedrig kann blockieren, zu hoch unnötige Last erzeugen."),
    "Playerbots.Updates.EnableDatabases": ("Playerbot-DB-Updates aktiv", "Steuert automatische SQL-Updates für Playerbot-Datenbanken. Falsch gesetzt können notwendige Updates fehlen."),
}


def playerbot_path(cfg: dict) -> str:
    return f"{cfg['server']['playerbot_path']}/etc/modules/playerbots.conf"


def load_playerbot(cfg: dict) -> tuple[str, list[PlayerbotField]]:
    path = playerbot_path(cfg)
    content = SSHClient(cfg["server"]).read_file(path)
    fields: list[PlayerbotField] = []
    for item in scan_content(path, content):
        if not (item.key.startswith("AiPlayerbot.") or item.key.startswith("AIPlayerbot.") or item.key.startswith("Playerbots")):
            continue
        label, desc = describe(item.key, item.description)
        fields.append(PlayerbotField(
            key=item.key,
            value=item.value,
            default=item.default,
            label=label,
            description=desc,
            group=group_for(item.key),
            type=field_type(item.key, item.type),
            line=item.line,
            important=item.key in IMPORTANT_KEYS,
            sensitive=item.sensitive or item.key == "PlayerbotsDatabaseInfo",
        ))
    return path, fields


def grouped_fields(fields: list[PlayerbotField]) -> list[dict]:
    result = []
    for group_id, label in GROUPS:
        items = [field for field in fields if field.group == group_id]
        if items:
            important = [field for field in items if field.important]
            advanced = [field for field in items if not field.important]
            result.append({"id": group_id, "label": label, "important": important, "advanced": advanced, "count": len(items)})
    return result


def summarize(fields: list[PlayerbotField]) -> list[str]:
    values = {field.key: field.value for field in fields}
    return [
        f"Playerbots: {'aktiv' if values.get('AiPlayerbot.Enabled') == '1' else 'inaktiv'}",
        f"RandomBots: {'Autologin aktiv' if values.get('AiPlayerbot.RandomBotAutologin') == '1' else 'Autologin aus'} · {values.get('AiPlayerbot.MinRandomBots', '?')} bis {values.get('AiPlayerbot.MaxRandomBots', '?')}",
        f"Bot-Accounts: {values.get('AiPlayerbot.RandomBotAccountCount', '?')} · Max. hinzugefuegte Bots: {values.get('AiPlayerbot.MaxAddedBots', '?')}",
        f"KI: {values.get('AiPlayerbot.IterationsPerTick', '?')} Schritte/Tick · Reaktion {values.get('AiPlayerbot.ReactDelay', '?')} ms",
        f"Quests/PvP: Auto-Quests {'ja' if values.get('AiPlayerbot.AutoDoQuests') == '1' else 'nein'} · LFG {'ja' if values.get('AiPlayerbot.RandomBotJoinLfg') == '1' else 'nein'} · BG {'ja' if values.get('AiPlayerbot.RandomBotJoinBG') == '1' else 'nein'}",
    ]


def save_playerbot(cfg: dict, values: dict[str, str]) -> tuple[str, list[tuple[str, str, str]]]:
    path, fields = load_playerbot(cfg)
    allowed = {field.key: field.value for field in fields}
    ssh = SSHClient(cfg["server"])
    content = ssh.read_file(path)
    changes = []
    for key, old in allowed.items():
        if key not in values:
            continue
        new = str(values[key]).strip()
        if key == "PlayerbotsDatabaseInfo" and new == "********":
            continue
        if new == old:
            continue
        content = update_value(content, key, new)
        changes.append((key, old, new))
    if changes:
        backup = f"{path}.wowpanel.bak"
        ssh.run(f"cp {shell_quote(path)} {shell_quote(backup)}", timeout=10)
        code, out, err = ssh.write_file(path, content)
        if code != 0:
            raise RuntimeError(err or out or f"Config konnte nicht geschrieben werden: {path}")
    return path, changes


def reset_playerbot(cfg: dict) -> tuple[str, list[tuple[str, str, str]], str]:
    path, fields = load_playerbot(cfg)
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
        code, out, err = ssh.write_file(path, content)
        if code != 0:
            raise RuntimeError(err or out or f"Config konnte nicht geschrieben werden: {path}")
    return path, changes, f"Defaults aus Kommentaren wiederhergestellt. Backup: {backup}"


def group_for(key: str) -> str:
    if key.startswith("Playerbots"):
        return "datenbank"
    if any(part in key for part in ["Log", "Debug", "PerfMon", "SpellDump", "AllowedLogFiles"]):
        return "debug"
    if key.startswith(("AiPlayerbot.Premade", "AiPlayerbot.RandomClassSpec", "AiPlayerbot.WorldBuffMatrix")):
        return "premade"
    if key.startswith("AiPlayerbot.ZoneBracket") or "Tele" in key or "Taxi" in key or key.endswith("Maps"):
        return "reise"
    if any(part in key for part in ["BG", "Arena", "Pvp", "PvP", "MMR"]):
        return "pvp"
    if any(part in key for part in ["Broadcast", "Chat", "Replies", "Reply", "Talk", "Emote", "Greet", "Toxic", "Thunderfury", "GuildFeedback", "Say"]):
        return "chat"
    if any(part in key for part in ["Quest", "Rpg", "Grind", "Travel", "Rest", "Wander", "Camp", "Outdoor"]):
        return "quests"
    if any(part in key for part in ["Gear", "Equip", "Loot", "Maintenance", "Repair", "Ammo", "Food", "Reagents", "Consumables", "Potions", "Bags", "Mounts", "Glyphs", "Gems", "Enchant", "Pet", "Attunement"]):
        return "ausruestung"
    if any(part in key for part in ["Distance", "Delay", "Cooldown", "React", "Health", "Mana", "Aoe", "Combat", "Strategy", "Strategies", "Flee", "Aggro", "Melee", "Spell", "Shoot", "Heal", "Move", "Tick"]):
        return "kampf"
    if any(part in key for part in ["Account", "Login", "Password", "Prefix", "CommandServerPort"]):
        return "accounts"
    if any(part in key for part in ["Group", "Invite", "Summon", "Guild", "Trusted"]):
        return "gruppen"
    if "RandomBot" in key or "Randombot" in key or "RandomBots" in key or "Periodic" in key:
        return "random"
    if key in {"AiPlayerbot.Enabled", "AiPlayerbot.MaxAddedBots", "AiPlayerbot.AddClassCommand", "AiPlayerbot.AutoInitOnly"}:
        return "uebersicht"
    return "sonstige"


def describe(key: str, original: str) -> tuple[str, str]:
    if key in META:
        return META[key]
    label = human_label(key)
    prefix = description_by_pattern(key, label)
    if prefix:
        return label, prefix
    return label, group_description(key, label)


def human_label(key: str) -> str:
    raw = key.replace("AIPlayerbot.", "").replace("AiPlayerbot.", "").replace("Playerbots.", "Playerbot-")
    if raw.startswith("RpgStatusProbWeight."):
        return "RPG-Gewichtung: " + translate_words(raw.split(".", 1)[1])
    if raw.startswith("ZoneBracket."):
        return "Zonen-Levelbereich: Zone " + raw.split(".", 1)[1]
    if raw.startswith("TeleTo") and raw.endswith("Weight"):
        city = raw[len("TeleTo"):-len("Weight")]
        return "Teleport-Gewichtung: " + translate_words(city)
    if raw.startswith("BroadcastChance"):
        return "Broadcast-Chance: " + translate_words(raw[len("BroadcastChance"):])
    if raw.startswith("PremadeSpecName."):
        return "Premade-Name: " + class_spec_suffix(raw)
    if raw.startswith("PremadeSpecGlyph."):
        return "Premade-Glyphen: " + class_spec_suffix(raw)
    if raw.startswith("PremadeSpecLink."):
        return "Premade-Talentlink: " + class_spec_suffix(raw)
    if raw.startswith("PremadeHunterPetLink."):
        return "Premade-Jägerbegleiter: " + class_spec_suffix(raw)
    if raw.startswith("RandomClassSpecProb."):
        return "Klassen-/Skillungs-Chance: " + class_spec_suffix(raw)
    if raw.startswith("RandomClassSpecIndex."):
        return "Klassen-/Skillungs-Index: " + class_spec_suffix(raw)
    return translate_words(raw)


def class_spec_suffix(raw: str) -> str:
    nums = ".".join(raw.split(".")[1:])
    return nums.replace(".", " / ")


def translate_words(value: str) -> str:
    words = {
        "Enabled": "aktiv", "Enable": "aktiv", "Disabled": "deaktiviert", "Disable": "deaktivieren",
        "Random": "zufaellig", "Bot": "Bot", "Bots": "Bots", "Account": "Account", "Accounts": "Accounts",
        "Autologin": "Autologin", "Login": "Login", "Logout": "Logout", "Delay": "Verzoegerung",
        "Min": "Minimum", "Max": "Maximum", "Count": "Anzahl", "Added": "hinzugefuegt",
        "Class": "Klasse", "Command": "Befehl", "Pool": "Pool", "Size": "Groesse",
        "Group": "Gruppe", "Invitation": "Einladung", "Permission": "Recht", "Keep": "behalten",
        "Alts": "Twinks", "Guild": "Gilde", "Trusted": "vertraut", "Invite": "einladen",
        "Chat": "Chat", "Summon": "beschwoeren", "When": "wenn", "Master": "Meister",
        "Dead": "tot", "Revive": "wiederbeleben", "Repair": "reparieren", "Ground": "Boden",
        "Mount": "Reittier", "Fast": "schnell", "Fly": "Flug", "Level": "Level",
        "Show": "anzeigen", "Helmet": "Helm", "Cloak": "Umhang", "Auto": "automatisch",
        "Equip": "ausruesten", "Upgrade": "Upgrade", "Loot": "Beute", "Threshold": "Schwelle",
        "Gear": "Ausrüstung", "Init": "Initialisierung", "Free": "frei", "Method": "Methode",
        "Need": "Bedarf", "Greed": "Gier", "Roll": "Wurf", "Recipe": "Rezept",
        "Disenchant": "Entzaubern", "Iterations": "Schritte", "Per": "pro", "Tick": "Tick",
        "Global": "global", "Cooldown": "Abklingzeit", "Wait": "Wartezeit", "Move": "Bewegung",
        "Movement": "Bewegung", "Search": "Suche", "Time": "Zeit", "Expire": "Ablauf",
        "Action": "Aktion", "Dispel": "Reinigung", "Aura": "Aura", "Duration": "Dauer",
        "React": "Reaktion", "Dynamic": "dynamisch", "Passive": "passiv", "Repeat": "Wiederholung",
        "Error": "Fehler", "Rpg": "RPG", "Sit": "Sitzen", "Return": "Rueckkehr",
        "Far": "weit", "Distance": "Distanz", "Sight": "Sicht", "Spell": "Zauber",
        "Shoot": "Schuss", "Heal": "Heilung", "Flee": "Flucht", "Aggro": "Aggro",
        "Too": "zu", "Close": "nah", "Melee": "Nahkampf", "Follow": "Folgen",
        "Whisper": "Fluestern", "Contact": "Kontakt", "Aoe": "Flaecheneffekt",
        "Radius": "Radius", "Grind": "Farmen", "Critical": "kritisch", "Health": "Gesundheit",
        "Low": "niedrig", "Medium": "mittel", "Almost": "fast", "Full": "voll",
        "Mana": "Mana", "High": "hoch", "Pick": "waehlen", "Reward": "Belohnung",
        "Sync": "synchronisieren", "Quest": "Quest", "Quests": "Quests", "Player": "Spieler",
        "Obsolete": "veraltet", "Apply": "anwenden", "Instance": "Instanz",
        "Strategies": "Strategien", "Strategy": "Strategie", "Avoid": "vermeiden",
        "Save": "sparen", "Fleeing": "Flucht", "Greater": "groesser", "Buff": "Buff",
        "Warning": "Warnung", "Maintenance": "Wartung", "Ammo": "Munition", "Food": "Essen",
        "Reagents": "Reagenzien", "Consumables": "Verbrauchsgueter", "Potions": "Traenke",
        "Bags": "Taschen", "Mounts": "Reittiere", "Skills": "Skills", "Spells": "Zauber",
        "Available": "verfuegbar", "Special": "spezial", "Talent": "Talent", "Tree": "Baum",
        "Glyphs": "Glyphen", "Gems": "Edelsteine", "Enchants": "Verzauberungen",
        "Pet": "Begleiter", "Talents": "Talente", "Reputation": "Ruf", "Attunement": "Zugang",
        "Keyring": "Schluesselbund", "Quality": "Qualitaet", "Score": "Wertung",
        "Limit": "Limit", "Cheats": "Cheats", "Taxi": "Flugtaxi", "Gap": "Abstand",
        "Jitter": "Streuung", "Profession": "Beruf", "Chance": "Chance", "Fishing": "Angeln",
        "Password": "Passwort", "Prefix": "Praefix", "Horde": "Horde", "Alliance": "Allianz",
        "Ratio": "Verhaeltnis", "Death": "Tod", "Knight": "Ritter", "Fixed": "fest",
        "XPRate": "XP-Multiplikator", "Armor": "Ruestung", "Type": "Typ", "Weapons": "Waffen",
        "Incremental": "schrittweise", "Enchanting": "Verzauberkunst", "Expansion": "Erweiterung",
        "Lowering": "Absenkung", "Unobtainable": "nicht erhaeltlich", "Items": "Items",
        "Check": "Pruefung", "Persistence": "Speicherung", "Hunter": "Jaeger", "Wolf": "Wolf",
        "Default": "Standard", "Stance": "Haltung", "Families": "Familien", "Active": "aktiv",
        "Alone": "allein", "Force": "erzwingen", "Zone": "Zone", "Map": "Karte",
        "Friend": "Freund", "Smart": "intelligent", "Scale": "Skalierung", "Diff": "Differenz",
        "Floor": "untere Grenze", "Ceiling": "obere Grenze", "Ids": "IDs", "Do": "erledigen",
        "Open": "oeffnen", "Go": "gehen", "Wander": "wandern", "Npc": "NPC", "Camp": "Camp",
        "Travel": "reisen", "Flight": "Flug", "Outdoor": "Outdoor", "Pvp": "PvP",
        "Prob": "Wahrscheinlichkeit", "Weight": "Gewichtung", "Bankers": "Bankiers",
        "City": "Stadt", "Stormwind": "Sturmwind", "Ironforge": "Eisenschmiede",
        "Darnassus": "Darnassus", "Exodar": "Exodar", "Orgrimmar": "Orgrimmar",
        "Undercity": "Unterstadt", "Thunder": "Donner", "Bluff": "fels", "Silvermoon": "Silbermond",
        "Shattrath": "Shattrath", "Dalaran": "Dalaran", "Higher": "hoeher",
        "Bracket": "Levelbereich", "Rated": "gewertet", "Team": "Team", "Rating": "Wertung",
        "Delete": "loeschen", "Update": "Update", "Interval": "Intervall", "World": "Welt",
        "Randomize": "neu wuerfeln", "ReviveTime": "Wiederbelebungszeit", "Permanently": "dauerhaft",
        "Name": "Name", "Glyph": "Glyphe", "Link": "Link", "Matrix": "Matrix",
        "Index": "Index", "Database": "Datenbank", "WorkerThreads": "Arbeits-Threads",
        "SynchThreads": "Synchrone Threads", "Updates": "Updates", "Databases": "Datenbanken",
        "Server": "Server", "Port": "Port", "Values": "Werte", "Separator": "Trenner",
        "Trade": "Handel", "Mention": "Erwaehnung", "Suggest": "vorschlagen",
        "Dungeons": "Dungeons", "Greet": "gruessen", "Replies": "Antworten", "Rate": "Rate",
        "Broadcasts": "Broadcasts", "To": "an", "Local": "lokal", "Defense": "Verteidigung",
        "Recruitment": "Rekrutierung", "Accepted": "angenommen", "Objective": "Ziel",
        "Completed": "abgeschlossen", "Progress": "Fortschritt", "Failed": "fehlgeschlagen",
        "Timer": "Timer", "Complete": "fertig", "Turned": "abgegeben", "Kill": "Kill",
        "Normal": "normal", "Elite": "Elite", "Rareelite": "seltene Elite", "Worldboss": "Weltboss",
        "Unknown": "unbekannt", "Levelup": "Levelaufstieg", "Generic": "allgemein",
        "Sell": "verkaufen", "Something": "etwas", "Toxic": "toxisch", "Links": "Links",
        "Thunderfury": "Donnerzorn", "Management": "Verwaltung", "Files": "Dateien",
        "Disallowed": "verboten", "GameObjects": "Spielobjekte", "Startup": "Serverstart",
        "Tasks": "Aufgaben", "Lower": "kleiner", "Case": "Schreibung", "Randomly": "zufaellig",
        "Walking": "laufend", "InDoors": "innen", "Price": "Preis", "Change": "Aenderung",
        "Advertisement": "Anzeige", "Cleanup": "Aufraeumen", "Target": "Ziel", "Pos": "Position",
        "Recalc": "neu berechnen", "Innkeepers": "Gastwirte", "ICCBuffs": "ICC-Buffs",
    }
    parts = []
    for part in re.split(r"[._-]+", value):
        if not part:
            continue
        split = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", part)
        split = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", split)
        split = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", split)
        for piece in split.split():
            parts.append(words.get(piece, piece))
    return " ".join(parts)


def description_by_pattern(key: str, label: str) -> str:
    if key.startswith("AiPlayerbot.RpgStatusProbWeight."):
        return "Gewichtung für ein RPG-Verhalten zufälliger Bots. Höher bedeutet: Bots wählen diese Aktivität öfter. Niedriger macht das Verhalten seltener. Die Summe aller Gewichte bestimmt die Verteilung, nicht ein einzelner Wert allein."
    if key.startswith("AiPlayerbot.ZoneBracket."):
        return "Levelbereich für eine Zone. RandomBots nutzen diese Zuordnung, um passende Gebiete für Leveln, Reisen und RPG-Aktivitäten zu wählen. Falsche Bereiche schicken Bots in zu leichte oder zu schwere Zonen."
    if key.startswith("AiPlayerbot.PremadeSpec"):
        return "Premade-Skillung für Bots. Diese Werte bestimmen Namen, Glyphen oder Talentlinks je Klasse/Spezialisierung und Level. Änderungen wirken sich auf neu initialisierte oder neu ausgerüstete Bots aus."
    if key.startswith("AiPlayerbot.PremadeHunterPet"):
        return "Premade-Jägerbegleiter für Bot-Skillungen. Bestimmt, welche Begleiter-Konfiguration für bestimmte Jägerprofile genutzt wird."
    if key.startswith("AiPlayerbot.RandomClassSpec"):
        return "Wahrscheinlichkeit oder Index für zufällige Klassen-/Skillungsverteilung. Höhere Chancen erzeugen mehr Bots dieser Skillung; falsche Werte können die Rollenverteilung unausgewogen machen."
    if key.startswith("AiPlayerbot.BroadcastChance"):
        return "Wahrscheinlichkeit für automatische Bot-Nachrichten zu diesem Ereignis. Höher macht Bots gesprächiger und die Welt lebendiger; zu hoch wirkt schnell wie Spam."
    if "Distance" in key or "Radius" in key:
        return "Distanzwert für Bot-KI. Höhere Werte lassen Bots weiter sehen, folgen oder reagieren, erhöhen aber Sucharbeit und können Verhalten weiträumiger machen."
    if "Delay" in key or "Cooldown" in key or "Interval" in key or "Time" in key:
        return "Zeitwert für Bot-Verhalten. Niedriger reagiert schneller und wirkt aktiver, kann aber Last und Botstärke erhöhen. Höher macht Bots ruhiger und ressourcenschonender."
    if "Health" in key or "Mana" in key:
        return "Schwellwert für Ressourcenbewertung. Bots entscheiden damit, wann sie heilen, Mana sparen, trinken oder defensiver spielen. Höher reagiert vorsichtiger, niedriger aggressiver."
    if "Gear" in key or "Equip" in key or "Loot" in key:
        return "Ausrüstungs- oder Lootregel. Sie beeinflusst, welche Items Bots nehmen, anlegen oder behalten. Änderungen machen Bots stärker, schwächer oder wartungsärmer."
    if "Quest" in key:
        return "Questregel für Bots. Sie beeinflusst, ob Bots Quests annehmen, synchronisieren, erledigen oder aufgeben. Spieler merken das beim gemeinsamen Leveln und in der offenen Welt."
    if "RandomBot" in key or "Randombot" in key:
        return "RandomBot-Regel. Sie steuert Anzahl, Level, Login, Verhalten oder Verteilung zufälliger Bots. Höhere Aktivität belebt die Welt, kostet aber Serverleistung."
    return ""


def group_description(key: str, label: str) -> str:
    group = group_for(key)
    descriptions = {
        "uebersicht": f"Grundlegende Playerbot-Einstellung für {label}. Sie beeinflusst, ob und wie Bots im Realm verfügbar sind. Änderungen brauchen meist einen Neustart des Playerbot-Realms.",
        "accounts": f"Account- und Login-Einstellung für {label}. Sie beeinflusst Bot-Accounts, Autologin, Passwörter oder Befehlszugriff. Falsche Werte können Bots am Einloggen hindern.",
        "gruppen": f"Gruppen- und Beschwörungsregel für {label}. Spieler merken sie beim Einladen, Folgen, Beschwören und gemeinsamen Spielen mit Bots.",
        "ausruestung": f"Ausrüstungs-, Loot- oder Wartungsregel für {label}. Sie bestimmt, wie selbstständig Bots Items, Reparatur, Munition, Zauber, Talente oder Begleiter pflegen.",
        "kampf": f"Kampf- und KI-Regel für {label}. Sie beeinflusst Reaktion, Distanzen, AOE-Vermeidung, Heilen, Flucht und allgemeine Botstärke.",
        "quests": f"Quest- und RPG-Regel für {label}. Sie steuert, ob Bots selbstständig leveln, reisen, grinden, Quests erledigen oder rollenspielartig durch die Welt laufen.",
        "random": f"RandomBot-Einstellung für {label}. Sie verändert die simulierte Weltbevölkerung. Mehr Aktivität wirkt lebendiger, braucht aber mehr Leistung.",
        "pvp": f"PvP-Regel für {label}. Sie beeinflusst Bot-Verhalten in Schlachtfeldern, Arena, Warteschlangen und PvP-Zonen.",
        "reise": f"Reise- und Zonenregel für {label}. Bots nutzen sie für Teleports, Flugrouten, Levelzonen und Positionswechsel.",
        "chat": f"Chat- und Broadcastregel für {label}. Sie macht Bots gesprächiger oder ruhiger. Zu hohe Chancen können Spielerchat überfüllen.",
        "premade": f"Premade-Konfiguration für {label}. Diese Werte bestimmen Skillungen, Glyphen, Talentlinks oder Rollenprofile von Bots.",
        "datenbank": f"Datenbank-Einstellung für {label}. Sie beeinflusst Playerbot-Datenbankzugriff und Updates. Falsche Werte können den Playerbot-Start verhindern.",
        "debug": f"Debug- und Diagnoseoption für {label}. Aktiviert hilft bei Fehlersuche, kann aber Logs stark vergrößern oder Leistung kosten.",
    }
    return descriptions.get(group, f"Playerbot-Spezialoption für {label}. Wert mit Backup ändern und nach dem Speichern den Playerbot-Realm neu starten.")


def field_type(key: str, detected: str) -> str:
    if key in {"PlayerbotsDatabaseInfo"}:
        return "password"
    if any(key.startswith(prefix) for prefix in FORCE_NUMBER_PREFIXES):
        return "number"
    if detected == "boolean" or any(hint in key for hint in BOOLEAN_HINTS):
        if is_probably_boolean_value(key):
            return "boolean"
    if detected == "number":
        return "number"
    return "text"


def is_probably_boolean_value(key: str) -> bool:
    numeric_words = ("Min", "Max", "Count", "Delay", "Distance", "Radius", "Chance", "Ratio", "Level", "Time", "Interval", "Weight", "Port", "Size", "Score", "Limit", "Threshold", "Cooldown", "Duration")
    return not any(word in key for word in numeric_words)
