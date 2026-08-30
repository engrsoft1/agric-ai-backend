import os
import shutil
import uuid

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Product, ProductImage
from utils.auth import get_current_user

router = APIRouter(
    prefix="/marketplace",
    tags=["Marketplace"],
)


UPLOAD_FOLDER = "uploads/products"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True,
)


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()



# ==========================================================
# GET SINGLE PRODUCT DETAILS
# ==========================================================

@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.status == "available",
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    # Clean phone number for WhatsApp
    whatsapp_number = product.whatsapp or ""
    whatsapp_number = (
        whatsapp_number
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    # Nigeria-specific handling:
    # 080234567891 -> 23480234567891
    if whatsapp_number.startswith("0"):
        whatsapp_number = "234" + whatsapp_number[1:]
    elif whatsapp_number.startswith("234"):
        pass
    elif len(whatsapp_number) == 11:
     whatsapp_number = "234" + whatsapp_number

    whatsapp_url = (
        f"https://wa.me/{whatsapp_number}"
        if whatsapp_number
        else None
    )

    # Phone dialing URL
    phone_url = (
        f"tel:{product.phone}"
        if product.phone
        else None
    )

    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "category": product.category,
        "price": product.price,
        "quantity": product.quantity,
        "unit": product.unit,
        "location": product.location,
        "phone": product.phone,
        "whatsapp": product.whatsapp,
        "phone_url": phone_url,
        "whatsapp_url": whatsapp_url,
        "status": product.status,
        "owner_id": product.owner_id,
        "created_at": product.created_at,
        "updated_at": product.updated_at,

        "images": [
            f"/uploads/products/{os.path.basename(image.image_url)}"
            for image in product.images
            if image.image_url
        ],
    }

# ==========================================================
# GET ALL AVAILABLE PRODUCTS
# SEARCH + FILTER + PAGINATION
# ==========================================================
@router.get("/products")
def get_products(
    search: str | None = None,
    category: str | None = None,
    location: str | None = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "newest",

    db: Session = Depends(get_db),
):
    # ------------------------------------------------------
    # VALIDATE PAGINATION
    # ------------------------------------------------------

    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page must be greater than or equal to 1.",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100.",
        )

    # ------------------------------------------------------
    # BASE QUERY
    # ------------------------------------------------------

    query = (
        db.query(Product)
        .filter(Product.status == "available")
    )

    # ------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------

    if search:
        search_term = f"%{search.strip()}%"

        query = query.filter(
            Product.title.ilike(search_term)
            | Product.description.ilike(search_term)
            | Product.category.ilike(search_term)
            | Product.location.ilike(search_term)
        )

    # ------------------------------------------------------
    # CATEGORY FILTER
    # ------------------------------------------------------

    if category:
        query = query.filter(
            Product.category.ilike(
                category.strip()
            )
        )

    # ------------------------------------------------------
    # LOCATION FILTER
    # ------------------------------------------------------

    if location:
        query = query.filter(
            Product.location.ilike(
                location.strip()
            )
        )

    # ------------------------------------------------------
    # TOTAL PRODUCTS
    # ------------------------------------------------------

    total = query.count()

    # ------------------------------------------------------
    # PAGINATION
    # ------------------------------------------------------

    offset = (page - 1) * limit

      # ------------------------------------------------------
    # SORTING
    # ------------------------------------------------------

    if sort == "newest":

        query = query.order_by(
            Product.created_at.desc()
        )

    elif sort == "oldest":

        query = query.order_by(
            Product.created_at.asc()
        )

    elif sort == "price_asc":

        query = query.order_by(
            Product.price.asc()
        )

    elif sort == "price_desc":

        query = query.order_by(
            Product.price.desc()
        )

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid sort option. "
                "Use newest, oldest, price_asc, or price_desc."
            ),
        )

    products = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    # ------------------------------------------------------
    # FORMAT PRODUCTS
    # ------------------------------------------------------

    product_list = []

    for product in products:

        product_list.append({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "category": product.category,
            "price": product.price,
            "quantity": product.quantity,
            "unit": product.unit,
            "location": product.location,
            "phone": product.phone,
            "whatsapp": product.whatsapp,
            "phone_url": (
                f"tel:{product.phone}"
                if product.phone
                else None
            ),
            "whatsapp_url": (
                f"https://wa.me/{product.whatsapp}"
                if product.whatsapp
                else None
            ),
            "status": product.status,
            "owner_id": product.owner_id,
            "created_at": product.created_at,
            "updated_at": product.updated_at,

            "images": [
                f"/uploads/products/{os.path.basename(image.image_url)}"
                for image in product.images
                if image.image_url
            ],
        })

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    return {
        "products": product_list,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (
                (total + limit - 1) // limit
                if total > 0
                else 0
            ),
        },
    }

# ==========================================================
# GET SELLER'S PRODUCTS
# ==========================================================

@router.get("/my-products/{owner_id}")
def get_my_products(
    owner_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only allow a seller to view their own products
    if current_user.id != owner_id:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to view these products.",
        )

    products = (
        db.query(Product)
        .filter(Product.owner_id == owner_id)
        .order_by(Product.created_at.desc())
        .all()
    )

    product_list = []

    for product in products:
        product_list.append({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "category": product.category,
            "price": product.price,
            "quantity": product.quantity,
            "unit": product.unit,
            "location": product.location,
            "phone": product.phone,
            "whatsapp": product.whatsapp,
            "status": product.status,
            "owner_id": product.owner_id,
            "created_at": product.created_at,
            "updated_at": product.updated_at,

            "images": [
                f"/uploads/products/{os.path.basename(image.image_url)}"
                for image in product.images
                if image.image_url
            ],
        })

    return product_list

# ==========================================================
# CREATE PRODUCT
# ==========================================================

@router.post("/products")
def create_product(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    unit: str = Form(...),
    location: str = Form(...),
    phone: str = Form(...),
    whatsapp: str = Form(...),
    images: list[UploadFile] = File(...),

    current_user = Depends(get_current_user),

    db: Session = Depends(get_db),
):
    product = Product(
        title=title,
        description=description,
        category=category,
        price=price,
        quantity=quantity,
        unit=unit,
        location=location,
        phone=phone,
        whatsapp=whatsapp,
        owner_id=current_user.id,
        status="available",
    )

    db.add(product)

    db.commit()

    db.refresh(product)


    # ------------------------------------------------------
    # SAVE PRODUCT IMAGES
    # ------------------------------------------------------

    for image in images:

        if not image.filename:
            continue

        extension = os.path.splitext(
            image.filename
        )[1]

        filename = (
            f"{uuid.uuid4().hex}{extension}"
        )

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename,
        )

        with open(
            filepath,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                image.file,
                buffer,
            )


        db.add(
            ProductImage(
                image_url=filepath,
                product_id=product.id,
            )
        )


    db.commit()

    return {
        "message": "Product created successfully",
        "product_id": product.id,
    }


# ==========================================================
# UPDATE PRODUCT
# ==========================================================

@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    unit: str = Form(...),
    location: str = Form(...),
    phone: str = Form(...),
    whatsapp: str = Form(...),

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db),
):

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.owner_id == current_user.id,
        )
        .first()
    )


    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found or does not belong to this seller.",
        )


    product.title = title
    product.description = description
    product.category = category
    product.price = price
    product.quantity = quantity
    product.unit = unit
    product.location = location
    product.phone = phone
    product.whatsapp = whatsapp


    db.commit()

    db.refresh(product)


    return {
        "message": "Product updated successfully",
        "product_id": product.id,
    }


# ==========================================================
# DELETE PRODUCT
# ==========================================================

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.owner_id == current_user.id,
        )
        .first()
    )


    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found or does not belong to this seller.",
        )


    # ------------------------------------------------------
    # DELETE IMAGE FILES
    # ------------------------------------------------------

    for image in product.images:

        if image.image_url and os.path.exists(
            image.image_url
        ):

            try:
                os.remove(
                    image.image_url
                )

            except OSError:
                pass


    db.delete(product)

    db.commit()


    return {
        "message": "Product deleted successfully",
    }