import re
from dataclasses import asdict

from .config_scanner import ConfigOption, scan_content, update_value
from .ssh_service import SSHClient, shell_quote


MAIN_FILES = ("authserver.conf", "worldserver.conf")

GROUP_ORDER = [
    ("uebersicht", "Übersicht & wichtigste Regler"),
    ("auth_login", "Authserver: Login & Sicherheit"),
    ("datenbanken", "Datenbanken & Updates"),
    ("remote", "Remotezugriff: SOAP, RA & Konsole"),
    ("leistung", "Leistung, Netzwerk & Stabilität"),
    ("logs", "Logs, Monitoring & Diagnose"),
    ("realm", "Realm, Client & Session"),
    ("gm", "GM-System, Tickets & Support"),
    ("charaktere", "Charaktere, Startwerte & Namen"),
    ("raten", "Raten: XP, Ruf, Skills & Progress"),
    ("welt", "Welt, Sichtweite, Karten & Wetter"),
    ("kampf", "Kampf, Kreaturen & Todesfolgen"),
    ("loot", "Loot, Items & Wirtschaft"),
    ("gruppen", "Gruppen, Instanzen & Dungeonfinder"),
    ("pvp", "PvP, Schlachtfelder & Arena"),
    ("gilden", "Gilden, Mail & Kommunikation"),
    ("warden", "Warden & Schutzmechanismen"),
    ("sonstige", "Weitere Spezialoptionen"),
]

IMPORTANT_KEYS = {
    "PlayerLimit", "GameType", "Expansion", "MaxPlayerLevel", "StartPlayerLevel",
    "Rate.XP.Kill", "Rate.XP.Quest", "Rate.Drop.Money", "Rate.Drop.Item.Normal",
    "Rate.Reputation.Gain", "Rate.Honor", "Rate.Creature.Normal.HP",
    "Rate.Creature.Normal.Damage", "InstantLogout", "CharactersPerRealm",
    "CharactersPerAccount", "AllowTickets", "GM.Visible", "GM.Chat", "SOAP.Enabled",
    "SOAP.Port", "Ra.Enable", "WorldServerPort", "RealmServerPort", "BindIP",
    "DataDir", "LogsDir", "ActivateWeather", "ChangeWeatherInterval",
    "Visibility.Distance.Continents", "MoveMaps.Enable", "vmap.enableLOS",
    "vmap.enableHeight", "Warden.Enabled", "AutoBroadcast.On",
}

FORCE_NUMBER_KEYS = {
    "UseProcessors", "WrongPass.MaxCount",
    "LoginDatabase.WorkerThreads", "LoginDatabase.SynchThreads", "WorldDatabase.WorkerThreads",
    "WorldDatabase.SynchThreads", "CharacterDatabase.WorkerThreads", "CharacterDatabase.SynchThreads",
    "Updates.EnableDatabases", "RealmID", "Network.Threads", "ThreadPool", "Compression",
    "Metric.Interval", "Metric.OverallStatusInterval", "ClientCacheVersion",
    "DisconnectToleranceInterval", "MaxCoreStuckTime",
    "Warden.NumLuaChecks", "Warden.NumMemChecks", "Warden.NumOtherChecks",
    "AutoBroadcast.MinDisableLevel",
    "LevelReq.Mail", "LevelReq.Auction", "AuctionHouse.WorkerThreads", "Rate.Auction.Time",
    "Rate.Auction.Deposit", "Rate.Auction.Cut", "Respawn.DynamicRateCreature",
    "Respawn.DynamicRateGameObject", "Channel.ModerationGMLevel", "ChatStrictLinkChecking.Severity",
    "ChatFlood.MessageDelay", "ChatFlood.AddonMessageDelay",
    "ChatLevelReq.Channel", "ChatLevelReq.Whisper", "ChatLevelReq.Say", "PartyLevelReq",
    "ChangeFaction.MaxMoney", "LevelReq.Ticket", "Command.LookupMaxResults",
    "Die.Command.Mode", "GM.LoginState", "GM.Visible", "GM.Chat", "GM.WhisperingTo",
    "GM.InGMList.Level", "GM.InWhoList.Level", "GM.StartLevel", "GM.TicketSystem.ChanceOfGMSurvey",
    "StrictPlayerNames", "StrictPetNames", "CharacterCreating.Disabled",
    "CharacterCreating.Disabled.RaceMask", "CharacterCreating.Disabled.ClassMask",
    "SkipCinematics", "CleanCharacterDB", "PersistentCharacterCleanFlags", "CharDelete.Method",
    "CharDelete.MinLevel", "CharDelete.KeepDays", "DungeonFinder.OptionsMask",
    "DungeonAccessRequirements.PrintMode", "DungeonAccessRequirements.OptionalStringID",
    "Wintergrasp.PlayerMin", "Battleground.ReportAFK",
    "Battleground.Warsong.Flags", "Arena.QueueAnnouncer.Detail", "PvPToken.MapAllowType",
}

FORCE_ENUM_KEYS = {
    "ProcessPriority", "WrongPass.BanType", "RealmZone", "PreventAFKLogout",
    "PacketSpoof.BanMode", "Warden.ClientCheckFailAction", "AutoBroadcast.Center",
    "Visibility.GroupMode", "StrictChannelNames", "ChatStrictLinkChecking.Severity",
    "ChatStrictLinkChecking.Kick", "Battleground.InvitationType",
}

FORCE_BOOLEAN_KEYS = {
    "EnableProxyProtocol", "WrongPass.Logging", "StrictVersionCheck", "AllowLoggingIPAddressesInDatabase",
    "EnableTOTP", "Updates.AutoSetup", "Updates.Redundancy", "Updates.ArchivedRedundancy",
    "Updates.AllowRehash", "Network.UseSocketActivation", "Console.Enable", "BeepAtStart",
    "FlashAtStart", "Network.TcpNodelay", "Network.EnableProxyProtocol", "Ra.Enable", "SOAP.Enabled",
    "Allow.IP.Based.Action.Logging", "LogSpamReports", "ChatLog.Enable", "Log.Async.Enable",
    "Metric.Enable", "Metric.InfluxDB.v2", "World.RealmAvailability", "CloseIdleConnections",
    "EnableLoginAfterDC", "SaveRespawnTimeImmediately", "Server.LoginInfo", "ShowKickInWorld",
    "ShowMuteInWorld", "ShowBanInWorld", "Warden.Enabled", "AutoBroadcast.On",
    "Visibility.ObjectSparkles", "Visibility.ObjectQuestMarkers", "MoveMaps.Enable",
    "vmap.enableLOS", "vmap.enableHeight", "vmap.petLOS", "vmap.BlizzlikePvPLOS",
    "vmap.BlizzlikeLOSInOpenWorld", "vmap.enableIndoorCheck", "DetectPosCollision",
    "CheckGameObjectLoS", "PreloadAllNonInstancedMapGrids", "DontCacheRandomMovementPaths",
    "ActivateWeather", "AllowTickets", "AllowPlayerCommands", "GM.AllowInvite", "GM.AllowFriend",
    "GM.LowerSecurity", "DisableWaterBreath", "AllFlightPaths", "InstantFlightPaths",
    "AlwaysMaxSkillForLevel", "AlwaysMaxWeaponSkill", "PlayerStart.AllReputation",
    "PlayerStart.CustomSpells", "PlayerStart.MapsExplored", "InstantLogout",
    "PlayerSave.Stats.SaveOnlyOnLogout", "ValidateSkillLearnedBySpells", "DeclinedNames",
    "StrictNames.Reserved", "StrictNames.Profanity", "EnablePlayerSettings", "EnableLowLevelRegenBoost",
    "SpellQueue.Enabled", "SkillChance.MiningSteps", "SkillChance.SkinningSteps",
    "OffhandCheckAtSpellUnlearn", "Stats.Limits.Enable", "PvPToken.Enable", "Death.Bones.World",
    "Death.Bones.BattlegroundOrArena", "ItemDelete.Vendor", "DBC.EnforceItemAttributes",
    "Quests.EnableQuestTracker", "QuestPOI.Enabled", "Quests.IgnoreRaid", "Quests.IgnoreAutoAccept",
    "Quests.IgnoreAutoComplete", "Creature.RepositionAgainstNpcs", "LeaveGroupOnLogout.Enabled",
    "Instance.GMSummonPlayer", "Instance.IgnoreLevel", "Instance.IgnoreRaid",
    "Instance.SharedNormalHeroicId", "JoinBGAndLFG.Enable", "LFG.MailItemOnFullInventory",
    "LFG.Location.All", "DungeonFinder.CastDeserter", "DungeonFinder.AllowCompleted",
    "DungeonAccessRequirements.PortalAvgIlevelCheck", "Wintergrasp.Enable",
    "Wintergrasp.KickVoAPlayers", "Battleground.CastDeserter", "Battleground.QueueAnnouncer.Enable",
    "Battleground.QueueAnnouncer.Timed", "Battleground.GiveXPForKills",
    "Battleground.StoreStatistics.Enable", "Battleground.TrackDeserters.Enable",
    "Battleground.DisableQuestShareInBG", "Battleground.DisableReadyCheckInBG",
    "Arena.AutoDistributePoints", "Arena.QueueAnnouncer.Enable", "Guild.AllowMultipleGuildMaster",
    "IsContinentTransport.Enabled", "IsPreloadedContinentTransport.Enabled", "AddonChannel",
    "ChatFakeMessagePreventing", "Chat.MuteFirstLogin", "Channel.RestrictedLfg",
    "Channel.SilentlyGMJoin", "PreserveCustomChannels", "AllowTwoSide.Accounts",
    "AllowTwoSide.Interaction.Calendar", "AllowTwoSide.Interaction.Chat",
    "AllowTwoSide.Interaction.Channel", "AllowTwoSide.Interaction.Group",
    "AllowTwoSide.Interaction.Guild", "AllowTwoSide.Interaction.Arena",
    "AllowTwoSide.Interaction.Auction", "TalentsInspecting", "Event.Announce",
    "PlayerDump.DisallowPaths", "PlayerDump.DisallowOverwrite", "WipeGunshipBlizzlike.Enable",
    "Minigob.Manabonk.Enable", "Calculate.Creature.Zone.Area.Data",
    "Calculate.Gameoject.Zone.Area.Data", "MunchingBlizzlike.Enabled", "Daze.Enabled",
    "InfiniteAmmo.Enabled", "Debug.Battleground", "Debug.Arena", "Debug.LFG",
    "Respawn.DynamicEscortNPC", "Respawn.ForceCompatibilityMode",
}

DIRECT_LABELS = {
    "MaxPingTime": "Datenbank-Ping-Intervall",
    "EnableProxyProtocol": "Proxy-Protokoll aktiv",
    "PidFile": "PID-Datei",
    "UseProcessors": "CPU-Kernmaske",
    "ProcessPriority": "Prozessprioritaet",
    "RealmsStateUpdateDelay": "Realmstatus-Aktualisierung",
    "WrongPass.MaxCount": "Falsches Passwort: maximale Versuche",
    "WrongPass.BanTime": "Falsches Passwort: Sperrdauer",
    "WrongPass.BanType": "Falsches Passwort: Sperrart",
    "WrongPass.Logging": "Falsche Passwoerter protokollieren",
    "BanExpiryCheckInterval": "Abgelaufene Sperren pruefen",
    "StrictVersionCheck": "Clientversion streng pruefen",
    "SourceDirectory": "Quellcode-Verzeichnis",
    "MySQLExecutable": "MySQL-Programm",
    "TempDir": "Temporaeres Verzeichnis",
    "IPLocationFile": "IP-Standortdatei",
    "AllowLoggingIPAddressesInDatabase": "IP-Adressen in der Datenbank loggen",
    "EnableTOTP": "Zwei-Faktor-Login aktiv",
    "TOTPMasterSecret": "TOTP-Hauptschluessel",
    "Console.Enable": "Serverkonsole aktiv",
    "BeepAtStart": "Signalton nach Start",
    "FlashAtStart": "Fenster blinkt nach Start",
    "ThreadPool": "Allgemeine Thread-Anzahl",
    "Compression": "Paket-Kompression",
    "PacketLogFile": "Paketlog-Datei",
    "RecordUpdateTimeDiffInterval": "Updatezeit-Logintervall",
    "MinRecordUpdateTimeDiff": "Mindestwert fuer Updatezeit-Log",
    "World.RealmAvailability": "Realm verfuegbar",
    "RealmZone": "Realm-Zone",
    "DBC.Locale": "DBC-Sprache",
    "ClientCacheVersion": "Clientcache-Version",
    "SessionAddDelay": "Sitzung hinzufuegen: Verzoegerung",
    "CloseIdleConnections": "Inaktive Verbindungen schliessen",
    "SocketTimeOutTime": "Socket-Timeout",
    "SocketTimeOutTimeActive": "Aktiver Socket-Timeout",
    "MaxOverspeedPings": "Maximale Overspeed-Pings",
    "DisconnectToleranceInterval": "Reconnect-Toleranz nach Disconnect",
    "EnableLoginAfterDC": "Login nach Verbindungsabbruch erlauben",
    "MinWorldUpdateTime": "Minimale Welt-Tickzeit",
    "UpdateUptimeInterval": "Uptime-Aktualisierung",
    "MaxCoreStuckTime": "Freeze-Erkennung",
    "SaveRespawnTimeImmediately": "Respawnzeit sofort speichern",
    "Server.LoginInfo": "Login-Info im Chat",
    "ShowKickInWorld": "Kick-Meldungen weltweit anzeigen",
    "ShowMuteInWorld": "Mute-Meldungen weltweit anzeigen",
    "ShowBanInWorld": "Bann-Meldungen weltweit anzeigen",
    "PreventAFKLogout": "AFK-Logout verhindern",
    "PacketSpoof.BanMode": "Paketfaelschung: Bannmodus",
    "PacketSpoof.BanDuration": "Paketfaelschung: Banndauer",
    "DetectPosCollision": "Positionskollision erkennen",
    "CheckGameObjectLoS": "Sichtlinie fuer Spielobjekte pruefen",
    "PreloadAllNonInstancedMapGrids": "Offene Kartenbereiche vorladen",
    "DontCacheRandomMovementPaths": "Zufaellige Bewegungswege nicht cachen",
    "DisableWaterBreath": "Unterwasseratmung deaktivieren",
    "AllFlightPaths": "Alle Flugpunkte freischalten",
    "InstantFlightPaths": "Flugreisen sofort abschliessen",
    "AlwaysMaxSkillForLevel": "Fertigkeiten immer auf Levelmaximum",
    "AlwaysMaxWeaponSkill": "Waffenfertigkeit immer maximal",
    "PlayerStart.AllReputation": "Start-Rufwerte vergeben",
    "PlayerStart.CustomSpells": "Eigene Startzauber vergeben",
    "PlayerStart.MapsExplored": "Karten fuer neue Charaktere aufdecken",
    "PlayerSave.Stats.SaveOnlyOnLogout": "Spielerstatistiken nur beim Ausloggen speichern",
    "ValidateSkillLearnedBySpells": "Skills gegen gelernte Zauber pruefen",
    "DeclinedNames": "Deklination von Namen aktiv",
    "StrictNames.Reserved": "Reservierte Namen streng pruefen",
    "StrictNames.Profanity": "Schimpfwoerter in Namen pruefen",
    "EnablePlayerSettings": "Spielereinstellungen speichern",
    "EnableLowLevelRegenBoost": "Regenerationsbonus fuer niedrige Level",
    "SpellQueue.Enabled": "Zauberwarteschlange aktiv",
    "SkillChance.MiningSteps": "Bergbau: Skill-Stufen nutzen",
    "SkillChance.SkinningSteps": "Kuerchnerei: Skill-Stufen nutzen",
    "OffhandCheckAtSpellUnlearn": "Nebenhand nach Zauberverlust pruefen",
    "Stats.Limits.Enable": "Wertelimits aktiv",
    "PvPToken.Enable": "PvP-Marken aktiv",
    "Death.Bones.World": "Knochen in der Welt erzeugen",
    "Death.Bones.BattlegroundOrArena": "Knochen in BG/Arena erzeugen",
    "ItemDelete.Vendor": "Haendleritems automatisch loeschen",
    "Creature.RepositionAgainstNpcs": "Kreaturen gegen NPCs neu positionieren",
    "LeaveGroupOnLogout.Enabled": "Gruppe beim Ausloggen verlassen",
    "Instance.GMSummonPlayer": "GM-Beschwoerung in Instanzen erlauben",
    "Instance.IgnoreLevel": "Instanz-Levelgrenzen ignorieren",
    "Instance.IgnoreRaid": "Raid-Bedingung fuer Instanzen ignorieren",
    "Instance.SharedNormalHeroicId": "Normale und heroische ID teilen",
    "JoinBGAndLFG.Enable": "BG und Dungeonfinder gleichzeitig erlauben",
    "LFG.MailItemOnFullInventory": "Dungeonfinder-Beute per Post senden",
    "LFG.Location.All": "Dungeonfinder von ueberall erlauben",
    "DungeonFinder.CastDeserter": "Dungeon-Deserteur anwenden",
    "DungeonFinder.AllowCompleted": "Abgeschlossene Dungeons erlauben",
    "DungeonAccessRequirements.PortalAvgIlevelCheck": "Portalzugang: Gegenstandsstufe pruefen",
    "DungeonAccessRequirements.PrintMode": "Dungeonzugang: Ausgabemodus",
    "DungeonAccessRequirements.OptionalStringID": "Dungeonzugang: optionaler Text",
    "Wintergrasp.Enable": "Tausendwinter aktiv",
    "Wintergrasp.KickVoAPlayers": "AK-Spieler nach Tausendwinter kicken",
    "Battleground.CastDeserter": "Schlachtfeld-Deserteur anwenden",
    "Battleground.QueueAnnouncer.Enable": "Schlachtfeld-Warteschlange ansagen",
    "Battleground.QueueAnnouncer.Timed": "Schlachtfeld-Ansage wiederholen",
    "Battleground.GiveXPForKills": "XP fuer Kills im Schlachtfeld",
    "Battleground.StoreStatistics.Enable": "Schlachtfeldstatistiken speichern",
    "Battleground.TrackDeserters.Enable": "Schlachtfeld-Deserteure verfolgen",
    "Battleground.DisableQuestShareInBG": "Questteilen im Schlachtfeld sperren",
    "Battleground.DisableReadyCheckInBG": "Bereitschaftscheck im Schlachtfeld sperren",
    "Arena.AutoDistributePoints": "Arenapunkte automatisch verteilen",
    "Arena.QueueAnnouncer.Enable": "Arena-Warteschlange ansagen",
    "Guild.AllowMultipleGuildMaster": "Mehrere Gildenmeister erlauben",
    "AddonChannel": "Addon-Kanal erlauben",
    "ChatFakeMessagePreventing": "Gefakte Chatnachrichten verhindern",
    "Chat.MuteFirstLogin": "Neue Accounts beim ersten Login stummschalten",
    "Channel.RestrictedLfg": "SucheNachGruppe-Kanal beschraenken",
    "Channel.SilentlyGMJoin": "GM-Kanalbeitritt verbergen",
    "PreserveCustomChannels": "Eigene Kanaele erhalten",
    "TalentsInspecting": "Talente beim Inspizieren anzeigen",
    "Event.Announce": "Events im Chat ankuendigen",
    "PlayerDump.DisallowPaths": "PlayerDump-Pfade verbieten",
    "PlayerDump.DisallowOverwrite": "PlayerDump-Ueberschreiben verbieten",
    "WipeGunshipBlizzlike.Enable": "Kanonenboot-Wipe blizzlike",
    "Minigob.Manabonk.Enable": "Minigob Manabonk aktiv",
    "Calculate.Creature.Zone.Area.Data": "Kreatur-Zonen-/Gebietsdaten berechnen",
    "Calculate.Gameoject.Zone.Area.Data": "Spielobjekt-Zonen-/Gebietsdaten berechnen",
    "MunchingBlizzlike.Enabled": "Aura-Munching blizzlike",
    "Daze.Enabled": "Benommenheit aktiv",
    "InfiniteAmmo.Enabled": "Unendliche Munition aktiv",
}

DIRECT_DESCRIPTIONS = {
    "MaxPingTime": "Intervall, in dem der Server seine Datenbankverbindung aktiv haelt. Ein kleinerer Wert erkennt Verbindungsprobleme schneller, erzeugt aber mehr regelmaessige Datenbankabfragen. Ein zu hoher Wert kann dazu fuehren, dass kaputte Verbindungen spaeter bemerkt werden.",
    "EnableProxyProtocol": "Aktiviert das PROXY-Protokoll fuer vorgeschaltete Loadbalancer oder Reverse Proxies. Nur einschalten, wenn ein Proxy dieses Protokoll wirklich sendet; sonst koennen normale Verbindungen fehlschlagen.",
    "PidFile": "Pfad zur Datei, in die der Prozess seine Prozess-ID schreibt. Das hilft Init-Systemen und Wartungsskripten. Ein falscher oder nicht beschreibbarer Pfad kann Start-/Stop-Skripte stoeren.",
    "UseProcessors": "CPU-Kernmaske fuer den Serverprozess. Damit kann der Prozess auf bestimmte Kerne begrenzt werden. Auf normalen Servern meist unveraendert lassen; falsche Masken koennen Leistung verschlechtern.",
    "ProcessPriority": "Prioritaet des Serverprozesses im Betriebssystem. Hoehere Prioritaet kann den Worldserver bevorzugen, kann aber andere Dienste auf dem Container ausbremsen.",
    "WrongPass.MaxCount": "Anzahl falscher Loginversuche, bevor eine Sperraktion greift. Niedriger schuetzt staerker gegen Brute-Force, kann echte Spieler bei Tippfehlern aber schneller aussperren.",
    "WrongPass.BanTime": "Dauer der Sperre nach zu vielen falschen Passwoertern. Hoeher bremst Angriffe staerker, kann betroffene Spieler aber laenger blockieren.",
    "WrongPass.BanType": "Legt fest, ob nach falschen Passwoertern Account oder IP gesperrt werden. IP-Sperren treffen bei gemeinsamem Netzwerk eventuell mehrere Spieler.",
    "WrongPass.Logging": "Schreibt falsche Loginversuche ins Log. Hilft beim Erkennen von Angriffen oder vertippten Accounts, erzeugt aber mehr Logeintraege.",
    "StrictVersionCheck": "Prueft die Clientversion strenger. Aktiviert ist sicherer und sauberer fuer 3.3.5a; falsch konfigurierte Clients kommen dann nicht mehr hinein.",
    "AllowLoggingIPAddressesInDatabase": "Speichert IP-Adressen in der Datenbank. Hilft bei Administration und Missbrauchsanalyse, ist aber datenschutzrelevant.",
    "EnableTOTP": "Aktiviert Zwei-Faktor-Login ueber TOTP, sofern Accounts und Clientprozess dies unterstuetzen. Erhoeht Sicherheit, macht Login aber anspruchsvoller.",
    "TOTPMasterSecret": "Hauptschluessel fuer TOTP-Funktionen. Sehr sensibel: nicht teilen, nicht committen und nur aendern, wenn du weisst, wie bestehende TOTP-Daten betroffen sind.",
    "Console.Enable": "Aktiviert die lokale Serverkonsole. Nuetzlich fuer direkte Administration am Serverprozess; auf Headless-Diensten meist nur relevant, wenn die Konsole gezielt genutzt wird.",
    "Compression": "Kompressionsstufe fuer Netzwerkpakete. Hoehere Werte sparen Bandbreite, koennen aber CPU kosten. Zu niedrige Werte sind leichter fuer CPU, brauchen mehr Netzwerk.",
    "PacketLogFile": "Datei fuer Paketmitschnitte. Nur zur Fehlersuche aktiv nutzen, da Paketlogs sehr gross werden und sensible Spiel-/Accountablaeufe enthalten koennen.",
    "World.RealmAvailability": "Steuert, ob der Realm als verfuegbar gemeldet wird. Deaktiviert kann Spieler am Betreten hindern oder den Realm als nicht verfuegbar erscheinen lassen.",
    "RealmZone": "Region/Zeitzonenkennung des Realms fuer Client- und Realmlistenverhalten. Falsch gesetzte Werte sind meist nicht kritisch, koennen aber Anzeige und Sortierung beeinflussen.",
    "DBC.Locale": "Sprache/Locale fuer DBC-Daten. Beeinflusst, welche lokalisierten Clientdaten der Server nutzt. Falsch gesetzt koennen Namen oder Texte ungewohnt erscheinen.",
    "ClientCacheVersion": "Version fuer den Clientcache. Erhoehen zwingt Clients indirekt dazu, Cache-Daten neu zu laden. Praktisch nach Datenbank-/DBC-Aenderungen, aber nicht dauernd noetig.",
    "CloseIdleConnections": "Schliesst inaktive Datenbank- oder Netzwerkverbindungen. Aktiviert hilft gegen haengende Verbindungen; zu aggressiv kann bei kurzer Inaktivitaet mehr Reconnects erzeugen.",
    "EnableLoginAfterDC": "Erlaubt schnelleren Login nach Verbindungsabbruch. Komfortabel fuer Spieler mit instabiler Verbindung; zu locker kann Ghost-Session-Probleme kaschieren.",
    "MaxCoreStuckTime": "Zeitgrenze fuer die Erkennung eines haengenden Serverkerns. Ist der Worldserver laenger blockiert, kann dies Diagnose oder Schutzreaktionen ausloesen.",
    "SaveRespawnTimeImmediately": "Speichert Respawnzeiten sofort nach Aenderung. Sicherer bei Abstuerzen, erzeugt aber mehr Datenbankzugriffe bei vielen Kills oder dynamischem Respawn.",
    "PreventAFKLogout": "Verhindert automatisches Ausloggen in AFK-Situationen. Bequem fuer private Server, kann aber viele inaktive Charaktere online halten.",
    "DetectPosCollision": "Prueft Positionskollisionen in der Welt. Aktiviert ist genauer gegen falsche Positionen; deaktiviert spart etwas Rechenarbeit, kann aber Positionierungsfehler zulassen.",
    "CheckGameObjectLoS": "Prueft Sichtlinie zu Spielobjekten. Aktiviert verhindert Interaktion durch Waende oder Geometrie; deaktiviert ist weniger realistisch, aber etwas leichter.",
    "PreloadAllNonInstancedMapGrids": "Laedt offene Kartenbereiche beim Start vor. Das kann Ruckler beim ersten Betreten reduzieren, erhoeht aber Startzeit und RAM-Verbrauch.",
    "DontCacheRandomMovementPaths": "Speichert zufaellige Bewegungswege nicht zwischen. Spart Cache-Speicher, kann aber mehr Pfadberechnung erzeugen.",
    "DisableWaterBreath": "Schaltet Unterwasseratmungslogik ab. Nur fuer Sonderregeln verwenden; normalerweise sollten Spieler unter Wasser Luft verbrauchen.",
    "AllFlightPaths": "Schaltet alle Flugpunkte fuer Spieler frei. Sehr komfortabel, aber nicht blizzlike und nimmt Entdeckungs-/Reisefortschritt aus dem Spiel.",
    "InstantFlightPaths": "Laesst Flugreisen sofort enden. Spart Reisezeit, veraendert aber Weltgefuehl und kann Transportzeit als Spielmechanik entfernen.",
    "AlwaysMaxSkillForLevel": "Setzt Fertigkeiten passend zum Charakterlevel immer auf Maximum. Macht Waffen-/Berufsskillen einfacher, entfernt aber Progression in diesen Bereichen.",
    "AlwaysMaxWeaponSkill": "Haelt Waffenfertigkeiten immer maximal. Spieler muessen neue Waffenarten nicht mehr trainieren, wodurch Trefferprobleme beim Waffenwechsel verschwinden.",
    "PlayerStart.MapsExplored": "Neue Charaktere starten mit aufgedeckten Karten. Praktisch fuer Komfortserver, nimmt aber Erkundung und Entdeckungs-XP aus dem Startspiel.",
    "InstantLogout": "Spieler loggen sofort aus, ohne die normale Wartezeit. Komfortabel, kann aber genutzt werden, um Gefahr schneller zu verlassen.",
    "PlayerSave.Stats.SaveOnlyOnLogout": "Speichert bestimmte Statistiken nur beim Ausloggen. Reduziert laufende Datenbanklast, kann aber bei Absturz neuere Statistikdaten verlieren.",
    "EnableLowLevelRegenBoost": "Erhoeht Regeneration fuer niedrige Level. Macht den Einstieg leichter und reduziert Pausen nach Kaempfen.",
    "SpellQueue.Enabled": "Aktiviert die Zauberwarteschlange. Spieler koennen naechste Zauber kurz vor Ende des aktuellen Zaubers einreihen; das fuehlt sich fluessiger und moderner an.",
    "Stats.Limits.Enable": "Aktiviert Limits fuer Charakterwerte. Schutz gegen unplausible Werte; bei Custom-Items oder stark veraenderten Rates kann es Werte begrenzen.",
    "PvPToken.Enable": "Aktiviert ein PvP-Marken-/Token-System, sofern Datenbank und Scripts es nutzen. Beeinflusst Belohnungen durch PvP-Kills.",
    "Death.Bones.World": "Erzeugt Knochen/Leichenmarker nach Spielertod in der offenen Welt. Sichtbares Todesfeedback, aber mehr Objekte in stark bespielten Gebieten.",
    "Death.Bones.BattlegroundOrArena": "Erzeugt Knochen/Leichenmarker in Schlachtfeldern oder Arena. Mehr Optik, aber in PvP-Matches eventuell unruhiger.",
    "ItemDelete.Vendor": "Erlaubt automatisches Entfernen bestimmter Haendleritems. Vorsichtig verwenden, da falsche Regeln gewuenschte Gegenstaende entfernen koennen.",
    "Creature.RepositionAgainstNpcs": "Kreaturen positionieren sich im Kampf gegen NPCs genauer neu. Kann NPC-Kaempfe natuerlicher machen, kostet aber etwas Bewegungslogik.",
    "LeaveGroupOnLogout.Enabled": "Charaktere verlassen Gruppen beim Ausloggen. Das verhindert haengende Gruppen, kann aber Spieler aus geplanten Gruppen entfernen.",
    "Instance.GMSummonPlayer": "Erlaubt GM-Beschwoerung in Instanzen. Praktisch fuer Support, kann aber Instanzregeln umgehen.",
    "Instance.IgnoreLevel": "Ignoriert Levelanforderungen fuer Instanzen. Spieler koennen Inhalte frueher betreten; Progression und Schwierigkeit werden dadurch veraendert.",
    "Instance.IgnoreRaid": "Ignoriert Raid-Anforderungen fuer Instanzen. Praktisch fuer Tests oder kleine private Gruppen, aber weniger blizzlike.",
    "JoinBGAndLFG.Enable": "Erlaubt gleichzeitige Anmeldung fuer Schlachtfeld und Dungeonfinder. Komfortabler, kann aber Rollen-/Queue-Verhalten unuebersichtlicher machen.",
    "DungeonFinder.CastDeserter": "Vergibt den Deserteur-Debuff bei Dungeonfinder-Abbruch. Aktiviert verhindert haeufiges Verlassen, deaktiviert ist lockerer fuer private Gruppen.",
    "DungeonFinder.AllowCompleted": "Erlaubt Dungeonfinder fuer bereits abgeschlossene Inhalte. Praktisch zum Wiederholen, kann aber Belohnungslogik beeinflussen.",
    "Wintergrasp.Enable": "Aktiviert Tausendwinter. Spieler koennen das PvP-Event nutzen, sofern Karten- und Datenbankdaten stimmen.",
    "Battleground.GiveXPForKills": "Gewaehrt Erfahrung fuer Kills im Schlachtfeld. Macht PvP-Leveln moeglich, kann Leveltempo im PvP stark erhoehen.",
    "Arena.AutoDistributePoints": "Verteilt Arenapunkte automatisch. Komfortabel fuer Wochenabschluss, muss aber zum gewuenschten PvP-Rhythmus passen.",
    "Guild.AllowMultipleGuildMaster": "Erlaubt mehrere Gildenmeister. Administrativ flexibel, aber nicht blizzlike und kann Verantwortlichkeiten verwirren.",
    "AddonChannel": "Erlaubt Addon-Kommunikation ueber den Addon-Kanal. Viele Addons brauchen das; deaktiviert kann Addonfunktionen brechen.",
    "ChatFakeMessagePreventing": "Schutz gegen gefaelschte Chatnachrichten. Aktiviert ist sinnvoll gegen Missbrauch; deaktiviert nur fuer Tests.",
    "Channel.RestrictedLfg": "Beschraenkt den SucheNachGruppe-Kanal. Hilft gegen Spam und falsche Nutzung, kann aber legitime Kommunikation einschraenken.",
    "PreserveCustomChannels": "Erhaelt eigene Chatkanaele ueber Sitzungen hinweg. Komfortabel fuer Spielergruppen, speichert aber mehr Kanalzustand.",
    "TalentsInspecting": "Erlaubt das Anzeigen fremder Talente beim Inspizieren. Komfortabel fuer Gruppen und Raids, weniger privat.",
    "Event.Announce": "Kuendigt Serverevents im Chat an. Spieler sehen Start/Ende von Events besser; deaktiviert wirkt ruhiger.",
    "Calculate.Creature.Zone.Area.Data": "Berechnet Kreatur-Zonen-/Gebietsdaten neu. Nur fuer Wartung oder Datenkorrektur aktivieren, da der Start laenger dauern kann.",
    "Calculate.Gameoject.Zone.Area.Data": "Berechnet Spielobjekt-Zonen-/Gebietsdaten neu. Nur fuer Wartung oder Datenkorrektur aktivieren, da der Start laenger dauern kann.",
    "MunchingBlizzlike.Enabled": "Steuert blizzlike Aura-Munching. Aktiviert kann historisches WotLK-Verhalten nachbilden; deaktiviert fuehlt sich fuer manche Klassen moderner an.",
    "Daze.Enabled": "Aktiviert Benommenheit, wenn Spieler von hinten getroffen werden. Blizzlike und gefaehrlicher beim Reiten durch Gegnergruppen.",
    "InfiniteAmmo.Enabled": "Aktiviert unendliche Munition. Komfortabel fuer Jaeger, entfernt aber Munitionsverwaltung und entsprechende Wirtschaft.",
}

META = {
    "RealmID": ("Realm-ID", "Muss zur Realm-ID in der Auth-Datenbank passen. Wenn dieser Wert nicht stimmt, zeigt der Authserver den Realm falsch an oder der Client kann sich nicht korrekt verbinden."),
    "WorldServerPort": ("Worldserver-Port", "Port fuer den Spielwelt-Zugang. Spieler verbinden nach dem Login auf diesen Port. Aenderungen brauchen Firewall-Anpassung und Realm-Konfiguration."),
    "RealmServerPort": ("Authserver-Port", "Port fuer den Loginserver. Der WoW-Client erwartet normalerweise 3724. Nur aendern, wenn du bewusst einen anderen Login-Port nutzt."),
    "BindIP": ("Bind-IP", "Legt fest, auf welcher Netzwerkadresse der Dienst lauscht. 0.0.0.0 bedeutet alle Interfaces. Eine konkrete IP kann sicherer sein, kann aber Verbindungen blockieren, wenn sie falsch ist."),
    "PlayerLimit": ("Spielerlimit", "Maximale Anzahl gleichzeitiger Spieler auf dem Realm. Bei privaten Servern meist hoch genug lassen. Ein niedriger Wert sperrt weitere Logins, sobald die Grenze erreicht ist."),
    "GameType": ("Realm-Typ", "Bestimmt die Anzeige und Regeln des Realms, zum Beispiel Normal, PvP oder RP. Spieler sehen diesen Typ in der Realmliste; je nach Wert gelten andere PvP-Grundregeln."),
    "Expansion": ("Erweiterungsstand", "Legt fest, welche Erweiterung der Realm anbietet. Fuer WoW 3.3.5a normalerweise 2 fuer Wrath of the Lich King."),
    "MaxPlayerLevel": ("Maximales Spielerlevel", "Obergrenze fuer Charakterlevel. Fuer 3.3.5a normalerweise 80. Hoehere Werte koennen Skills, Quests und Balance brechen."),
    "StartPlayerLevel": ("Startlevel normaler Charaktere", "Level neuer Charaktere. 1 ist blizzlike. Hoehere Werte machen Twinks schneller spielbar, ueberspringen aber Startgebiete und fruehe Quests."),
    "StartHeroicPlayerLevel": ("Startlevel Todesritter", "Startlevel fuer heroische Klassen wie Todesritter. Fuer WotLK normalerweise 55."),
    "StartPlayerMoney": ("Startgeld normaler Charaktere", "Kupferbetrag fuer neue Charaktere. 10000 entspricht 1 Gold. Zu viel Startgeld entwertet fruehe Wirtschaft und Berufe."),
    "StartHeroicPlayerMoney": ("Startgeld Todesritter", "Kupferbetrag fuer neue Todesritter. 2000 entspricht 20 Silber."),
    "CharactersPerRealm": ("Charaktere pro Realm", "Maximale Anzahl Charaktere pro Account auf diesem Realm. Im Client wirkt sich das direkt auf die Charakterliste aus."),
    "CharactersPerAccount": ("Charaktere pro Account", "Globale Charaktergrenze pro Account. Wenn niedriger als pro Realm, begrenzt dieser Wert zuerst."),
    "InstantLogout": ("Sofort ausloggen", "Wenn aktiv, loggen Spieler ohne 20-Sekunden-Wartezeit aus. Komfortabel fuer private Server, aber weniger blizzlike und kann Flucht vor Gefahr erleichtern."),
    "PlayerSaveInterval": ("Speicherintervall Spieler", "Intervall in Millisekunden, in dem Charakterdaten gespeichert werden. Kleiner senkt Datenverlust bei Absturz, erzeugt aber mehr Datenbanklast."),
    "Rate.XP.Kill": ("XP durch Gegner", "Multiplikator fuer Erfahrung durch Kills. 2 bedeutet doppelte Kill-XP. Macht Leveln schneller, beeinflusst aber Questfluss und Gebietsdauer."),
    "Rate.XP.Quest": ("XP durch Quests", "Multiplikator fuer Quest-Erfahrung. Der wichtigste Regler fuer Levelgeschwindigkeit, wenn Spieler normal questen."),
    "Rate.XP.Explore": ("XP durch Erkunden", "Multiplikator fuer Entdeckungs-XP beim Betreten neuer Gebiete."),
    "Rate.Reputation.Gain": ("Rufgewinn", "Multiplikator fuer allgemeinen Rufgewinn. Hoehere Werte verkuerzen Fraktions-Grinds deutlich."),
    "Rate.Honor": ("Ehre-Rate", "Multiplikator fuer Ehrenpunkte. Hoehere Werte beschleunigen PvP-Ausrüstung."),
    "Rate.Drop.Money": ("Gold-/Geld-Drop", "Multiplikator fuer Geld von Kreaturen. Hoehere Werte bringen mehr Gold in die Wirtschaft und koennen Preise steigen lassen."),
    "Rate.Drop.Item.Normal": ("Normale Itemdrops", "Drop-Multiplikator fuer normale Items. Hoehere Werte fuellen Taschen schneller und versorgen AH/Verzauberung staerker."),
    "Rate.Drop.Item.Uncommon": ("Gruene Itemdrops", "Drop-Multiplikator fuer ungewoehnliche Items. Beeinflusst Twink-Ausrüstung, Entzauberung und Auktionshaus stark."),
    "Rate.Drop.Item.Rare": ("Blaue Itemdrops", "Drop-Multiplikator fuer seltene Items. Zu hohe Werte machen Dungeon- und Rare-Loot weniger besonders."),
    "Rate.Drop.Item.Epic": ("Epische Itemdrops", "Drop-Multiplikator fuer epische Items. Sehr vorsichtig aendern, da dies Progression und Wirtschaft massiv beeinflusst."),
    "Rate.Creature.Normal.HP": ("Kreaturen-Leben normal", "Multiplikator fuer Lebenspunkte normaler Kreaturen. Hoeher macht die Welt zaeher, niedriger macht Solo-Leveln einfacher."),
    "Rate.Creature.Normal.Damage": ("Kreaturen-Schaden normal", "Multiplikator fuer Schaden normaler Kreaturen. Niedriger macht die offene Welt entspannter, hoeher macht sie gefaehrlicher."),
    "Rate.Creature.Elite.Elite.HP": ("Elite-Leben", "Multiplikator fuer Elite-Gegner. Beeinflusst Gruppenquests und Dungeons spuerbar."),
    "Rate.Creature.Elite.Elite.Damage": ("Elite-Schaden", "Multiplikator fuer Elite-Schaden. Zu hoch macht Gruppencontent schnell frustrierend."),
    "Corpse.Decay.NORMAL": ("Leichnam-Dauer: normale Gegner", "Zeit in Sekunden, wie lange der Leichnam eines normalen getöteten Gegners in der Welt liegen bleibt. Danach verschwindet er optisch aus dem Spiel. Höher wirkt natürlicher und gibt mehr Zeit zum Plündern; sehr hohe Werte können in stark bespielten Gebieten mehr Objekte sichtbar halten."),
    "Corpse.Decay.RARE": ("Leichnam-Dauer: seltene Gegner", "Zeit in Sekunden, wie lange der Leichnam eines seltenen Gegners liegen bleibt. Seltene Gegner bleiben meist länger sichtbar, damit Spieler den Kill und die Beute nicht sofort verlieren."),
    "Corpse.Decay.ELITE": ("Leichnam-Dauer: Elite-Gegner", "Zeit in Sekunden, wie lange Elite-Gegner nach dem Tod sichtbar bleiben. Betrifft viele Gruppen- und Dungeon-Gegner. Höhere Werte geben Gruppen mehr Ruhe beim Plündern."),
    "Corpse.Decay.RAREELITE": ("Leichnam-Dauer: seltene Elite-Gegner", "Zeit in Sekunden, wie lange seltene Elite-Gegner nach dem Tod sichtbar bleiben. Diese Gegner sind besonderer als normale Mobs, deshalb ist ein längerer Wert meistens sinnvoll."),
    "Corpse.Decay.WORLDBOSS": ("Leichnam-Dauer: Weltbosse", "Zeit in Sekunden, wie lange ein Weltboss-Leichnam liegen bleibt. Lange Zeiten sind hier normal, damit Spieler den Kill sehen, Beute verteilen und Screenshots machen können."),
    "Rate.Corpse.Decay.Looted": ("Leichnam-Dauer nach dem Plündern", "Multiplikator für die verbleibende Leichnam-Zeit, nachdem ein Gegner geplündert wurde. 0.5 bedeutet: geplünderte Leichname verschwinden etwa doppelt so schnell. Höher lässt geplünderte Körper länger liegen, niedriger räumt die Welt schneller auf."),
    "DBC.EnforceItemAttributes": ("Item-Werte aus DBC erzwingen", "Legt fest, ob der Worldserver Item-Attribute aus den Client-DBC-Dateien streng gegen die Datenbankwerte prüft und erzwingt. Aktiviert sorgt für mehr Konsistenz mit dem Client und verhindert unpassende Itemwerte; deaktiviert lässt Datenbank-Anpassungen freier wirken. Falsch gesetzte Werte können dazu führen, dass selbst bearbeitete Items anders wirken als erwartet."),
    "Quests.EnableQuestTracker": ("Questfortschritt verfolgen", "Aktiviert die serverseitige Questverfolgung. Spieler sehen dadurch Questfortschritte zuverlässiger, zum Beispiel Zähler für getötete Gegner oder gesammelte Gegenstände. Deaktiviert kann die Anzeige weniger komfortabel sein, spart aber etwas Logik."),
    "QuestPOI.Enabled": ("Questziele auf Karte anzeigen", "Aktiviert Quest-POI-Daten für die Kartenanzeige. Spieler sehen Questbereiche und Ziele besser auf Karte oder Minimap, sofern der Client und die Datenbank passende Daten haben. Deaktiviert wirkt das Questen klassischer, aber weniger komfortabel."),
    "Quests.LowLevelHideDiff": ("Niedrige Quests ausblenden ab Levelabstand", "Bestimmt, ab welchem Levelabstand niedrige Quests für Spieler als zu niedrig behandelt und weniger prominent angezeigt werden. Höhere Werte zeigen länger alte Quests; niedrigere Werte räumen die Questanzeige früher auf."),
    "Quests.HighLevelHideDiff": ("Hohe Quests ausblenden ab Levelabstand", "Bestimmt, ab welchem Levelabstand zu hohe Quests ausgeblendet oder als nicht passend behandelt werden. Höhere Werte zeigen Spielern früher schwere Quests; niedrigere Werte halten die Questanzeige stärker am aktuellen Levelbereich."),
    "Quests.IgnoreRaid": ("Raid-Bedingung für Quests ignorieren", "Wenn aktiviert, können Questregeln rund um Raids lockerer behandelt werden. Spieler können dadurch bestimmte Questbedingungen auch erfüllen, wenn die normale Raid-Einschränkung sonst greifen würde. Nur aktivieren, wenn du bewusst weniger blizzlike Questregeln willst."),
    "Quests.IgnoreAutoAccept": ("Automatische Questannahme ignorieren", "Steuert, ob automatische Questannahme aus den Daten ignoriert wird. Aktiviert verhindert, dass bestimmte Quests automatisch angenommen werden; deaktiviert folgt stärker den Datenbankvorgaben."),
    "Quests.IgnoreAutoComplete": ("Automatischen Questabschluss ignorieren", "Steuert, ob automatische Questabschlüsse aus den Daten ignoriert werden. Aktiviert verhindert automatische Abschlüsse; deaktiviert lässt entsprechend konfigurierte Quests automatisch fertig werden."),
    "ActivateWeather": ("Wetter aktiv", "Aktiviert dynamisches Wetter. Spieler sehen Regen, Schnee oder Sandsturm je nach Zone. Aus spart etwas Logik, macht die Welt aber statischer."),
    "ChangeWeatherInterval": ("Wetterwechsel-Intervall", "Zeit in Millisekunden zwischen Wetter-Aktualisierungen. Niedriger wirkt lebendiger, kann aber haeufige Wetterwechsel erzeugen."),
    "AllowTickets": ("Tickets erlauben", "Aktiviert das GM-Ticketsystem. Spieler koennen Hilfeanfragen erstellen; GMs sehen und bearbeiten sie ingame."),
    "GM.Visible": ("GM-Sichtbarkeit", "Steuert, ob GMs sichtbar sind. Je nach Wert bleiben GMs fuer normale Spieler sichtbar oder automatisch verborgen."),
    "GM.Chat": ("GM-Chatmodus", "Steuert GM-Chatkennzeichnung und Sichtbarkeit. Falsch gesetzt kann GM-Aktivitaet fuer Spieler ungewohnt sichtbar oder unsichtbar machen."),
    "GM.StartLevel": ("GM-Startlevel", "Startlevel fuer neu erstellte GM-Charaktere, falls diese Sonderbehandlung aktiv ist."),
    "SOAP.Enabled": ("SOAP aktiv", "Aktiviert die Remote-Schnittstelle fuer Webpanel-GM-Befehle. Ohne SOAP funktionieren viele Webpanel-Aktionen nicht direkt."),
    "SOAP.Port": ("SOAP-Port", "Port der SOAP-Schnittstelle. Muss frei sein und zum Webpanel passen. Beim Normal-Realm nutzt du derzeit 7878."),
    "SOAP.IP": ("SOAP-IP", "Adresse, auf der SOAP lauscht. 0.0.0.0 ist bequem, aber offener. In produktiven Umgebungen besser firewallen."),
    "Ra.Enable": ("Remote-Admin aktiv", "Aktiviert die telnetartige RA-Konsole. Nur nutzen, wenn abgesichert. SOAP ist fuer das Webpanel meist sauberer."),
    "Ra.Port": ("Remote-Admin-Port", "Port fuer RA. Muss firewallseitig geschuetzt werden, wenn RA aktiv ist."),
    "Warden.Enabled": ("Warden aktiv", "Aktiviert Client-Pruefungen gegen Manipulation. Kann helfen, Cheats zu erkennen, kann aber bei privaten Clients auch false positives verursachen."),
    "AutoBroadcast.On": ("AutoBroadcast aktiv", "Sendet automatische Servernachrichten im Chat. Gut fuer Hinweise, Regeln oder Neustartinformationen."),
    "AutoBroadcast.Timer": ("AutoBroadcast-Intervall", "Abstand zwischen automatischen Nachrichten in Millisekunden."),
    "Visibility.Distance.Continents": ("Sichtweite Kontinente", "Entfernung, in der Spieler, Kreaturen und Objekte in der offenen Welt sichtbar werden. Hoeher wirkt weiter, kostet aber Leistung."),
    "MoveMaps.Enable": ("MoveMaps aktiv", "Aktiviert Pfadfindung ueber mmaps. Kreaturen bewegen sich intelligenter; deaktiviert spart Ressourcen, macht NPC-Bewegung schlechter."),
    "vmap.enableLOS": ("VMap Sichtlinie", "Aktiviert Sichtlinienpruefung. Zauber und Sicht durch Waende werden realistischer berechnet."),
    "vmap.enableHeight": ("VMap Hoehenpruefung", "Aktiviert Hoeheninformationen. Wichtig fuer korrekte Positionen, LoS und Innen-/Aussenbereich."),
    "DataDir": ("Datenverzeichnis", "Pfad zu maps, vmaps, mmaps und dbc. Wenn falsch, startet der Worldserver nicht oder viele Weltfunktionen fehlen."),
    "LogsDir": ("Logverzeichnis", "Zielordner fuer Serverlogs. Hilft bei Fehleranalyse. Muss fuer den Serverprozess beschreibbar sein."),
}


def main_config_paths(cfg: dict) -> list[str]:
    base = cfg["server"]["normal_path"]
    return [f"{base}/etc/authserver.conf", f"{base}/etc/worldserver.conf"]


def load_main_configs(cfg: dict) -> tuple[list[dict], list[dict]]:
    ssh = SSHClient(cfg["server"])
    fields: list[dict] = []
    errors: list[dict] = []
    for path in main_config_paths(cfg):
        try:
            content = ssh.read_file(path)
            for option in scan_content(path, content):
                fields.append(enrich(option))
        except Exception as exc:
            errors.append({"file": path, "error": str(exc)})
    return fields, errors


def grouped_main_configs(fields: list[dict]) -> list[dict]:
    result = []
    for group_id, label in GROUP_ORDER:
        items = [field for field in fields if field["group"] == group_id]
        if not items:
            continue
        important = [field for field in items if field["important"]]
        advanced = [field for field in items if not field["important"]]
        result.append({"id": group_id, "label": label, "important": important, "advanced": advanced, "count": len(items)})
    return result


def summarize_main_configs(fields: list[dict]) -> list[str]:
    values = {field["key"]: field["value"] for field in fields}
    return [
        f"Realm-Port: {values.get('WorldServerPort', '?')} | Auth-Port: {values.get('RealmServerPort', '?')}",
        f"SOAP: {'aktiv' if values.get('SOAP.Enabled') == '1' else 'inaktiv'} auf Port {values.get('SOAP.Port', '?')}",
        f"Spielerlimit: {values.get('PlayerLimit', '?')} | Max-Level: {values.get('MaxPlayerLevel', '?')}",
        f"XP: Kill {values.get('Rate.XP.Kill', '?')}x, Quest {values.get('Rate.XP.Quest', '?')}x | Geld-Drop {values.get('Rate.Drop.Money', '?')}x",
        f"Wetter: {'aktiv' if values.get('ActivateWeather') == '1' else 'inaktiv'} | Tickets: {'aktiv' if values.get('AllowTickets') == '1' else 'inaktiv'}",
    ]


def save_main_configs(cfg: dict, values: dict[str, str]) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    ssh = SSHClient(cfg["server"])
    changed: list[tuple[str, str, str, str]] = []
    touched_files: list[str] = []
    for path in main_config_paths(cfg):
        content = ssh.read_file(path)
        fields = {option.key: option for option in scan_content(path, content)}
        file_changed = False
        for key, option in fields.items():
            form_key = form_field_name(path, key)
            if form_key not in values:
                continue
            new = str(values[form_key]).strip()
            if option.sensitive and new == "********":
                continue
            if new == option.value:
                continue
            content = update_value(content, key, new)
            changed.append((path, key, option.value, new))
            file_changed = True
        if file_changed:
            backup = f"{path}.wowpanel.bak"
            ssh.run(f"cp {shell_quote(path)} {shell_quote(backup)}", timeout=10)
            code, out, err = ssh.write_file(path, content)
            if code != 0:
                raise RuntimeError(err or out or f"Config konnte nicht geschrieben werden: {path}")
            touched_files.append(path)
    return changed, touched_files


def schedule_auth_restart(cfg: dict, delay: int) -> str:
    base = cfg["server"]["normal_path"]
    workdir = f"{base}/bin"
    script = "/tmp/wowpanel_restart_auth.sh"
    log = "/tmp/wowpanel_restart_auth.log"
    content = f"""#!/usr/bin/env bash
set -u
log={shell_quote(log)}
exec >>"$log" 2>&1
echo "[$(date -Is)] Authserver restart scheduled after {int(delay)} seconds"
sleep {int(delay)}
echo "[$(date -Is)] Stopping authserver in {workdir}"
for pid in $(pgrep -x authserver || true); do
  if [ "$(readlink -f /proc/$pid/cwd 2>/dev/null)" = {shell_quote(workdir)} ]; then
    echo "[$(date -Is)] TERM $pid"
    kill -TERM "$pid" || true
  fi
done
for i in $(seq 1 60); do
  remaining=""
  for pid in $(pgrep -x authserver || true); do
    if [ "$(readlink -f /proc/$pid/cwd 2>/dev/null)" = {shell_quote(workdir)} ]; then
      remaining="$remaining $pid"
    fi
  done
  [ -z "$remaining" ] && break
  sleep 1
done
for pid in $(pgrep -x authserver || true); do
  if [ "$(readlink -f /proc/$pid/cwd 2>/dev/null)" = {shell_quote(workdir)} ]; then
    echo "[$(date -Is)] KILL $pid after timeout"
    kill -KILL "$pid" || true
  fi
done
for i in $(seq 1 60); do
  ss -ltn "sport = :3724" | grep -q LISTEN || break
  echo "[$(date -Is)] Waiting for port 3724"
  sleep 1
done
sleep 2
cd {shell_quote(workdir)}
echo "[$(date -Is)] Starting ./authserver"
nohup ./authserver >/tmp/authserver_normal.wowpanel.log 2>&1 &
echo "[$(date -Is)] Started with pid $!"
"""
    marker = "WOWPANEL_AUTH_RESTART"
    command = f"cat > {shell_quote(script)} <<'{marker}'\n{content}{marker}\nchmod +x {shell_quote(script)}\n: > {shell_quote(log)}\nnohup bash {shell_quote(script)} >/dev/null 2>&1 &"
    code, out, err = SSHClient(cfg["server"]).run(command, timeout=10)
    if code != 0:
        raise RuntimeError(err or out or "Authserver-Neustart konnte nicht geplant werden.")
    return f"Authserver-Neustart in {delay} Sekunden geplant."


def form_field_name(path: str, key: str) -> str:
    return f"cfg::{path}::{key}"


def group_for(option: ConfigOption) -> str:
    key = option.key
    file_name = option.file.rsplit("/", 1)[-1]
    if key in IMPORTANT_KEYS:
        return "uebersicht"
    if file_name == "authserver.conf":
        if key.startswith("WrongPass") or key in {"StrictVersionCheck", "EnableTOTP", "TOTPMasterSecret", "BanExpiryCheckInterval", "AllowLoggingIPAddressesInDatabase"}:
            return "auth_login"
        if "Database" in key or key.startswith("Updates."):
            return "datenbanken"
        if key.startswith(("Appender.", "Logger.")) or "Log" in key:
            return "logs"
        if key.startswith("Network.") or key in {"UseProcessors", "ProcessPriority", "MaxPingTime", "PidFile", "RealmsStateUpdateDelay"}:
            return "leistung"
        return "auth_login"
    if key.endswith("DatabaseInfo") or "Database." in key or key.startswith("Updates."):
        return "datenbanken"
    if key.startswith(("SOAP.", "Ra.")) or key == "Console.Enable":
        return "remote"
    if key.startswith(("Network.", "ThreadPool")) or key in {"UseProcessors", "ProcessPriority", "Compression", "MaxPingTime", "MinWorldUpdateTime", "MaxCoreStuckTime"}:
        return "leistung"
    if key.startswith(("Log", "Logger.", "Appender.", "Metric.")) or key in {"PacketLogFile", "RecordUpdateTimeDiffInterval", "MinRecordUpdateTimeDiff"}:
        return "logs"
    if key.startswith("Warden."):
        return "warden"
    if key.startswith(("GM.", "AllowTickets", "LevelReq.Ticket", "DeletedCharacterTicketTrace", "AllowPlayerCommands", "Command.", "Die.Command")):
        return "gm"
    if key.startswith(("Character", "Characters", "CharDelete", "PlayerStart", "StartPlayer", "StartHeroic", "MinPlayerName", "MinPetName", "Strict", "DeclinedNames", "MaxPlayerLevel", "MinDualSpecLevel", "PlayerSave", "CleanCharacterDB", "ValidateSkill")):
        return "charaktere"
    if key.startswith(("Rate.XP.", "Rate.Reputation", "Rate.Honor", "Rate.Arena", "Rate.Talent", "Rate.Skill", "Skill", "LevelReq.Trade", "NoResetTalentsCost", "ToggleXP", "MaxHonor", "StartHonor", "MaxArena", "StartArena", "Achievement.", "MaxPrimaryTradeSkill")):
        return "raten"
    if key.startswith(("Visibility.", "Map", "MoveMaps", "vmap.", "DetectPosCollision", "CheckGameObjectLoS", "Preload", "DontCache", "ActivateWeather", "ChangeWeatherInterval", "DataDir", "DBC.")):
        return "welt"
    if key.startswith(("Rate.Creature", "Creature", "Npc", "MonsterSight", "WorldBoss", "Death.", "Durability", "Corpse.", "Pet.", "ListenRange")):
        return "kampf"
    if key.startswith(("Rate.Drop", "Rate.SellValue", "Rate.BuyValue", "Rate.RepairCost", "Item", "Loot", "Quests.", "Quest")):
        return "loot" if not key.startswith(("Quest", "Quests.")) else "welt"
    if key.startswith(("Instance.", "Dungeon", "LFG.", "JoinBGAndLFG", "Group.", "LeaveGroupOnLogout", "AccountInstancesPerHour")):
        return "gruppen"
    if key.startswith(("Battleground.", "Arena.", "Wintergrasp.", "OutdoorPvP", "FFAPvP", "PvPToken", "MaxAllowedMMRDrop")):
        return "pvp"
    if key.startswith(("Guild.", "Mail", "MinCharter", "StrictCharter", "MinPetition")):
        return "gilden"
    if key.startswith(("Realm", "World.", "GameType", "Expansion", "ClientCacheVersion", "Session", "SocketTimeOut", "CloseIdle", "EnableLoginAfterDC", "DisconnectTolerance", "PlayerLimit", "BirthdayTime")):
        return "realm"
    return "sonstige"


def enrich(option: ConfigOption) -> dict:
    data = asdict(option)
    label, description = describe(option)
    choices = choices_for(option)
    data["label"] = label
    data["description"] = description
    data["type"] = field_type(option, choices)
    data["choices"] = choices
    data["group"] = group_for(option)
    data["important"] = option.key in IMPORTANT_KEYS or option.key.startswith(("Rate.XP.", "Rate.Drop.Item."))
    data["form_name"] = form_field_name(option.file, option.key)
    data["file_label"] = option.file.rsplit("/", 1)[-1]
    data["requires_restart"] = "Worldserver" if data["file_label"] == "worldserver.conf" else "Authserver"
    return data


def field_type(option: ConfigOption, choices: list[dict]) -> str:
    if option.sensitive:
        return "password"
    if option.key.startswith("Corpse.Decay."):
        return "number"
    if option.key in FORCE_BOOLEAN_KEYS:
        return "boolean"
    if option.key in FORCE_ENUM_KEYS and choices:
        return "enum"
    if option.key in FORCE_NUMBER_KEYS:
        return "number"
    if choices and len(choices) > 1:
        return "enum"
    if option.type == "boolean":
        return "number"
    return option.type


def choices_for(option: ConfigOption) -> list[dict]:
    text = option.description or ""
    found: list[dict] = []
    for value, label in re.findall(r"(?m)(-?\d+)\s*-\s*\(([^)\n]+)\)", text):
        label = cleanup_choice(label)
        if not any(item["value"] == value for item in found):
            found.append({"value": value, "label": label})
    return found[:12]


def cleanup_choice(text: str) -> str:
    value = text.strip()
    replacements = [
        (r"\bDescription\b", "Beschreibung"),
        (r"\bDisabled\b", "deaktiviert"),
        (r"\bEnabled\b", "aktiviert"),
        (r"\bDisable\b", "deaktivieren"),
        (r"\bEnable\b", "aktivieren"),
        (r"\bNormal\b", "normal"),
        (r"\bHigh\b", "hoch"),
        (r"\bSpeed\b", "schnell"),
        (r"\bBest compression\b", "beste Komprimierung"),
        (r"\bBan IP\b", "IP bannen"),
        (r"\bBan Account\b", "Account bannen"),
        (r"\bSystem message\b", "Systemnachricht"),
        (r"\bArea trigger\b", "Gebiets-Ausloeser"),
        (r"\bBlizzlike\b", "blizzlike"),
        (r"\bplayers\b", "Spieler"),
        (r"\bplayer\b", "Spieler"),
        (r"\blogging only\b", "nur protokollieren"),
        (r"\bKick\b", "Kick"),
        (r"\bBan\b", "Bann"),
        (r"\bAnnounce\b", "Ankündigung"),
        (r"\bNotify\b", "Bildschirmmeldung"),
        (r"\bBoth\b", "beides"),
        (r"\bFaction\b", "Fraktion"),
        (r"\bprevent\b", "verhindern"),
    ]
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.I)
    return value


def describe(option: ConfigOption) -> tuple[str, str]:
    label = human_label(option.key)
    if option.key in META:
        return label, META[option.key][1]
    if option.key in DIRECT_DESCRIPTIONS:
        return label, DIRECT_DESCRIPTIONS[option.key]
    prefix_desc = description_by_prefix(option.key)
    if prefix_desc:
        return label, prefix_desc
    return label, description_by_group(option, label)


def description_by_group(option: ConfigOption, label: str) -> str:
    group = group_for(option)
    restart = "Worldserver" if option.file.endswith("worldserver.conf") else "Authserver"
    if group == "auth_login":
        return f"Authserver-Einstellung für {label}. Sie beeinflusst Login, Accountprüfung oder Schutz beim Verbinden. Zu strenge Werte können Spieler am Einloggen hindern; zu lockere Werte reduzieren Schutz und Kontrolle. Änderung wirkt nach Neustart des {restart}."
    if group == "datenbanken":
        return f"Datenbank-Einstellung für {label}. Sie beeinflusst Verbindungen, automatische Updates oder Datenbank-Threads. Höhere Threadwerte können mehr parallele Arbeit erlauben, erzeugen aber mehr Last; falsche Verbindungswerte verhindern den Serverstart. Änderung wirkt nach Neustart des {restart}."
    if group == "remote":
        return f"Remotezugriff-Einstellung für {label}. Sie beeinflusst Konsole, SOAP oder Remote-Admin. Falsche Werte können Webpanel-Befehle blockieren oder unnötig offene Verwaltungsports erzeugen. Nach Änderungen den betroffenen Dienst neu starten."
    if group == "leistung":
        return f"Leistungs- und Stabilitätswert für {label}. Höhere Werte bedeuten nicht automatisch besser: sie können mehr CPU, RAM oder Netzwerkpuffer nutzen. Zu niedrige Werte können Verzögerungen verursachen, zu hohe Werte unnötige Last. Änderung vorsichtig testen und Server neu starten."
    if group == "logs":
        return f"Protokollierungs- und Diagnosewert für {label}. Mehr Logging hilft bei Fehlersuche, kann aber größere Logdateien und etwas mehr Last erzeugen. Weniger Logging hält den Server ruhiger, erschwert aber spätere Fehleranalyse."
    if group == "realm":
        return f"Realm-, Client- oder Sitzungswert für {label}. Spieler bemerken solche Werte beim Verbinden, in der Realmliste, bei Verbindungsabbrüchen oder im allgemeinen Realmverhalten. Falsche Werte können Login, Cache oder Sitzungsstabilität stören."
    if group == "gm":
        return f"GM- und Support-Einstellung für {label}. Sie beeinflusst GM-Sichtbarkeit, Tickets, GM-Kommandos oder Supportfunktionen. Höhere Freigaben machen Administration komfortabler; zu offene Werte können normale Spielerfunktionen oder GM-Sichtbarkeit unbeabsichtigt verändern."
    if group == "charaktere":
        return f"Charakter-Einstellung für {label}. Spieler bemerken sie bei Charaktererstellung, Namen, Startwerten, Löschung oder beim Speichern von Charakterdaten. Zu großzügige Werte machen den Server komfortabler; zu strenge Werte können gewünschte Charaktere blockieren."
    if group == "raten":
        return f"Progressionswert für {label}. Er beeinflusst, wie schnell Spieler vorankommen, Punkte erhalten oder Skills steigern. Höhere Werte beschleunigen den Spielfortschritt; niedrigere Werte halten den Server näher an blizzlike Tempo."
    if group == "welt":
        return f"Welt- und Kartenwert für {label}. Spieler bemerken ihn bei Karte, Quests, Wetter, Sichtlinie, Bewegung oder Objektdarstellung. Höhere Komfortwerte machen die Welt lesbarer; strengere Werte sind näher an klassischem Verhalten oder sparen Leistung."
    if group == "kampf":
        return f"Kampf- oder Todesfolge für {label}. Sie beeinflusst Gegnerverhalten, Tod, Haltbarkeit, Sichtweite oder Kampfgefühl. Höhere Werte machen Kämpfe oft härter oder länger; niedrigere Werte machen Spiel und Farmen leichter."
    if group == "loot":
        return f"Beute-, Item- oder Wirtschaftswert für {label}. Spieler merken Änderungen beim Plündern, Verkaufen, Reparieren, Auktionshaus oder Itemverhalten. Höhere Werte können mehr Gold oder Items erzeugen und die Serverwirtschaft deutlich verändern."
    if group == "gruppen":
        return f"Gruppen-, Instanz- oder Dungeonfinderwert für {label}. Er beeinflusst Gruppenbildung, Instanzzugang, Resetzeiten, Dungeonfinder-Komfort oder Dungeonregeln. Änderungen wirken sich direkt auf Gruppencontent aus."
    if group == "pvp":
        return f"PvP-, Schlachtfeld- oder Arena-Regel für {label}. Sie beeinflusst Warteschlangen, Belohnungen, Punkte, Wertung oder PvP-Timer. Kleine Änderungen können PvP-Fortschritt und Balance stark verändern."
    if group == "gilden":
        return f"Gilden-, Post- oder Kommunikationswert für {label}. Spieler merken ihn bei Gildenbank, Gildenregeln, Postzustellung, Charter oder Kommunikation. Höhere Kosten oder strengere Limits bremsen Komfort; niedrigere Werte erleichtern Organisation."
    if group == "warden":
        return f"Warden-Schutzwert für {label}. Er beeinflusst Clientprüfungen und Reaktion auf auffällige Clients. Strengere Werte erhöhen Schutz, können aber auf privaten Clients eher Fehlalarme erzeugen."
    return f"Servereinstellung für {label}. Sie beeinflusst einen speziellen Bereich des Normal-Realms. Höhere Werte verstärken meist die jeweilige Wirkung, niedrigere Werte reduzieren sie oder schalten sie ab. Änderung mit Backup testen und nach dem Speichern den betroffenen Dienst neu starten."


def human_label(key: str) -> str:
    special = special_label(key)
    if special:
        return special
    parts = re.split(r"[._-]+", key)
    return " ".join(translate_label_part(part) for part in parts if part)


def special_label(key: str) -> str:
    if key in DIRECT_LABELS:
        return DIRECT_LABELS[key]
    if key in META:
        return META[key][0]
    if key.startswith("Rate.Creature."):
        parts = key.split(".")
        creature_type = creature_label(parts[2:-1])
        stat = {
            "HP": "Lebenspunkte",
            "Damage": "Nahkampfschaden",
            "SpellDamage": "Zauberschaden",
        }.get(parts[-1], translate_label_part(parts[-1]))
        return f"Kreaturen-{stat}: {creature_type}"
    if key.startswith("Rate.Drop.Item."):
        quality = item_quality_label(key.rsplit(".", 1)[-1])
        return f"Itemdrop-Multiplikator: {quality}"
    if key.startswith("Rate.SellValue.Item."):
        quality = item_quality_label(key.rsplit(".", 1)[-1])
        return f"Verkaufspreis-Multiplikator: {quality}"
    if key.startswith("Rate.BuyValue.Item."):
        quality = item_quality_label(key.rsplit(".", 1)[-1])
        return f"Kaufpreis-Multiplikator: {quality}"
    if key.startswith("Rate.XP."):
        return {
            "Rate.XP.Kill": "Erfahrung durch Gegner",
            "Rate.XP.Quest": "Erfahrung durch Quests",
            "Rate.XP.Quest.DF": "Erfahrung durch Dungeonfinder-Quests",
            "Rate.XP.Explore": "Erfahrung durch Entdecken",
            "Rate.XP.Pet": "Begleiter-Erfahrung",
            "Rate.XP.BattlegroundBonus": "Schlachtfeld-Bonus-Erfahrung",
        }.get(key, "Erfahrungs-Multiplikator")
    if key.startswith("Rate.Reputation."):
        return "Ruf-Multiplikator: " + " ".join(translate_label_part(part) for part in key.split(".")[2:])
    if key.startswith("Rate.Auction."):
        return {
            "Rate.Auction.Time": "Auktionsdauer-Multiplikator",
            "Rate.Auction.Deposit": "Auktionshaus-Anzahlung-Multiplikator",
            "Rate.Auction.Cut": "Auktionshaus-Gebühr-Multiplikator",
        }.get(key, "Auktionshaus-Multiplikator")
    if key.startswith("SkillChance."):
        return "Skillchance: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("SkillGain."):
        return "Skillgewinn: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Corpse.Decay."):
        return META.get(key, ("Leichnam-Dauer", ""))[0]
    if key.startswith("Battleground."):
        return "Schlachtfeld: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Arena."):
        return "Arena: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Guild."):
        return "Gilde: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("AllowTwoSide."):
        return "Fraktionsübergreifend: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Respawn.DynamicRate"):
        target = "Kreaturen" if key.endswith("Creature") else "Spielobjekte"
        return f"Dynamischer Respawn-Faktor: {target}"
    if key.startswith("Respawn.DynamicMinimum"):
        target = "Kreaturen" if key.endswith("Creature") else "Spielobjekte"
        return f"Minimaler dynamischer Respawn: {target}"
    if key.startswith("DungeonFinder."):
        return "Dungeonfinder: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Instance."):
        return "Instanzen: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Wintergrasp."):
        return "Tausendwinter: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("GM."):
        return "GM: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Warden."):
        return "Warden: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("World."):
        return "Weltserver: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("PacketSpoof."):
        return "Paketfaelschung: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("ChatFlood."):
        return "Chatflut-Schutz: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("ChatLevelReq."):
        return "Chat-Levelanforderung: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("LevelReq."):
        return "Levelanforderung: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Command."):
        return "GM-Befehl: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Death."):
        return "Tod: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Pet."):
        return "Begleiter: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Item."):
        return "Item: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Loot."):
        return "Beute: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Quests."):
        return "Quests: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Quest"):
        return "Quest: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    if key.startswith("Rate."):
        return "Multiplikator: " + " ".join(translate_label_part(part) for part in key.split(".")[1:])
    return ""


def creature_label(parts: list[str]) -> str:
    value = ".".join(parts)
    return {
        "Normal": "normale Gegner",
        "Elite.Elite": "Elite-Gegner",
        "Elite.RARE": "seltene Gegner",
        "Elite.RAREELITE": "seltene Elite-Gegner",
        "Elite.WORLDBOSS": "Weltbosse",
    }.get(value, " ".join(translate_label_part(part) for part in parts))


def item_quality_label(value: str) -> str:
    return {
        "Poor": "grau / schlecht",
        "Normal": "weiß / normal",
        "Uncommon": "grün / ungewöhnlich",
        "Rare": "blau / selten",
        "Epic": "episch",
        "Legendary": "legendär",
        "Artifact": "Artefakt",
        "Heirloom": "Erbstück",
        "Referenced": "referenzierte Beute",
        "ReferencedAmount": "Menge referenzierter Beute",
        "GroupAmount": "Gruppenbeute-Menge",
    }.get(value, translate_label_part(value))


def translate_label_part(part: str) -> str:
    words = {
        "Enable": "aktiv",
        "Enabled": "aktiv",
        "Disable": "deaktivieren",
        "Disabled": "deaktiviert",
        "Player": "Spieler",
        "Players": "Spieler",
        "Creature": "Kreatur",
        "Creatures": "Kreaturen",
        "NPC": "NPC",
        "Npc": "NPC",
        "Quest": "Quest",
        "Quests": "Quests",
        "Battleground": "Schlachtfeld",
        "Arena": "Arena",
        "Guild": "Gilde",
        "Mail": "Post",
        "Auction": "Auktion",
        "AuctionHouse": "Auktionshaus",
        "Visibility": "Sichtweite",
        "Distance": "Distanz",
        "Weather": "Wetter",
        "Interval": "Intervall",
        "Delay": "Verzögerung",
        "Timer": "Timer",
        "Time": "Zeit",
        "Count": "Anzahl",
        "Max": "Maximum",
        "Min": "Minimum",
        "Level": "Level",
        "Req": "Anforderung",
        "Reward": "Belohnung",
        "Money": "Geld",
        "Cost": "Kosten",
        "Honor": "Ehre",
        "Reputation": "Ruf",
        "Damage": "Schaden",
        "SpellDamage": "Zauberschaden",
        "Health": "Gesundheit",
        "Mana": "Mana",
        "Rage": "Wut",
        "Energy": "Energie",
        "Focus": "Fokus",
        "RunicPower": "Runenmacht",
        "Normal": "normal",
        "Rare": "selten",
        "Elite": "Elite",
        "RareElite": "seltene Elite",
        "WorldBoss": "Weltboss",
        "Database": "Datenbank",
        "WorkerThreads": "Arbeits-Threads",
        "SynchThreads": "Synchrone Threads",
        "Reconnect": "Wiederverbindung",
        "Attempts": "Versuche",
        "Seconds": "Sekunden",
        "Port": "Port",
        "BindIP": "Bind-IP",
        "LogsDir": "Logverzeichnis",
        "DataDir": "Datenverzeichnis",
        "TempDir": "Temp-Verzeichnis",
        "PidFile": "PID-Datei",
        "Server": "Server",
        "World": "Welt",
        "Realm": "Realm",
        "Characters": "Charaktere",
        "Character": "Charakter",
        "Start": "Start",
        "Rate": "Multiplikator",
        "Drop": "Drop",
        "Item": "Item",
        "Items": "Items",
        "Looted": "nach dem Plündern",
        "Decay": "Dauer",
        "Corpse": "Leichnam",
        "Chat": "Chat",
        "Channel": "Kanal",
        "Whisper": "Flüstern",
        "Say": "Sagen",
        "Yell": "Schreien",
        "Group": "Gruppe",
        "Raid": "Raid",
        "LFG": "Dungeonfinder",
        "Queue": "Warteschlange",
        "Announcer": "Ankündigung",
        "Win": "Sieg",
        "Lose": "Niederlage",
        "Rating": "Wertung",
        "Modifier": "Modifikator",
        "Modifier1": "Modifikator 1",
        "Modifier2": "Modifikator 2",
        "Matchmaker": "Gegnersuche",
        "Personal": "persönlich",
        "Bank": "Bank",
        "Tab": "Fach",
        "Cost0": "Kosten Fach 1",
        "Cost1": "Kosten Fach 2",
        "Cost2": "Kosten Fach 3",
        "Cost3": "Kosten Fach 4",
        "Cost4": "Kosten Fach 5",
        "Cost5": "Kosten Fach 6",
        "Two": "zwei",
        "Side": "Fraktionen",
        "Interaction": "Interaktion",
        "Calendar": "Kalender",
        "Invite": "Einladung",
        "Kick": "Kick",
        "Ban": "Bann",
        "Mute": "Stummschaltung",
        "Ticket": "Ticket",
        "Tickets": "Tickets",
        "Update": "Update",
        "Updates": "Updates",
        "Clean": "Bereinigen",
        "Debug": "Debug",
        "Log": "Log",
        "Logger": "Logger",
        "Metric": "Metrik",
        "Wrong": "falsch",
        "Pass": "Passwort",
        "BanTime": "Sperrdauer",
        "BanType": "Sperrart",
        "Logging": "Protokollierung",
        "Strict": "streng",
        "Version": "Version",
        "Check": "Pruefung",
        "Directory": "Verzeichnis",
        "Executable": "Programm",
        "Location": "Standort",
        "File": "Datei",
        "TOTP": "Zwei-Faktor-Code",
        "Master": "Haupt",
        "Secret": "Schluessel",
        "Processors": "CPU-Kerne",
        "Priority": "Prioritaet",
        "Realms": "Realms",
        "State": "Status",
        "Birthday": "Geburtstag",
        "Availability": "Verfuegbarkeit",
        "Zone": "Zone",
        "Locale": "Sprache",
        "Cache": "Cache",
        "Add": "hinzufuegen",
        "Idle": "inaktiv",
        "Connections": "Verbindungen",
        "Socket": "Socket",
        "Out": "Ablauf",
        "Active": "aktiv",
        "Overspeed": "zu schnelle Bewegung",
        "Pings": "Pings",
        "Disconnect": "Verbindungsabbruch",
        "Tolerance": "Toleranz",
        "After": "nach",
        "DC": "Disconnect",
        "Core": "Serverkern",
        "Stuck": "haengt",
        "Save": "speichern",
        "Immediately": "sofort",
        "Show": "anzeigen",
        "In": "in",
        "Who": "Wer",
        "List": "Liste",
        "Returns": "Rueckgabe",
        "Prevent": "verhindern",
        "AFK": "AFK",
        "Logout": "Logout",
        "Packet": "Paket",
        "Spoof": "Faelschung",
        "Duration": "Dauer",
        "Detect": "erkennen",
        "Pos": "Position",
        "Collision": "Kollision",
        "GameObject": "Spielobjekt",
        "LoS": "Sichtlinie",
        "Preload": "vorladen",
        "Instanced": "instanziert",
        "Map": "Karte",
        "Grids": "Kartenbereiche",
        "Dont": "nicht",
        "Random": "zufaellig",
        "Movement": "Bewegung",
        "Paths": "Pfade",
        "Deleted": "geloescht",
        "Lookup": "Suche",
        "Results": "Ergebnisse",
        "Water": "Wasser",
        "Breath": "Atmung",
        "Flight": "Flug",
        "Always": "immer",
        "Weapon": "Waffe",
        "Custom": "eigene",
        "Spells": "Zauber",
        "Explored": "aufgedeckt",
        "Stats": "Statistiken",
        "Only": "nur",
        "Validate": "pruefen",
        "Learned": "gelernt",
        "By": "durch",
        "Keep": "behalten",
        "Days": "Tage",
        "Names": "Namen",
        "Reserved": "reserviert",
        "Profanity": "Schimpfwoerter",
        "Settings": "Einstellungen",
        "Regen": "Regeneration",
        "Boost": "Bonus",
        "MoveSpeed": "Bewegungsgeschwindigkeit",
        "Income": "Einnahmen",
        "Loss": "Verlust",
        "Rest": "Erholung",
        "Offline": "offline",
        "Tavern": "Gasthaus",
        "City": "Stadt",
        "Wilderness": "Wildnis",
        "Bonus": "Bonus",
        "MissChanceMultiplier": "Verfehlchance",
        "Target": "Ziel",
        "Affects": "wirkt",
        "Trade": "Handel",
        "Talent": "Talent",
        "Pet": "Begleiter",
        "Discovery": "Entdeckung",
        "Dodge": "Ausweichen",
        "Parry": "Parieren",
        "Block": "Blocken",
        "Crit": "kritischer Treffer",
        "Points": "Punkte",
        "Token": "Marke",
        "Durability": "Haltbarkeit",
        "Absorb": "Absorbieren",
        "Sickness": "Schwaeche",
        "Reclaim": "zurueckholen",
        "Bones": "Knochen",
        "RankMod": "Rangmodifikator",
        "Quality": "Qualitaet",
        "Tradeable": "handelbar",
        "Monster": "Monster",
        "Sight": "Sicht",
        "Aggro": "Aggro",
        "Boss": "Boss",
        "Diff": "Abstand",
        "Range": "Reichweite",
        "Text": "Text",
        "Emote": "Emote",
        "Waypoint": "Wegpunkt",
        "Unload": "entladen",
        "Shared": "geteilt",
        "Heroic": "heroisch",
        "Access": "Zugang",
        "Requirements": "Anforderungen",
        "Print": "Ausgabe",
        "Mode": "Modus",
        "Portal": "Portal",
        "Avg": "Durchschnitt",
        "Ilevel": "Gegenstandsstufe",
        "Optional": "optional",
        "String": "Text",
        "Join": "beitreten",
        "BG": "Schlachtfeld",
        "And": "und",
        "Petition": "Gildenurkunde",
        "Signs": "Unterschriften",
        "FFA": "Jeder gegen jeden",
        "Capture": "Eroberung",
        "MMR": "MMR",
        "Team": "Team",
        "Charter": "Urkunde",
        "Recruit": "Rekrutierung",
        "Friend": "Freund",
        "Difference": "Unterschied",
        "Events": "Events",
        "Sunsreach": "Sonnenweiten",
        "Counter": "Zaehler",
        "Scourge": "Geissel",
        "Invasion": "Invasion",
        "ICC": "ICC",
        "Buff": "Stärkung",
        "Horde": "Horde",
        "Alliance": "Allianz",
        "Gunship": "Kanonenboot",
        "Munching": "Aura-Munching",
        "Daze": "Benommenheit",
        "Ammo": "Munition",
    }
    if part in words:
        return words[part]
    split = split_camel(part)
    if split != part:
        return " ".join(translate_label_part(piece) for piece in split.split())
    return split


def split_camel(value: str) -> str:
    value = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", value)
    value = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", value)
    return re.sub(r"(?<!^)(?=[A-Z])", " ", value).strip()


def description_by_prefix(key: str) -> str:
    if key.startswith("Rate.XP."):
        return "Multiplikator fuer erhaltene Erfahrungspunkte. Hoehere Werte beschleunigen das Leveln; Spieler verlassen Gebiete schneller und erreichen Dungeons oder Endgame frueher."
    if key.startswith("Rate.Drop."):
        return "Multiplikator fuer Beute. Hoehere Werte erzeugen mehr Drops oder Gold und beeinflussen dadurch Auktionshaus, Berufe und Serverwirtschaft direkt."
    if key.startswith("Rate.SellValue.Item."):
        return "Multiplikator fuer den Verkaufswert beim Haendler. Hoehere Werte geben Spielern mehr Geld beim Verkaufen dieser Itemqualitaet und bringen mehr Gold in die Wirtschaft."
    if key.startswith("Rate.BuyValue.Item."):
        return "Multiplikator fuer den Kaufpreis beim Haendler. Hoehere Werte machen Items dieser Qualitaet beim NPC teurer."
    if key.startswith("Rate.Auction."):
        return "Multiplikator fuer Auktionshausregeln. Je nach Feld wird Auktionsdauer, Anzahlung oder Auktionshausgebuehr veraendert; Spieler merken das direkt beim Einstellen und Verkaufen von Auktionen."
    if key.startswith("Rate.MoveSpeed."):
        return "Multiplikator fuer Bewegungsgeschwindigkeit. Höhere Werte lassen die betroffene Einheit schneller laufen; niedrigere Werte verlangsamen Bewegung. Das verändert Reisezeit, Kampfgefühl und Verfolgung durch NPCs deutlich."
    if key.startswith(("Rate.Health", "Rate.Mana", "Rate.Rage", "Rate.Energy", "Rate.Focus", "Rate.RunicPower", "Rate.Loyalty")):
        return "Multiplikator fuer Ressourcen oder Regeneration. Höhere Werte geben Spielern oder Begleitern mehr Spielraum und machen Kämpfe leichter; niedrigere Werte machen Ressourcenmanagement wichtiger."
    if key.startswith("Rate.Rest."):
        return "Multiplikator fuer Erholungsbonus. Höhere Werte lassen ausgeruhte Erfahrung schneller entstehen oder länger wirken; niedrigere Werte bremsen den Bonus für Gelegenheitsspieler."
    if key.startswith("Rate.MissChanceMultiplier."):
        return "Multiplikator fuer Verfehlchance. Höhere Werte erhöhen die Chance, Ziele zu verfehlen; niedrigere Werte machen Treffer zuverlässiger. Das beeinflusst Kampfgefühl und Balance direkt."
    if key.startswith("Rate.Pet."):
        return "Begleiter-Multiplikator. Höhere Werte beschleunigen Fortschritt oder Wirkung von Begleitern; niedrigere Werte machen Begleiterentwicklung langsamer."
    if key.startswith("Rate.Reward"):
        return "Belohnungs-Multiplikator. Höhere Werte erhöhen Geld- oder Bonusbelohnungen und bringen mehr Gold in die Wirtschaft; niedrigere Werte halten Belohnungen näher an blizzlike."
    if key.startswith("Rate.InstanceResetTime"):
        return "Multiplikator fuer Instanz-Resetzeiten. Höhere Werte verlängern Resetzeiten, niedrigere Werte lassen Instanzen schneller wieder verfügbar werden."
    if key.startswith("Rate.Creature.") and key.endswith(".HP"):
        return "Multiplikator fuer die Lebenspunkte dieser Gegnerkategorie. Hoehere Werte machen Kaempfe laenger und schwerer; niedrigere Werte machen Solo-Spiel und Farmen einfacher."
    if key.startswith("Rate.Creature.") and "Damage" in key:
        if key.endswith("SpellDamage"):
            return "Multiplikator fuer Zauberschaden dieser Gegnerkategorie. Hoehere Werte machen Caster-Gegner, Bosse und Magieangriffe gefaehrlicher; niedrigere Werte entschärfen magielastige Kaempfe."
        return "Multiplikator fuer Nahkampf- und normalen Schaden dieser Gegnerkategorie. Hoehere Werte machen die Welt gefaehrlicher; niedrigere Werte erleichtern Solo- und Twink-Spiel."
    if key.startswith("SkillChance."):
        return "Chance fuer Skillfortschritt. Hoehere Werte lassen Berufe und Waffenfertigkeiten schneller steigen."
    if key.startswith("SkillGain."):
        return "Multiplikator fuer Skillpunkte. Hoehere Werte verkuerzen Berufs- oder Waffen-Skillphasen deutlich."
    if key.startswith("GM."):
        return "GM-Verhalten. Beeinflusst Sichtbarkeit, Chat, Listen oder Rechte von GM-Charakteren im Spiel."
    if key.startswith("Warden."):
        return "Warden-Schutz. Beeinflusst Client-Pruefungen, Reaktionszeiten und moegliche Sanktionen bei auffaelligen Clients."
    if key.startswith("AutoBroadcast."):
        return "Automatische Servernachrichten. Spieler sehen diese Hinweise je nach Einstellung im Chat oder zentral."
    if key.startswith("Visibility."):
        return "Sichtweiten- und Anzeigeoption. Hoehere Werte wirken lebendiger und weiter, kosten aber Server- und Clientleistung."
    if key.startswith("vmap.") or key.startswith("MoveMaps") or key.startswith("MapUpdate"):
        return "Karten-, Sichtlinien- oder Bewegungsberechnung. Wichtig fuer korrekte NPC-Bewegung, Zauber-Sichtlinie und Geometrie."
    if key.startswith("CharacterCreating."):
        return "Charaktererstellung. Beeinflusst, welche Rassen/Klassen erstellt werden duerfen und was Spieler im Charakterbildschirm sehen."
    if key.startswith("Start"):
        return "Startwert fuer neue Charaktere. Spieler bemerken die Aenderung direkt bei neu erstellten Figuren."
    if key.startswith("DungeonFinder") or key.startswith("LFG."):
        return "Dungeonfinder-Verhalten. Beeinflusst Warteschlangen, Deserteur, abgeschlossene Dungeons und Komfortfunktionen."
    if key.startswith("Battleground."):
        return "Schlachtfeld-Regel. Beeinflusst Warteschlangen, Belohnungen, Timer oder Verhalten in Battlegrounds."
    if key.startswith("Arena."):
        return "Arena-Regel. Beeinflusst Wertungen, Punkte, Vorbereitung oder Matchmaking."
    if key.startswith("Guild."):
        return "Gildenregel. Beeinflusst Gildenbank, Charter, Limits oder gespeicherte Logs."
    if key.startswith("Mail"):
        return "Postsystem. Beeinflusst Zustellzeit und Mindestlevel fuer Ingame-Post."
    if key.startswith("Database.") or "Database." in key or key.endswith("DatabaseInfo"):
        return "Datenbankverbindung oder Datenbankverhalten. Falsche Werte verhindern Start oder verursachen Verbindungsabbrueche."
    if key.startswith("Network."):
        return "Netzwerkoption. Beeinflusst Socket-Verhalten, Puffer und Verbindungsperformance."
    if key.startswith("Log") or key.startswith("Logger.") or key.startswith("Appender."):
        return "Logging-Option. Beeinflusst, welche Informationen in Konsole, Dateien oder Datenbank protokolliert werden."
    if key.startswith("Metric."):
        return "Monitoring-Metrik. Aktiviert oder konfiguriert Messwerte fuer externe Systeme wie InfluxDB."
    if key.startswith("Updates."):
        return "AzerothCore-Datenbankupdates. Beeinflusst automatische SQL-Updates beim Start. Falsch gesetzt kann Updates blockieren."
    if key.startswith("Wintergrasp."):
        return "Tausendwinter-Regel. Beeinflusst Schlachtzeiten, Spielerlimits, Mindestlevel und Neustartverhalten des Events."
    if key.startswith("Quest") or key.startswith("Quests."):
        return "Questverhalten. Spieler bemerken dies bei Questanzeige, Questbedingungen oder Belohnungen."
    if key.startswith("DBC."):
        return "DBC- und Clientdatenprüfung. Diese Werte bestimmen, wie streng der Server Daten aus Clientdateien gegen Datenbankwerte prüft. Strengere Werte erhöhen Konsistenz, können aber eigene Anpassungen ausbremsen."
    if key.startswith("ItemDelete."):
        return "Automatisches Löschen alter oder bestimmter Items. Diese Einstellung beeinflusst, welche Items aus Charakterdaten entfernt oder behalten werden. Falsche Werte können gewünschte Items löschen, deshalb vorsichtig testen."
    if key.startswith("Item."):
        return "Item-Regel. Sie beeinflusst, wie Items nach Handel, Loot oder Sonderfällen behandelt werden. Spieler bemerken Änderungen direkt im Inventar oder beim Weitergeben von Gegenständen."
    if key.startswith("Loot"):
        return "Loot-Regel. Sie beeinflusst, wann und wie Beute verteilt oder beschränkt wird. Änderungen wirken sich direkt auf Gruppenloot und Itemverteilung aus."
    if key.startswith("Creature") or key.startswith("Npc"):
        return "Kreaturen- und NPC-Verhalten. Beeinflusst Aggro, Flucht, Bewegung oder Regeneration in der Welt."
    if key.startswith("Network."):
        return "Netzwerkoption fuer den Serverprozess. Falsche Werte koennen Verbindungen stoeren; sinnvolle Werte verbessern Stabilitaet oder Latenz."
    if key.startswith("Chat") or key.startswith("Channel."):
        return "Chat- und Kanalregel. Spieler merken diese Einstellung beim Schreiben, Fluestern, Gruppensuchen oder beim Schutz gegen Spam und gefaelschte Nachrichten."
    if key.startswith("AllowTwoSide."):
        return "Fraktionsuebergreifende Interaktion. Aktiviert oder deaktiviert, ob Allianz und Horde in diesem Bereich miteinander interagieren duerfen."
    if key.startswith("Respawn."):
        return "Respawn-Verhalten fuer Kreaturen oder Objekte. Beeinflusst, wann Gegner oder Spielobjekte nach Tod, Nutzung oder hoher Spielerzahl wieder erscheinen."
    if key.startswith("Durability"):
        return "Haltbarkeitsverlust. Höhere Werte lassen Ausrüstung schneller Schaden nehmen und erhöhen Reparaturdruck; niedrigere Werte machen Tod und Kämpfe günstiger."
    if key.startswith("Death."):
        return "Todesregel. Sie beeinflusst Geistheiler, Knochen, Leichnamrückkehr oder Wiederbelebungsfolgen. Spieler merken Änderungen direkt nach dem Sterben."
    if key.startswith("Pet."):
        return "Begleiterregel. Sie beeinflusst Werte oder Skalierung von Begleitern und macht Jäger-/Hexer-Spiel je nach Wert stärker oder schwächer."
    if key.startswith("ListenRange."):
        return "Chat-Reichweite in der Welt. Höhere Werte lassen Sagen, Emotes oder Schreien weiter hörbar sein; niedrigere Werte begrenzen Kommunikation stärker auf die Umgebung."
    if key.startswith("AllowTwoSide."):
        return "Fraktionsübergreifende Interaktion. Aktiviert oder deaktiviert, ob Allianz und Horde in diesem Bereich miteinander interagieren dürfen."
    if key.startswith("Debug."):
        return "Debug-Funktion für Tests. Aktivieren kann Sonderverhalten einschalten, das für Entwicklung praktisch ist, aber auf einem normalen Spielserver unblizzlike oder ausnutzbar sein kann."
    if key.startswith("Calculate."):
        return "Berechnungs- und Wartungsfunktion beim Serverstart. Aktivieren kann Daten nachberechnen, verlangsamt aber den Start stark und ist meist nur für Korrekturen oder Debugging gedacht."
    return ""


def cleanup_original(text: str) -> str:
    value = " ".join(line.strip() for line in (text or "").splitlines() if line.strip())
    value = value.replace("Enable/Disable", "Aktivieren/deaktivieren")
    value = re.sub(r"\benable or disable\b", "aktivieren oder deaktivieren", value, flags=re.I)
    value = re.sub(r"\benabled or disabled\b", "aktiviert oder deaktiviert", value, flags=re.I)
    replacements = [
        (r"\bDescription\b", "Beschreibung"),
        (r"\bDefault\b", "Standard"),
        (r"\bdisabled\b", "deaktiviert"),
        (r"\benabled\b", "aktiviert"),
        (r"\bplayers\b", "Spieler"),
        (r"\bplayer\b", "Spieler"),
        (r"\bcreatures\b", "Kreaturen"),
        (r"\bcreature\b", "Kreatur"),
        (r"\bworldserver\b", "Worldserver"),
        (r"\bauthserver\b", "Authserver"),
        (r"\bdatabases\b", "Datenbanken"),
        (r"\bdatabase\b", "Datenbank"),
        (r"\bmilliseconds\b", "Millisekunden"),
        (r"\bseconds\b", "Sekunden"),
    ]
    for pattern, new in replacements:
        value = re.sub(pattern, new, value, flags=re.I)
    return value
