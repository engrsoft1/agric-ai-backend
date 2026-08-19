from pydantic import BaseModel, Field, EmailStr


# ============================================================
# FARMER REGISTRATION
# ============================================================

class FarmerRegister(BaseModel):

    farmer_id: str
    phone: str
    age: int

    password: str = Field(
        min_length=6,
        max_length=128,
    )

    confirm_password: str


# ============================================================
# BUYER REGISTRATION
# ============================================================

class BuyerRegister(BaseModel):

    full_name: str

    email: EmailStr

    phone: str

    age: int

    password: str = Field(
        min_length=6,
        max_length=128,
    )

    confirm_password: str

# ============================================================
# FARMER LOGIN
# ============================================================

class FarmerLogin(BaseModel):

    identifier: str   # farmer_id or phone number

    password: str


# ============================================================
# BUYER LOGIN
# ============================================================

class BuyerLogin(BaseModel):

    identifier: str  # Email or phone number

    password: str