from ..models import CommandHistory

COMMANDS = [
    {"level": 1, "name": "Ankündigung", "template": "announce {text}", "fields": ["text"]},
    {"level": 1, "name": "Spieler kicken", "template": "kick {player}", "fields": ["player"]},
    {"level": 2, "name": "Wiederbeleben", "template": "revive {player}", "fields": ["player"]},
    {"level": 2, "name": "Level setzen", "template": "character level {player} {level}", "fields": ["player", "level"]},
    {"level": 2, "name": "Geld geben", "template": "modify money {money}", "fields": ["money"]},
    {"level": 3, "name": "Server speichern", "template": "saveall", "fields": []},
    {"level": 3, "name": "Herunterfahren", "template": "server shutdown {seconds}", "fields": ["seconds"]},
]


def allowed_commands(gm_level: int):
    return [cmd for cmd in COMMANDS if gm_level >= cmd["level"]]


def record_command(db, user_id, realm, command, result):
    db.add(CommandHistory(user_id=user_id, realm=realm, command=command, result=result))
    db.commit()
