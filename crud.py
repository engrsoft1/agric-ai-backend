from sqlalchemy.orm import Session

import models
import schemas

from utils.security import hash_password


# ============================================================
# FIND USER BY FARMER ID
# ============================================================

def get_user_by_farmer_id(
    db: Session,
    farmer_id: str,
):
    return (
        db.query(models.User)
        .filter(
            models.User.farmer_id == farmer_id
        )
        .first()
    )


# ============================================================
# FIND USER BY EMAIL
# ============================================================

def get_user_by_email(
    db: Session,
    email: str,
):
    return (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


# ============================================================
# FIND USER BY PHONE
# ============================================================

def get_user_by_phone(
    db: Session,
    phone: str,
):
    return (
        db.query(models.User)
        .filter(
            models.User.phone == phone
        )
        .first()
    )


# ============================================================
# CREATE FARMER
# ============================================================

def create_farmer(
    db: Session,
    user: schemas.FarmerRegister,
    verified_farmer: models.VerifiedFarmer,
):

    db_user = models.User(

        farmer_id=user.farmer_id,

        phone=user.phone,

        age=user.age,

        password_hash=hash_password(
            user.password
        ),

        role="farmer",

        status="approved",

        is_verified=1,

        verified_farmer_id=verified_farmer.id,

    )

    db.add(db_user)

    db.commit()

    db.refresh(db_user)

    return db_user


# ============================================================
# CREATE BUYER
# ============================================================

def create_buyer(
    db: Session,
    user: schemas.BuyerRegister,
):

    db_user = models.User(

        full_name=user.full_name,

        email=user.email,

        phone=user.phone,

        age=user.age,

        password_hash=hash_password(
            user.password
        ),

        role="buyer",

        status="approved",

        is_verified=0,

    )

    db.add(db_user)

    db.commit()

    db.refresh(db_user)

    return db_user