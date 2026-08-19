from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    Text,
)

from sqlalchemy.orm import relationship

from datetime import datetime

from database import Base


# ==========================================
# USERS
# ==========================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Buyer information
    full_name = Column(
        String,
        nullable=True,
    )

    email = Column(
        String,
        nullable=True,
        unique=True,
    )

    # Common information
    phone = Column(
        String,
        nullable=False,
    )

    age = Column(
        Integer,
        nullable=False,
    )

    # Farmer information
    farmer_id = Column(
        String,
        nullable=True,
        unique=True,
    )

    password_hash = Column(
        String,
        nullable=False,
    )

    role = Column(
        String,
        nullable=False,
        default="buyer",
    )

    status = Column(
        String,
        nullable=False,
        default="approved",
    )

    is_verified = Column(
        Integer,
        default=0,
    )

    verified_farmer_id = Column(
        Integer,
        ForeignKey("verified_farmers.id"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    products = relationship(
        "Product",
        back_populates="owner",
    )
# ==========================================
# VERIFIED FARMERS
# ==========================================

class VerifiedFarmer(Base):
    __tablename__ = "verified_farmers"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    farmer_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    phone = Column(
        String,
        nullable=False,
    )

    age = Column(
        Integer,
        nullable=False,
    )
# ==========================================
# PRODUCTS
# ==========================================

class Product(Base):

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    description = Column(Text)

    category = Column(String)

    price = Column(Float)

    quantity = Column(Integer)

    unit = Column(String)

    location = Column(String)

    phone = Column(String)

    whatsapp = Column(String)

    status = Column(
    String,
    default="available",
)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
    )

    owner = relationship(
        "User",
        back_populates="products",
    )

    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete",
    )

    updated_at = Column(
    DateTime,
    default=datetime.utcnow,
    onupdate=datetime.utcnow,
)


# ==========================================
# PRODUCT IMAGES
# ==========================================

class ProductImage(Base):

    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True)

    image_url = Column(String)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
    )

    product = relationship(
        "Product",
        back_populates="images",
    )