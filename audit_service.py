from typing import Optional

from sqlalchemy.orm import Session

import models


def log_activity(
    db: Session,
    category: str,
    action: str,
    actor_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    result: str = "SUCCESS",
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    phone: Optional[str] = None,
    farmer_id: Optional[str] = None,
) -> models.AdminAuditLog:
    """
    Record an application activity in the audit log.

    The caller controls the database transaction and must commit
    the record along with the related operation when appropriate.
    """

    audit_record = models.AdminAuditLog(
        actor_id=actor_id,
        target_user_id=target_user_id,
        category=category,
        action=action,
        result=result,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        phone=phone,
        farmer_id=farmer_id,
    )

    db.add(audit_record)

    return audit_record