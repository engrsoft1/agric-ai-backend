from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request
from audit_service import log_activity
from sqlalchemy.orm import Session
from sqlalchemy import func
from audit_service import log_activity
import schemas
import crud
import models
from schemas import (
    FarmerRegister,
    BuyerRegister,
    FarmerLogin,
    BuyerLogin,
    AdminLogin,
    AdminRegister,
)


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
# FARMER REGISTRATION WITH AUDIT LOGGING
# ============================================================

@router.post("/farmer-register")
def farmer_register(
    user: schemas.FarmerRegister,
    request: Request,
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Prepare audit information
    # --------------------------------------------------------

    ip_address = (
        request.client.host
        if request.client
        else None
    )
    user_agent = request.headers.get("user-agent")

    def record_registration(
        result: str,
        details: str,
        actor_id: int = None,
        target_user_id: int = None,
    ):
        log_activity(
            db=db,
            category="AUTHENTICATION",
            action="FARMER_REGISTRATION",
            actor_id=actor_id,
            target_user_id=target_user_id,
            result=result,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()

    # --------------------------------------------------------
    # 1. Check password confirmation
    # --------------------------------------------------------

    if user.password != user.confirm_password:
        record_registration(
            result="FAILED",
            details="Farmer registration failed: passwords did not match.",
        )

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
        record_registration(
            result="FAILED",
            details="Farmer registration failed: Farmer ID already registered.",
            target_user_id=existing_user.id,
        )

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
            models.VerifiedFarmer.farmer_id == user.farmer_id
        )
        .first()
    )

    if verified_farmer is None:
        record_registration(
            result="FAILED",
            details="Farmer registration failed: Farmer ID was not recognized.",
        )

        raise HTTPException(
            status_code=403,
            detail="Farmer ID is not recognized.",
        )

    # --------------------------------------------------------
    # 4. Verify phone number
    # --------------------------------------------------------

    if verified_farmer.phone != user.phone:
        record_registration(
            result="FAILED",
            details="Farmer registration failed: phone number did not match the verified record.",
        )

        raise HTTPException(
            status_code=403,
            detail="Phone number does not match the verified Farmer ID.",
        )

    # --------------------------------------------------------
    # 5. Verify age
    # --------------------------------------------------------

    if verified_farmer.age != user.age:
        record_registration(
            result="FAILED",
            details="Farmer registration failed: age did not match the verified record.",
        )

        raise HTTPException(
            status_code=403,
            detail="Age does not match the verified Farmer ID.",
        )

    # --------------------------------------------------------
    # 6. Create farmer account
    # --------------------------------------------------------

    try:
        created = crud.create_farmer(
            db,
            user,
            verified_farmer,
        )

        # Record successful registration.
        log_activity(
            db=db,
            category="AUTHENTICATION",
            action="FARMER_REGISTRATION",
            actor_id=created.id,
            target_user_id=created.id,
            result="SUCCESS",
            details="Farmer account registered successfully.",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(created)

    except Exception:
        db.rollback()

        # Do not expose internal database errors to the client.
        raise HTTPException(
            status_code=500,
            detail="Farmer registration could not be completed.",
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

# ============================================================
# VERIFY ADMINISTRATOR ACCESS
# ============================================================

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
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
            detail="Invalid authentication token.",
        )

    db_user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="User account not found.",
        )

    if (db_user.role or "").strip().lower() != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator privileges are required.",
        )

    if (db_user.status or "").strip().lower() == "blocked":
        raise HTTPException(
            status_code=403,
            detail="This administrator account has been disabled.",
        )

    return db_user
# ============================================================
# ADMIN LOGIN
# ============================================================

@router.post("/admin-login")
def admin_login(
    data: AdminLogin,
    db: Session = Depends(get_db),
):
    identifier = data.identifier.strip()

    # Find the matching administrator account specifically.
    db_user = (
        db.query(models.User)
        .filter(
            models.User.role.ilike("admin"),
            (
                (models.User.email == identifier)
                | (models.User.phone == identifier)
            ),
        )
        .first()
    )

    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials or administrator account not found.",
        )

    # Verify password.
    if not verify_password(
        data.password,
        db_user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials.",
        )

    # Reject disabled administrator accounts.
    if (db_user.status or "").strip().lower() == "blocked":
        raise HTTPException(
            status_code=403,
            detail="This administrator account has been disabled.",
        )

    # Generate access token.
    access_token = create_access_token(
        {
            "sub": str(db_user.id),
            "role": db_user.role,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "full_name": db_user.full_name,
            "email": db_user.email,
            "phone": db_user.phone,
            "role": db_user.role,
        },
    }
# ============================================================
# ADMIN REGISTRATION
# ============================================================

@router.post("/admin-register", status_code=201)
def admin_register(
    user: AdminRegister,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    # Verify password confirmation.
    if user.password != user.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match.",
        )

    # Normalize input.
    full_name = user.full_name.strip()
    email = str(user.email).strip().lower()
    phone = user.phone.strip()

    # Validate required fields.
    if not full_name:
        raise HTTPException(
            status_code=400,
            detail="Full name is required.",
        )

    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Phone number is required.",
        )

    if user.age < 18:
        raise HTTPException(
            status_code=400,
            detail="Administrator must be at least 18 years old.",
        )

    if len(user.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )

    # Check whether the email is already registered.
    existing_email = (
        db.query(models.User)
        .filter(models.User.email.ilike(email))
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email is already registered.",
        )

    # Check whether the phone number is already registered.
    existing_phone = (
        db.query(models.User)
        .filter(models.User.phone == phone)
        .first()
    )

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone number is already registered.",
        )

    # Create the administrator account.
    new_admin = models.User(
        full_name=full_name,
        email=email,
        phone=phone,
        age=user.age,
        password_hash=hash_password(user.password),
        role="admin",
        status="approved",
        is_verified=1,
        farmer_id=None,
        verified_farmer_id=None,
    )

    try:
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to register administrator. Please try again.",
        )

    return {
        "message": "Administrator registered successfully.",
        "user": {
            "id": new_admin.id,
            "full_name": new_admin.full_name,
            "email": new_admin.email,
            "phone": new_admin.phone,
            "role": new_admin.role,
            "status": new_admin.status,
        },
    }
# ============================================================
# REMOVE ADMIN ACCESS
# ============================================================

@router.delete("/admins/{user_id}/remove-access")
def remove_admin_access(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    # Prevent an administrator from removing their own access.
    if current_admin.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot remove your own administrator access.",
        )

    # Find the target account.
    target_admin = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if target_admin is None:
        raise HTTPException(
            status_code=404,
            detail="User account not found.",
        )

    # Only administrator accounts can be demoted.
    if (target_admin.role or "").strip().lower() != "admin":
        raise HTTPException(
            status_code=400,
            detail="This user is not an administrator.",
        )

    # Count active administrators.
    active_admin_count = (
        db.query(models.User)
        .filter(
            func.lower(models.User.role) == "admin",
            func.lower(models.User.status) != "blocked",
        )
        .count()
    )

    # Protect the last active administrator.
    if active_admin_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove access from the last active administrator.",
        )

    # Demote the administrator and record the activity.
    try:
        target_admin.role = "buyer"

        log_activity(
            db=db,
            category="ADMINISTRATION",
            action="ADMIN_ACCESS_REMOVED",
            actor_id=current_admin.id,
            target_user_id=target_admin.id,
            result="SUCCESS",
            details="Administrator privileges removed; role changed to buyer.",
        )

        db.commit()
        db.refresh(target_admin)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to remove administrator access.",
        )

    return {
        "success": True,
        "message": "Administrator access removed successfully.",
        "user": {
            "id": target_admin.id,
            "full_name": target_admin.full_name,
            "email": target_admin.email,
            "role": target_admin.role,
            "status": target_admin.status,
        },
    }
# ============================================================
# DISABLE ADMIN ACCOUNT
# ============================================================

@router.patch("/admins/{user_id}/disable")
def disable_admin_account(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    # Prevent an administrator from disabling their own account.
    if current_admin.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot disable your own administrator account.",
        )

    # Find the target account.
    target_admin = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if target_admin is None:
        raise HTTPException(
            status_code=404,
            detail="User account not found.",
        )

    # Only administrator accounts can be disabled through this endpoint.
    if (target_admin.role or "").strip().lower() != "admin":
        raise HTTPException(
            status_code=400,
            detail="This user is not an administrator.",
        )

    # Check whether the target account is already disabled.
    if (target_admin.status or "").strip().lower() == "blocked":
        raise HTTPException(
            status_code=400,
            detail="This administrator account is already disabled.",
        )

    # Count active administrators.
    active_admin_count = (
        db.query(models.User)
        .filter(
            func.lower(models.User.role) == "admin",
            func.lower(models.User.status) != "blocked",
        )
        .count()
    )

    # Protect the last active administrator.
    if active_admin_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot disable the last active administrator.",
        )

    # Disable the account and record the activity.
    try:
        target_admin.status = "blocked"

        log_activity(
            db=db,
            category="ADMINISTRATION",
            action="ADMIN_ACCOUNT_DISABLED",
            actor_id=current_admin.id,
            target_user_id=target_admin.id,
            result="SUCCESS",
            details="Administrator account disabled; status changed to blocked.",
        )

        db.commit()
        db.refresh(target_admin)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to disable administrator account.",
        )

    return {
        "success": True,
        "message": "Administrator account disabled successfully.",
        "user": {
            "id": target_admin.id,
            "full_name": target_admin.full_name,
            "email": target_admin.email,
            "role": target_admin.role,
            "status": target_admin.status,
        },
    }
# ============================================================
# REACTIVATE ADMIN ACCOUNT
# ============================================================

@router.patch("/admins/{user_id}/reactivate")
def reactivate_admin_account(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    # Find the target account.
    target_admin = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if target_admin is None:
        raise HTTPException(
            status_code=404,
            detail="User account not found.",
        )

    # Only administrator accounts can be reactivated here.
    if (target_admin.role or "").strip().lower() != "admin":
        raise HTTPException(
            status_code=400,
            detail="This user is not an administrator.",
        )

    # Check whether the account is already active.
    if (target_admin.status or "").strip().lower() != "blocked":
        raise HTTPException(
            status_code=400,
            detail="This administrator account is not disabled.",
        )

    # Restore access and record the activity.
    try:
        target_admin.status = "approved"

        log_activity(
            db=db,
            category="ADMINISTRATION",
            action="ADMIN_ACCOUNT_REACTIVATED",
            actor_id=current_admin.id,
            target_user_id=target_admin.id,
            result="SUCCESS",
            details="Administrator account reactivated; status changed to approved.",
        )

        db.commit()
        db.refresh(target_admin)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to reactivate administrator account.",
        )

    return {
        "success": True,
        "message": "Administrator account reactivated successfully.",
        "user": {
            "id": target_admin.id,
            "full_name": target_admin.full_name,
            "email": target_admin.email,
            "role": target_admin.role,
            "status": target_admin.status,
        },
    }
# ============================================================
# LIST ALL ADMINISTRATORS
# ============================================================

@router.get("/admins")
def list_administrators(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    administrators = (
        db.query(models.User)
        .filter(
            func.lower(models.User.role) == "admin"
        )
        .order_by(models.User.id.asc())
        .all()
    )

    return {
        "success": True,
        "total": len(administrators),
        "administrators": [
            {
                "id": admin.id,
                "full_name": admin.full_name,
                "email": admin.email,
                "phone": admin.phone,
                "age": admin.age,
                "role": admin.role,
                "status": admin.status,
                "is_verified": admin.is_verified,
                "created_at": admin.created_at,
            }
            for admin in administrators
        ],
    }

# ============================================================
# VIEW APPLICATION ACTIVITY AUDIT LOGS
# ============================================================

@router.get("/admin-audit-logs")
def get_admin_audit_logs(
    category: str = None,
    action: str = None,
    result: str = None,
    actor_id: int = None,
    target_user_id: int = None,
    skip: int = 0,
    limit: int = 50,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Retrieve application activity audit logs.
    Only authenticated administrators can access this endpoint.
    """

    # Validate pagination parameters.
    if skip < 0:
        raise HTTPException(
            status_code=400,
            detail="skip cannot be negative.",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100.",
        )

    # Start the audit log query.
    query = db.query(models.AdminAuditLog)

    # Apply optional filters.
    if category:
        query = query.filter(
            models.AdminAuditLog.category == category
        )

    if action:
        query = query.filter(
            models.AdminAuditLog.action == action
        )

    if result:
        query = query.filter(
            models.AdminAuditLog.result == result
        )

    if actor_id is not None:
        query = query.filter(
            models.AdminAuditLog.actor_id == actor_id
        )

    if target_user_id is not None:
        query = query.filter(
            models.AdminAuditLog.target_user_id == target_user_id
        )

    # Count matching records before pagination.
    total = query.count()

    # Retrieve the most recent records first.
    logs = (
        query.order_by(
            models.AdminAuditLog.created_at.desc(),
            models.AdminAuditLog.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Return the audit records.
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "logs": [
            {
                "id": log.id,
                "actor_id": log.actor_id,
                "target_user_id": log.target_user_id,
                "category": log.category,
                "action": log.action,
                "result": log.result,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }