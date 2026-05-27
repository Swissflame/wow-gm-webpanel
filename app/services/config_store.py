from sqlalchemy.orm import Session
from ..models import PanelConfig


DEFAULTS = {
    "server": {
        "wow_host": "192.168.1.118",
        "ssh_user": "klaus",
        "ssh_password": "",
        "ssh_port": 22,
        "normal_path": "/opt/azeroth-server",
        "playerbot_path": "/opt/azeroth-playerbots-server",
    },
    "mysql": {
        "host": "192.168.1.118",
        "port": 3306,
        "user": "acore",
        "password": "",
        "auth_db": "acore_auth",
        "world_db": "acore_world",
        "characters_db": "acore_characters",
        "pb_world_db": "pb_world",
        "pb_characters_db": "pb_characters",
        "playerbots_db": "acore_playerbots",
    },
    "realms": {
        "auth_port": 3724,
        "normal_world_port": 8085,
        "playerbot_world_port": 8086,
    },
    "language": "de",
    "gm_transport": {
        "mode": "disabled",
        "username": "",
        "password": "",
        "normal_host": "192.168.1.118",
        "normal_port": 7878,
        "playerbot_host": "192.168.1.118",
        "playerbot_port": 7879,
    },
    "setup_complete": False,
}


def get_config(db: Session, key: str, default=None):
    row = db.query(PanelConfig).filter_by(key=key).first()
    return row.value if row else default


def set_config(db: Session, key: str, value):
    row = db.query(PanelConfig).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        row = PanelConfig(key=key, value=value)
        db.add(row)
    db.commit()
    return row


def all_config(db: Session) -> dict:
    data = {k: v.copy() if isinstance(v, dict) else v for k, v in DEFAULTS.items()}
    for row in db.query(PanelConfig).all():
        data[row.key] = row.value
    return data


def bootstrap_defaults(db: Session):
    for key, value in DEFAULTS.items():
        if db.query(PanelConfig).filter_by(key=key).first() is None:
            set_config(db, key, value)
