from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session


import crud
import models
import schemas

from database import get_db

from utils.security import (
    hash_password,
    verify_password,
)


from utils.jwt_handler import (
    create_access_token,
    decode_access_token,
)
bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# FARMER REGISTRATION
# ============================================================

@router.post("/farmer-register")
def farmer_register(
    user: schemas.FarmerRegister,
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # 1. Check password confirmation
    # --------------------------------------------------------

    if user.password != user.confirm_password:

        raise HTTPException(
            status_code=400,
            detail="Passwords do not match.",
        )

    # --------------------------------------------------------
    # 2. Check if Farmer ID already has an account
    # --------------------------------------------------------

    existing_user = crud.get_user_by_farmer_id(
        db,
        user.farmer_id,
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="This Farmer ID is already registered.",
        )

    # --------------------------------------------------------
    # 3. Find Farmer ID in verified farmers table
    # --------------------------------------------------------

    verified_farmer = (
        db.query(models.VerifiedFarmer)
        .filter(
            models.VerifiedFarmer.farmer_id
            == user.farmer_id
        )
        .first()
    )

    if verified_farmer is None:

        raise HTTPException(
            status_code=403,
            detail="Farmer ID is not recognized.",
        )

    # --------------------------------------------------------
    # 4. Verify phone number
    # --------------------------------------------------------

    if verified_farmer.phone != user.phone:

        raise HTTPException(
            status_code=403,
            detail="Phone number does not match the verified Farmer ID.",
        )

    # --------------------------------------------------------
    # 5. Verify age
    # --------------------------------------------------------

    if verified_farmer.age != user.age:

        raise HTTPException(
            status_code=403,
            detail="Age does not match the verified Farmer ID.",
        )

    # --------------------------------------------------------
    # 6. Create farmer account
    # --------------------------------------------------------

    created = crud.create_farmer(
        db,
        user,
        verified_farmer,
    )

    # --------------------------------------------------------
    # 7. Return successful registration
    # --------------------------------------------------------

    return {
        "message": "Farmer registration successful.",

        "user": {
            "id": created.id,
            "farmer_id": created.farmer_id,
            "phone": created.phone,
            "age": created.age,
            "role": created.role,
            "status": created.status,
            "is_verified": created.is_verified,
        },
    }


# ============================================================
# FARMER LOGIN
# ============================================================

@router.post("/farmer-login")
def farmer_login(
    user: schemas.FarmerLogin,
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Try Farmer ID first
    # --------------------------------------------------------

    db_user = crud.get_user_by_farmer_id(
        db,
        user.identifier,
    )

    # --------------------------------------------------------
    # If Farmer ID doesn't find a user, try phone
    # --------------------------------------------------------

    if db_user is None:

        db_user = crud.get_user_by_phone(
            db,
            user.identifier,
        )

    # --------------------------------------------------------
    # User not found
    # --------------------------------------------------------

    if db_user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid Farmer ID/phone or password.",
        )

    # --------------------------------------------------------
    # Make sure this is a farmer account
    # --------------------------------------------------------

    if db_user.role != "farmer":

        raise HTTPException(
            status_code=401,
            detail="Invalid Farmer ID/phone or password.",
        )

    # --------------------------------------------------------
    # Verify password
    # --------------------------------------------------------

    if not verify_password(
        user.password,
        db_user.password_hash,
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid Farmer ID/phone or password.",
        )

    # --------------------------------------------------------
    # Make sure farmer is verified
    # --------------------------------------------------------

    if db_user.is_verified != 1:

        raise HTTPException(
            status_code=403,
            detail="Farmer account is not verified.",
        )

    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    token = create_access_token(
        {
            "sub": str(db_user.id),
            "role": db_user.role,
        }
    )

    # --------------------------------------------------------
    # Return login response
    # --------------------------------------------------------

    return {
        "access_token": token,

        "token_type": "bearer",

        "user": {
            "id": db_user.id,
            "farmer_id": db_user.farmer_id,
            "phone": db_user.phone,
            "age": db_user.age,
            "role": db_user.role,
            "is_verified": db_user.is_verified,
        },
    }

# ============================================================
# BUYER REGISTRATION
# ============================================================

@router.post("/buyer-register")
def buyer_register(
    user: schemas.BuyerRegister,
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # 1. Check password confirmation
    # --------------------------------------------------------

    if user.password != user.confirm_password:

        raise HTTPException(
            status_code=400,
            detail="Passwords do not match.",
        )

    # --------------------------------------------------------
    # 2. Check existing email
    # --------------------------------------------------------

    existing_email = crud.get_user_by_email(
        db,
        user.email,
    )

    if existing_email:

        raise HTTPException(
            status_code=400,
            detail="Email is already registered.",
        )

    # --------------------------------------------------------
    # 3. Check existing phone
    # --------------------------------------------------------

    existing_phone = crud.get_user_by_phone(
        db,
        user.phone,
    )

    if existing_phone:

        raise HTTPException(
            status_code=400,
            detail="Phone number is already registered.",
        )

    # --------------------------------------------------------
    # 4. Create buyer account
    # --------------------------------------------------------

    created = crud.create_buyer(
        db,
        user,
    )

    # --------------------------------------------------------
    # 5. Return successful registration
    # --------------------------------------------------------

    return {

        "message": "Buyer registration successful.",

        "user": {

            "id": created.id,

            "full_name": created.full_name,

            "email": created.email,

            "phone": created.phone,

            "age": created.age,

            "role": created.role,

        },
    }


# ============================================================
# BUYER LOGIN
# ============================================================

@router.post("/buyer-login")
def buyer_login(
    user: schemas.BuyerLogin,
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Try email first
    # --------------------------------------------------------

    db_user = crud.get_user_by_email(
        db,
        user.identifier,
    )

    # --------------------------------------------------------
    # If email doesn't find a user, try phone
    # --------------------------------------------------------

    if db_user is None:

        db_user = crud.get_user_by_phone(
            db,
            user.identifier,
        )

    # --------------------------------------------------------
    # User not found
    # --------------------------------------------------------

    if db_user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid email/phone or password.",
        )

    # --------------------------------------------------------
    # Make sure this is a buyer account
    # --------------------------------------------------------

    if db_user.role != "buyer":

        raise HTTPException(
            status_code=401,
            detail="Invalid email/phone or password.",
        )

    # --------------------------------------------------------
    # Verify password
    # --------------------------------------------------------

    if not verify_password(
        user.password,
        db_user.password_hash,
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email/phone or password.",
        )

    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    token = create_access_token(
        {
            "sub": str(db_user.id),
            "role": db_user.role,
        }
    )

    # --------------------------------------------------------
    # Return login response
    # --------------------------------------------------------

    return {

        "access_token": token,

        "token_type": "bearer",

        "user": {

            "id": db_user.id,

            "full_name": db_user.full_name,

            "email": db_user.email,

            "phone": db_user.phone,

            "age": db_user.age,

            "role": db_user.role,

        },
    }
# ============================================================
# CURRENT USER
# ============================================================

@router.get("/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Get JWT token
    # --------------------------------------------------------

    token = credentials.credentials

    # --------------------------------------------------------
    # Decode JWT
    # --------------------------------------------------------

    payload = decode_access_token(token)

    if payload is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
        )

    # --------------------------------------------------------
    # Get user ID from JWT
    # --------------------------------------------------------

    user_id = payload.get("sub")

    if user_id is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )

    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    db_user = (
        db.query(models.User)
        .filter(
            models.User.id == int(user_id)
        )
        .first()
    )

    if db_user is None:

        raise HTTPException(
            status_code=401,
            detail="User account not found.",
        )

    # --------------------------------------------------------
    # Return user information
    # --------------------------------------------------------

    return {

        "id": db_user.id,

        "role": db_user.role,

        "farmer_id": db_user.farmer_id,

        "full_name": db_user.full_name,

        "email": db_user.email,

        "phone": db_user.phone,

        "age": db_user.age,

        "status": db_user.status,

        "is_verified": db_user.is_verified,

    }