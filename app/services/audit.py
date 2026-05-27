from sqlalchemy.orm import Session
from ..models import AuditLog


def log_action(db: Session, user_id: int | None, action: str, target: str | None = None, detail: str | None = None, ip: str | None = None):
    db.add(AuditLog(user_id=user_id, action=action, target=target, detail=detail, ip_address=ip))
    db.commit()
