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

FORCE_NUMBER_KEYS = {
    "AiPlayerbot.AutoGearScoreLimit", "AiPlayerbot.RandomGearScoreLimit",
    "AiPlayerbot.LimitEnchantExpansion", "AiPlayerbot.LimitGearExpansion",
    "AiPlayerbot.RandomGearLoweringChance", "AiPlayerbot.GearScoreCheck",
    "AiPlayerbot.EquipmentPersistenceLevel", "AiPlayerbot.AutoInitEquipLevelLimitRatio",
    "AiPlayerbot.EndFishingWithMaster", "AiPlayerbot.BotActiveAlone",
    "AiPlayerbot.RandomBotAutoJoinICBrackets", "AiPlayerbot.RandomBotAutoJoinEYBrackets",
    "AiPlayerbot.RandomBotAutoJoinAVBrackets", "AiPlayerbot.RandomBotAutoJoinABBrackets",
    "AiPlayerbot.RandomBotAutoJoinWSBrackets", "AiPlayerbot.RandomBotAutoJoinArenaBracket",
}

FORCE_TEXT_KEYS = {
    "AiPlayerbot.AoeAvoidSpellWhitelist", "AiPlayerbot.BotCheats",
    "AiPlayerbot.AllowedLogFiles", "AiPlayerbot.PremadeAvoidAoe",
    "AiPlayerbot.TradeActionExcludedPrefixes",
}

ENUM_ROLL_KEYS = {"AiPlayerbot.LootNeedRollLevel"}
ENUM_QUALITY_KEYS = {"AiPlayerbot.AutoGearQualityLimit", "AiPlayerbot.RandomGearQualityLimit"}
ENUM_PET_STANCE_KEYS = {"AiPlayerbot.DefaultPetStance"}
ENUM_TRADING_KEYS = {"AiPlayerbot.EnableRandomBotTrading"}
ENUM_MOVEMENT_KEYS = {"AiPlayerbot.DisableMoveSplinePath"}
FORCE_BOOLEAN_KEYS = {
    "AiPlayerbot.LootGreedRollLevel", "AiPlayerbot.GearScoreCheck",
}


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
    "AiPlayerbot.RandomBotShowHelmet": ("RandomBots zeigen Helm", "Legt fest, ob zufaellige Bots ihren Helm sichtbar tragen. Reine Optik; wirkt erst nach Reset/Neuinitialisierung der RandomBots."),
    "AiPlayerbot.RandomBotShowCloak": ("RandomBots zeigen Umhang", "Legt fest, ob zufaellige Bots ihren Umhang sichtbar tragen. Reine Optik; wirkt erst nach Reset/Neuinitialisierung der RandomBots."),
    "AiPlayerbot.AutoEquipUpgradeLoot": ("Beute-Upgrades automatisch anlegen", "Wenn aktiv, legen Account-/Altbots bessere Items aus ihrem Inventar automatisch an. Das macht Bots wartungsaermer und staerker. Wenn du zuerst ueber Beute entscheiden willst, eher deaktivieren."),
    "AiPlayerbot.EquipUpgradeThreshold": ("Mindestverbesserung fuer Auto-Ausrüstung", "Faktor fuer automatische Ausruestungswechsel. 1.1 bedeutet: ein neues Item muss etwa 10 Prozent besser bewertet sein als das aktuelle. Niedriger wechselt haeufiger, hoeher nur bei klaren Upgrades."),
    "AiPlayerbot.TwoRoundsGearInit": ("Ausrüstung in zwei Durchgaengen erzeugen", "Bei der Bot-Erstausruestung wird ein zweiter Durchlauf gemacht, damit zusammenpassendere Ausruestung entsteht. Das kann Bots besser ausstatten, verlaengert aber Initialisierung/Randomisierung."),
    "AiPlayerbot.FreeMethodLoot": ("Bei freier Beute weiter plündern", "Wenn aktiv, plündern Bots auch dann weiter, wenn die Gruppenlootmethode 'Jeder gegen jeden / frei fuer alle' ist. Wenn du als Spieler immer zuerst looten willst, diesen Schalter deaktiviert lassen."),
    "AiPlayerbot.LootNeedRollLevel": ("Bot-Wurf bei Bedarf-Items", "Bestimmt, was Bots tun, wenn ein Item fuer sie als Bedarf gilt: 0 = passen, 1 = nur Gier, 2 = Bedarf. Fuer 'Spieler darf zuerst plündern' ist 0 am strengsten."),
    "AiPlayerbot.LootGreedRollLevel": ("Gierwürfe der Bots erlauben", "Globaler Schalter fuer Gierwuerfe. Aus bedeutet: Bots passen statt Gier zu wuerfeln. An bedeutet: Bots duerfen auf passende Items mit Gier wuerfeln."),
    "AiPlayerbot.LootRollRecipe": ("Auf Rezepte würfeln", "Wenn aktiv, wuerfeln Bots auf Rezepte. Lernbare Berufsrezepte koennen sie mit Bedarf nehmen; BoE-Rezepte koennen sie mit Gier nehmen, wenn Gierwuerfe erlaubt sind."),
    "AiPlayerbot.LootRollDisenchant": ("Entzaubern statt Gier wuerfeln", "Bots mit Verzauberkunst wuerfeln auf entzauberbare Items mit Entzaubern statt mit Gier. Deaktiviert laesst sie normal mit Gier wuerfeln, falls Gier erlaubt ist."),
    "AiPlayerbot.IterationsPerTick": ("KI-Schritte pro Tick", "Wie viele Bot-KI-Schritte pro Server-Tick verarbeitet werden. Höher macht Bots reaktionsfreudiger, kann aber CPU-Last stark erhöhen."),
    "AiPlayerbot.GlobalCooldown": ("Bot-Global-Cooldown", "Grundpause zwischen Botaktionen. Niedriger macht Bots schneller und stärker, höher ruhiger und weniger belastend."),
    "AiPlayerbot.ReactDelay": ("Reaktionsverzögerung", "Zeit, bis Bots auf Ereignisse reagieren. Niedriger wirkt menschlich schneller, erhöht aber Last und Botstärke."),
    "AiPlayerbot.DynamicReactDelay": ("Dynamische Reaktionsverzögerung", "Passt Reaktion je nach Situation an. Aktiviert kann Bots natürlicher und weniger gleichförmig machen."),
    "AiPlayerbot.SightDistance": ("Sichtdistanz", "Distanz, in der Bots Ziele, Spieler und Ereignisse beachten. Höher wirkt intelligenter, kostet aber mehr Such- und KI-Arbeit."),
    "AiPlayerbot.FollowDistance": ("Folgedistanz", "Abstand, den Bots beim Folgen halten. Niedriger klebt dichter am Spieler, höher wirkt natürlicher, kann aber in engen Wegen stören."),
    "AiPlayerbot.CriticalHealth": ("Kritische Gesundheit", "Prozentwert, ab dem Bots Gesundheit als kritisch bewerten. Höher lässt sie früher defensiv reagieren oder heilen."),
    "AiPlayerbot.LowMana": ("Niedriges Mana", "Prozentwert, ab dem Bots Mana sparen oder trinken möchten. Höher macht Caster vorsichtiger, niedriger aggressiver."),
    "AiPlayerbot.LootDelay": ("Plünder-Verzoegerung", "Wartezeit in Millisekunden, bevor Bots nach Beute greifen. Hoeher gibt Spielern mehr Zeit, zuerst zu plündern; niedriger laesst Bots schneller looten."),
    "AiPlayerbot.LootDistance": ("Plünder-Reichweite", "Entfernung in Yards, aus der Bots Beute wahrnehmen und aufnehmen. Niedriger reduziert Bot-Looting in deiner Naehe; hoeher macht Bots selbststaendiger."),
    "AiPlayerbot.AoeAvoidSpellWhitelist": ("AOE-Ausweich-Ausnahmen", "Kommagetrennte Zauber-IDs, vor denen Bots nicht ausweichen sollen. Nur IDs eintragen, wenn du sicher bist, dass die Fläche harmlos oder gewollt ist. Falsche Einträge können Bots in gefährlichen Flächen stehen lassen."),
    "AiPlayerbot.DisableMoveSplinePath": ("Bewegungspfad-System", "Legt fest, ob Bots das normale MoveSplinePath-Bewegungssystem verwenden: 0 = überall aktiv, 1 = nur in BG/Arena deaktiviert, 2 = überall deaktiviert. Deaktivieren macht Bewegung gröber, hilft aber, damit Stuns, Verlangsamungen und Roots korrekt auf Bots wirken."),
    "AiPlayerbot.AutoPickReward": ("Questbelohnung automatisch wählen", "Bots wählen Questbelohnungen selbst. Praktisch bei vielen Bots, kann aber nicht immer die perfekte Belohnung treffen."),
    "AiPlayerbot.SyncQuestWithPlayer": ("Bot-Quests mit Spieler synchronisieren", "Bots versuchen, Quests an den Spieler anzugleichen. Gut für gemeinsames Leveln, kann aber zusätzliche Questlogik erzeugen."),
    "AiPlayerbot.SyncQuestForPlayer": ("Spielerquests für Bots übernehmen", "Bots nehmen passende Spielerquests auf. Macht Gruppenquesten flüssiger, verändert aber Bot-Questfortschritt automatisch."),
    "AiPlayerbot.DropObsoleteQuests": ("Veraltete Quests aufgeben", "Bots geben alte oder nicht mehr passende Quests auf. Hält Questlogs sauber, kann aber bewusst behaltene Quests entfernen."),
    "AiPlayerbot.AutoDoQuests": ("Bots erledigen Quests automatisch", "RandomBots erledigen selbstständig Quests. Belebt die Welt und levelt Bots, erhöht aber KI- und Datenbankaktivität."),
    "AiPlayerbot.RandomBotJoinLfg": ("RandomBots im Dungeonfinder", "RandomBots dürfen sich für Dungeonfinder anmelden. Belebt Instanzen, kann aber Gruppen mit Bots füllen."),
    "AiPlayerbot.RandomBotJoinBG": ("RandomBots im PvP", "RandomBots dürfen Schlachtfelder nutzen. Belebt PvP, kann aber Balance und Warteschlangen stark verändern."),
    "AiPlayerbot.RandomBotAutoJoinBG": ("RandomBots automatisch ins Schlachtfeld", "Bots melden sich selbstständig für Battlegrounds an. Aktiviert macht PvP lebendiger, kostet aber zusätzliche KI-Last."),
    "AiPlayerbot.RandomBotAutoJoinICBrackets": ("Insel der Eroberung: Levelbereiche", "Levelbereich-Liste für automatische Bot-Anmeldung. Werte sind keine Ja/Nein-Schalter: 0 = 10-19, 1 = 20-29, 2 = 30-39 und so weiter. Mehrere Werte können kommagetrennt eingetragen werden."),
    "AiPlayerbot.RandomBotAutoJoinEYBrackets": ("Auge des Sturms: Levelbereiche", "Levelbereich-Liste für automatische Bot-Anmeldung. Werte sind keine Ja/Nein-Schalter: 0 = 10-19, 1 = 20-29, 2 = 30-39 und so weiter. Mehrere Werte können kommagetrennt eingetragen werden."),
    "AiPlayerbot.RandomBotAutoJoinAVBrackets": ("Alteractal: Levelbereiche", "Levelbereich-Liste für automatische Bot-Anmeldung. Werte sind keine Ja/Nein-Schalter: 0 = 10-19, 1 = 20-29, 2 = 30-39 und so weiter. Mehrere Werte können kommagetrennt eingetragen werden."),
    "AiPlayerbot.RandomBotAutoJoinABBrackets": ("Arathibecken: Levelbereiche", "Levelbereich-Liste für automatische Bot-Anmeldung. Werte sind keine Ja/Nein-Schalter: 0 = 10-19, 1 = 20-29, 2 = 30-39 und so weiter. Mehrere Werte können kommagetrennt eingetragen werden."),
    "AiPlayerbot.RandomBotAutoJoinWSBrackets": ("Kriegshymnenschlucht: Levelbereiche", "Levelbereich-Liste für automatische Bot-Anmeldung. Werte sind keine Ja/Nein-Schalter: 0 = 10-19, 1 = 20-29, 2 = 30-39 und so weiter. Bei WSG ist 7 der Level-80-Bereich."),
    "AiPlayerbot.RandomBotAutoJoinArenaBracket": ("Arena: Levelbereich", "Levelbereich für automatische Arena-Anmeldung. Das ist kein Ja/Nein-Schalter: 14 entspricht dem Levelbereich 80-84. Niedrigere Bereiche brauchen je nach Core zusätzliche Anpassungen."),
    "AiPlayerbot.RandomBotLoginAtStartup": ("RandomBots beim Serverstart einloggen", "Bots werden direkt beim Start hochgefahren. Welt ist sofort belebter, der Start dauert aber länger und Lastspitzen steigen."),
    "AiPlayerbot.EnableRandomBotTrading": ("RandomBot-Handel", "Steuert den simulierten Handel zufälliger Bots: 0 = aus, 1 = kaufen und verkaufen, 2 = nur kaufen, 3 = nur verkaufen. Höhere Handelsaktivität belebt Wirtschaft und Auktionshaus, erzeugt aber mehr Datenbank- und Wirtschaftsbewegung."),
    "AiPlayerbot.TradeActionExcludedPrefixes": ("Ausgeschlossene Handels-Chatpräfixe", "Kommagetrennte Liste von Chat-Präfixen, die bei der Analyse von Handelsaktionen ignoriert werden. Damit reagieren Bots nicht versehentlich auf Addon- oder Systemnachrichten."),
    "AiPlayerbot.EnableBroadcasts": ("Bot-Broadcasts aktiv", "Bots schreiben automatische Meldungen in Kanäle. Das wirkt lebendig, kann aber schnell wie Spam aussehen."),
    "AiPlayerbot.CommandPrefix": ("Bot-Befehlspräfix", "Zeichenfolge, mit der Bot-Kommandos beginnen. Spieler nutzen sie im Chat, um Bots zu steuern."),
    "AiPlayerbot.CommandSeparator": ("Bot-Befehlstrenner", "Trenner für mehrere Bot-Kommandos. Nur ändern, wenn du das Chat-Befehlssystem bewusst anders bedienen willst."),
    "AiPlayerbot.AutoGearCommand": ("AutoGear-Befehl aktiv", "Erlaubt die automatische Ausruestungslogik per Befehl. Aktiviert macht die Botpflege leichter; deaktiviert verhindert, dass Bots automatisch neue Gear-Bewertung ausloesen."),
    "AiPlayerbot.AutoGearCommandAltBots": ("AutoGear auch fuer Altbots", "Erlaubt AutoGear fuer Bots, die als Begleiter/Altbots genutzt werden. Deaktivieren, wenn du deren Ausruestung lieber manuell kontrollierst."),
    "AiPlayerbot.AutoGearQualityLimit": ("Maximale Qualitaet fuer AutoGear", "Hoechste Itemqualitaet, die AutoGear fuer Ausruestungsentscheidungen verwenden darf. Hoeher erlaubt bessere Items; niedriger verhindert, dass Bots sehr wertvolle Beute selbst nutzen."),
    "AiPlayerbot.AutoGearScoreLimit": ("Maximaler Gearscore fuer AutoGear", "Obergrenze fuer automatische Ausruestungsbewertung. 0 bedeutet normalerweise keine harte Grenze. Setzen, wenn Bots nicht ueber ein bestimmtes Ausruestungsniveau hinaus optimieren sollen."),
    "AiPlayerbot.RandomGearQualityLimit": ("Maximale Qualitaet fuer RandomBot-Gear", "Hoechste Itemqualitaet, die RandomBots bei zufaelliger Ausruestung erhalten duerfen. Hoeher macht RandomBots staerker; niedriger haelt sie einfacher."),
    "AiPlayerbot.RandomGearScoreLimit": ("Maximaler Gearscore fuer RandomBot-Gear", "Obergrenze fuer zufaellige Bot-Ausrüstung. 0 bedeutet normalerweise keine harte Grenze."),
    "AiPlayerbot.IncrementalGearInit": ("Ausrüstung schrittweise initialisieren", "Bots werden beim Erzeugen schrittweise mit Ausruestung aufgebaut. Aktiviert wirkt meist sauberer, kann Initialisierung aber verlaengern."),
    "AiPlayerbot.MinEnchantingBotLevel": ("Mindestlevel fuer Verzauberer-Bots", "Ab diesem Level koennen Bots fuer Verzauberungslogik beruecksichtigt werden. Hoeher beschraenkt Entzauber-/Verzauberlogik auf fortgeschrittene Bots."),
    "AiPlayerbot.LimitEnchantExpansion": ("Verzauberungen auf Erweiterung begrenzen", "Begrenzt Verzauberungen auf den simulierten Erweiterungsstand. Niedrigere Werte halten Bots naeher an Classic/TBC; hoehere Werte erlauben WotLK-Ausruestung."),
    "AiPlayerbot.LimitGearExpansion": ("Ausrüstung auf Erweiterung begrenzen", "Begrenzt Bot-Gear auf den simulierten Erweiterungsstand. Wichtig, wenn Bots beim Leveln keine spaeteren Erweiterungsitems tragen sollen."),
    "AiPlayerbot.RandomGearLoweringChance": ("Chance auf schlechtere RandomBot-Ausrüstung", "Chance, dass RandomBots absichtlich schlechtere Ausruestung bekommen. Hoeher macht sie menschlicher und weniger perfekt; 0 gibt keine kuenstliche Absenkung."),
    "AiPlayerbot.GearScoreCheck": ("Gearscore-Pruefung aktiv", "Steuert, ob Ausruestung nach Gearscore bewertet/geprueft wird. Aktivieren kann Bot-Gear besser kontrollieren, kostet aber etwas Logik."),
    "AiPlayerbot.EquipmentPersistence": ("Ausrüstung dauerhaft speichern", "Wenn aktiv, behalten Bots ihre Ausruestung dauerhafter statt sie bei Randomisierung/Initialisierung staendig neu zu erzeugen."),
    "AiPlayerbot.EquipmentPersistenceLevel": ("Ausrüstung speichern ab Level", "Ab diesem Level wird dauerhafte Ausruestung relevanter. Hoeher betrifft nur Endgame-Bots, niedriger auch Levelbots."),
    "AiPlayerbot.AutoUpgradeEquip": ("Ausrüstung automatisch verbessern", "Wenn aktiv, versuchen Bots ihre Ausruestung automatisch zu verbessern. Deaktivieren, wenn Spieler Loot und Ausruestung zuerst kontrollieren sollen."),
    "AiPlayerbot.HunterWolfPet": ("Jaegerbots nutzen Wolf", "Steuert, ob Jaegerbots bevorzugt einen Wolf als Begleiter erhalten. Das beeinflusst Begleiterwahl und Gruppenbuffs."),
    "AiPlayerbot.DefaultPetStance": ("Standardhaltung fuer Begleiter", "Start-Haltung fuer Bot-Begleiter: passiv, defensiv oder aggressiv. Defensiv ist meist am kontrollierbarsten; aggressiv kann ungewollt Gegner ziehen."),
    "AiPlayerbot.ExcludedHunterPetFamilies": ("Ausgeschlossene Jaegerbegleiter-Familien", "Liste von Begleiterfamilien, die Jaegerbots nicht verwenden sollen. Leer bedeutet keine zusaetzlichen Ausschluesse."),
    "AiPlayerbot.EnableFishingWithMaster": ("Mit dem Spieler angeln", "Wenn aktiv, fügen Bots mit Angelskill automatisch die Angel-Strategie hinzu, sobald ihr Spieler angelt. Das betrifft wirklich Angeln, nicht Loot oder Auktionshaus."),
    "AiPlayerbot.FishingDistanceFromMaster": ("Angel-Suchdistanz beim Spieler", "Yards, in denen ein Bot in der Nähe seines Spielers nach Wasser zum Angeln sucht. Höher lässt Bots weiter ausschweifen, niedriger hält sie näher bei dir."),
    "AiPlayerbot.FishingDistance": ("Angel-Suchdistanz ohne Spieler", "Yards, in denen ein Bot ohne direkten Spieler nach Wasser suchen würde. In deiner Config steht, dass masterlose Bots aktuell nicht angeln; der Wert ist deshalb meist nur Reserve."),
    "AiPlayerbot.EndFishingWithMaster": ("Angeln beenden ab Abstand", "Yards Abstand zum Wasser, ab dem ein Bot die Angel-Strategie wieder entfernt. Höher beendet später, niedriger beendet schneller, wenn er sich vom Angelplatz entfernt."),
    "AiPlayerbot.AutoInitEquipLevelLimitRatio": ("Levelgrenze fuer Startausruestung", "Verhaeltnis, bis zu welchem Levelbereich Bots bei der automatischen Erstausruestung Items erhalten duerfen. Hoeher kann Bots staerker ausstatten; niedriger haelt Gear naeher am Bot-Level."),
    "AiPlayerbot.MaintenanceCommand": ("Wartungsbefehl aktiv", "Erlaubt Wartungsfunktionen fuer Bots. Diese Funktionen fuellen oder korrigieren Dinge wie Munition, Reagenzien, Essen, Taschen, Reittiere, Skills, Zauber, Talente und Begleiter."),
    "AiPlayerbot.AltMaintenanceAmmo": ("Bot-Wartung: Munition", "Bots koennen bei der Wartung Munition auffuellen. Fuer Jaegerkomfort aktiv lassen; deaktivieren, wenn Munition bewusst knapp bleiben soll."),
    "AiPlayerbot.AltMaintenanceFood": ("Bot-Wartung: Essen", "Bots koennen Essen fuer Regeneration auffuellen. Aktiviert reduziert Pausenprobleme, deaktiviert macht Versorgung manueller."),
    "AiPlayerbot.AltMaintenanceReagents": ("Bot-Wartung: Reagenzien", "Bots koennen Klassen-/Zauberreagenzien auffuellen. Aktiviert verhindert fehlende Buffs oder Zauber durch leere Reagenzien."),
    "AiPlayerbot.AltMaintenanceConsumables": ("Bot-Wartung: Verbrauchsgueter", "Bots koennen allgemeine Verbrauchsgueter auffuellen. Aktiviert macht Bots selbstaendiger, kann aber mehr Items erzeugen oder kaufen lassen."),
    "AiPlayerbot.AltMaintenancePotions": ("Bot-Wartung: Traenke", "Bots koennen Traenke auffuellen. Aktiviert macht sie in Kaempfen robuster; deaktiviert reduziert automatische Vorteile."),
    "AiPlayerbot.AltMaintenanceBags": ("Bot-Wartung: Taschen", "Bots koennen Taschen verwalten oder auffuellen. Aktiviert verhindert volle Inventare, deaktiviert macht Inventarprobleme wahrscheinlicher."),
    "AiPlayerbot.AltMaintenanceMounts": ("Bot-Wartung: Reittiere", "Bots koennen passende Reittiere erhalten. Aktiviert verbessert Reiseverhalten; deaktiviert laesst Reittiere manueller/limitierter."),
    "AiPlayerbot.AltMaintenanceSkills": ("Bot-Wartung: Skills", "Bots koennen Skills nachziehen. Aktiviert haelt sie spielbarer; deaktiviert kann zu fehlenden Waffen-/Berufsskills fuehren."),
    "AiPlayerbot.AltMaintenanceClassSpells": ("Bot-Wartung: Klassenzauber", "Bots koennen wichtige Klassenzauber lernen. Aktiviert verhindert unvollstaendige Klassenkits."),
    "AiPlayerbot.AltMaintenanceAvailableSpells": ("Bot-Wartung: verfuegbare Zauber", "Bots koennen verfuegbare trainierbare Zauber lernen. Aktiviert macht sie staerker und vollstaendiger."),
    "AiPlayerbot.AltMaintenanceSpecialSpells": ("Bot-Wartung: Spezialzauber", "Bots koennen besondere Zusatzzauber erhalten, falls die Playerbot-Logik diese vorsieht."),
    "AiPlayerbot.AltMaintenanceTalentTree": ("Bot-Wartung: Talentbaum", "Bots koennen Talentpunkte passend verteilen. Aktiviert macht sie kampffaehiger; deaktiviert laesst Talente eher unveraendert."),
    "AiPlayerbot.AltMaintenanceGlyphs": ("Bot-Wartung: Glyphen", "Bots koennen Glyphen verwalten. Aktiviert verbessert Spezialisierungen, deaktiviert spart automatische Optimierung."),
    "AiPlayerbot.AltMaintenanceGemsEnchants": ("Bot-Wartung: Sockel & Verzauberungen", "Bots koennen Edelsteine und Verzauberungen pflegen. Aktiviert macht sie deutlich staerker; deaktiviert gibt Spielern mehr Kontrolle."),
    "AiPlayerbot.AltMaintenancePet": ("Bot-Wartung: Begleiter", "Bots koennen Begleiter verwalten. Relevant vor allem fuer Jaeger und Hexenmeister."),
    "AiPlayerbot.AltMaintenancePetTalents": ("Bot-Wartung: Begleiter-Talente", "Bots koennen Begleiter-Talente setzen. Aktiviert verbessert Begleiterleistung."),
    "AiPlayerbot.AltMaintenanceReputation": ("Bot-Wartung: Ruf", "Bots koennen rufbezogene Wartungslogik nutzen. Nur aktiv lassen, wenn automatische Rufpflege gewuenscht ist."),
    "AiPlayerbot.AltMaintenanceKeyring": ("Bot-Wartung: Schluesselbund", "Bots koennen Schluesselbund/Zugangsitems verwalten. Hilft bei Instanzen und alten Zugangsmechaniken."),
    "AiPlayerbot.BotActiveAlone": ("Aktive Bots ohne Spielergruppe", "Prozentwert der Bots, die auch ohne direkten Spieler aktiv bleiben. 0 bedeutet: nur erzwungen aktive Bots bleiben wach. 100 bedeutet: alle Bots bleiben aktiv und erzeugen maximale Last."),
    "AiPlayerbot.BotActiveAloneDurationSeconds": ("Wechselzeit aktiver Bots", "Sekunden bis die aktive Bot-Auswahl rotiert. Höher hält dieselben Bots länger aktiv; niedriger wechselt häufiger. Bots in Kampf, Instanz, BG, LFG oder mit Spielern werden nicht mitten in der Aktion abgeschaltet."),
    "AiPlayerbot.BotActiveAloneForceWhenInRadius": ("Aktiv halten: Spieler im Umkreis", "Yards um echte Spieler, in denen Bots aktiv bleiben. 0 deaktiviert diese Regel. Höher hält mehr Bots in deiner Nähe aktiv und lebendig, kostet aber Leistung."),
    "AiPlayerbot.BotActiveAloneForceWhenInZone": ("Aktiv halten: gleiche Zone", "Wenn aktiv, bleiben Bots in der gleichen Zone wie ein echter Spieler wach. Macht Zonen lebendiger, erhöht aber die Botlast."),
    "AiPlayerbot.BotActiveAloneForceWhenInMap": ("Aktiv halten: gleiche Karte", "Wenn aktiv, bleiben Bots auf derselben Weltkarte/Kontinent wie ein echter Spieler wach. Das ist deutlich breiter als Zone und kann viel Last erzeugen."),
    "AiPlayerbot.BotActiveAloneForceWhenIsFriend": ("Aktiv halten: Freundesliste", "Wenn aktiv, bleiben Bots wach, wenn ein echter Spieler sie auf der Freundesliste hat. Praktisch für feste Begleiter."),
    "AiPlayerbot.BotActiveAloneForceWhenInGuild": ("Aktiv halten: Gilde", "Wenn aktiv, bleiben Bots in einer Gilde mit echten Spielern wach. Gut für Gildenleben, aber mit mehr aktiven Bots verbunden."),
    "AiPlayerbot.BotCheats": ("Bot-Komfort-Cheats", "Kommagetrennte Liste erlaubter Komfortfunktionen für Bots, zum Beispiel food, taxi oder raid. Nur bewusst ändern: diese Einträge können Botverhalten deutlich weniger blizzlike machen."),
    "AiPlayerbot.AllowedLogFiles": ("Erlaubte Logdateien", "Liste erlaubter Playerbot-Logdateien. Leer bedeutet keine zusätzliche Freigabe. Nur ändern, wenn du gezielt Debuglogs aktivieren willst."),
    "AiPlayerbot.PremadeAvoidAoe": ("Premade: AOE meiden", "Spezialwert für Premade-KI, welche Flächeneffekte Bots vermeiden sollen. Das ist kein Ja/Nein-Feld; die Syntax kann IDs und Parameter enthalten. Nur mit bekannter Playerbot-Syntax ändern."),
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
            type=field_type(item.key, item.type, item.value),
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
    if raw.startswith("BroadcastChanceLootingItem"):
        return "Chat-Chance: " + quality_label(raw[len("BroadcastChanceLootingItem"):]) + " geplündert"
    if raw.startswith("BroadcastChanceQuest"):
        return "Chat-Chance: Quest " + translate_words(raw[len("BroadcastChanceQuest"):])
    if raw.startswith("BroadcastChanceKill"):
        return "Chat-Chance: Gegner " + translate_words(raw[len("BroadcastChanceKill"):])
    if raw.startswith("BroadcastChanceLevelup"):
        return "Chat-Chance: Levelaufstieg " + translate_words(raw[len("BroadcastChanceLevelup"):])
    if raw.startswith("BroadcastChanceSuggest"):
        return "Chat-Chance: Bot-Vorschlag " + translate_words(raw[len("BroadcastChanceSuggest"):])
    if raw.startswith("BroadcastChance"):
        return "Chat-Chance: " + translate_words(raw[len("BroadcastChance"):])
    if raw.startswith("AltMaintenance"):
        return "Bot-Wartung: " + translate_words(raw[len("AltMaintenance"):])
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


def quality_label(value: str) -> str:
    labels = {
        "Poor": "graues Item",
        "Normal": "weisses Item",
        "Uncommon": "gruenes Item",
        "Rare": "blaues Item",
        "Epic": "episches Item",
        "Legendary": "legendaeres Item",
        "Artifact": "Artefakt-Item",
    }
    return labels.get(value, translate_words(value))


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
        "Poor": "graue Items", "Uncommon": "grüne Items", "Rare": "blaue Items", "Epic": "epische Items",
        "Legendary": "legendäre Items", "Artifact": "Artefakt-Items", "Looting": "Plündern",
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
    if key.startswith("AiPlayerbot.BroadcastChanceLootingItem"):
        return "Chance in Prozent/Gewichtung, dass ein Bot eine Chatmeldung schreibt, wenn er Beute dieser Qualität findet oder aufnimmt. Höher macht Loot-Ereignisse sichtbarer, kann aber den Chat füllen. Niedriger macht Bots ruhiger."
    if key.startswith("AiPlayerbot.BroadcastChanceQuest"):
        return "Chance in Prozent/Gewichtung für Bot-Chat bei Questfortschritt, Questabschluss oder Questabgabe. Höher lässt Bots häufiger über Quests sprechen; niedriger reduziert Meldungen beim Leveln."
    if key.startswith("AiPlayerbot.BroadcastChanceKill"):
        return "Chance in Prozent/Gewichtung für Bot-Chat nach getöteten Gegnern. Höher erzeugt mehr Kampfkommentare, niedriger macht Gruppen ruhiger."
    if key.startswith("AiPlayerbot.BroadcastChanceLevelup"):
        return "Chance in Prozent/Gewichtung für Bot-Chat beim Levelaufstieg. Höher zeigt Levelups deutlicher im Chat, niedriger verhindert häufige Jubelmeldungen."
    if key.startswith("AiPlayerbot.BroadcastChanceSuggest"):
        return "Chance in Prozent/Gewichtung, dass Bots dem Spieler Vorschläge machen, zum Beispiel zu Quests, Reisen oder Gruppenaktionen. Höher wirkt hilfsbereiter, zu hoch kann stören."
    if key.startswith("AiPlayerbot.BroadcastChance"):
        return "Chance in Prozent/Gewichtung für automatische Bot-Nachrichten zu diesem Ereignis. Höher macht Bots gesprächiger und die Welt lebendiger; zu hoch wirkt schnell wie Spam."
    if "Distance" in key or "Radius" in key:
        return "Distanzwert für Bot-KI. Höhere Werte lassen Bots weiter sehen, folgen oder reagieren, erhöhen aber Sucharbeit und können Verhalten weiträumiger machen."
    if "Delay" in key or "Cooldown" in key or "Interval" in key or "Time" in key:
        return "Zeitwert für Bot-Verhalten. Niedriger reagiert schneller und wirkt aktiver, kann aber Last und Botstärke erhöhen. Höher macht Bots ruhiger und ressourcenschonender."
    if "Health" in key or "Mana" in key:
        return "Schwellwert für Ressourcenbewertung. Bots entscheiden damit, wann sie heilen, Mana sparen, trinken oder defensiver spielen. Höher reagiert vorsichtiger, niedriger aggressiver."
    if "Gear" in key or "Equip" in key or "Loot" in key:
        return "Ausrüstungs- oder Beuteregel. Sie beeinflusst, ob Bots Items aufnehmen, darauf würfeln, sie anlegen oder behalten. Niedrigere/strengere Werte geben Spielern mehr Kontrolle; automatische Werte machen Bots selbstständiger."
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


def field_type(key: str, detected: str, value: str = "") -> str:
    if key in {"PlayerbotsDatabaseInfo"}:
        return "password"
    if key in FORCE_TEXT_KEYS:
        return "text"
    if key in ENUM_ROLL_KEYS:
        return "enum_roll"
    if key in ENUM_QUALITY_KEYS:
        return "enum_quality"
    if key in ENUM_PET_STANCE_KEYS:
        return "enum_pet_stance"
    if key in ENUM_TRADING_KEYS:
        return "enum_trading"
    if key in ENUM_MOVEMENT_KEYS:
        return "enum_movement"
    if key in FORCE_BOOLEAN_KEYS:
        return "boolean"
    if key in FORCE_NUMBER_KEYS or any(key.startswith(prefix) for prefix in FORCE_NUMBER_PREFIXES):
        return "number"
    if detected == "boolean" or any(hint in key for hint in BOOLEAN_HINTS):
        if is_probably_boolean_value(key):
            return "boolean"
    if detected == "number" or is_numeric_value(value):
        return "number"
    return "text"


def is_probably_boolean_value(key: str) -> bool:
    numeric_words = ("Min", "Max", "Count", "Delay", "Distance", "Radius", "Chance", "Ratio", "Level", "Time", "Interval", "Weight", "Port", "Size", "Score", "Limit", "Threshold", "Cooldown", "Duration", "Stance")
    return not any(word in key for word in numeric_words)


def is_numeric_value(value: str) -> bool:
    return bool(re.fullmatch(r"-?\d+(\.\d+)?", str(value or "").strip()))
