from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import models

from database import get_db

from utils.jwt_handler import decode_access_token


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
):

    token = credentials.credentials

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):

        raise HTTPException(
            status_code=401,
            detail="Invalid user ID in authentication token.",
        )

    db_user = (
        db.query(models.User)
        .filter(
            models.User.id == user_id
        )
        .first()
    )

    if db_user is None:

        raise HTTPException(
            status_code=401,
            detail="User account not found.",
        )

    return db_user
def get_current_farmer(
    current_user=Depends(get_current_user),
):
    if current_user.role.lower() != "farmer":
        raise HTTPException(
            status_code=403,
            detail="Only farmers are allowed to manage marketplace products.",
        )

    return current_user

def get_current_admin(
    current_user=Depends(get_current_user),
):
    if current_user.role.lower() != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators are allowed to perform this action.",
        )

    return current_user
