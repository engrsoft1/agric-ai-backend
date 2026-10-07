import os
import uuid

import cloudinary
import cloudinary.uploader

from dotenv import load_dotenv

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
from utils.auth import (
    get_current_user,
    get_current_farmer,
    get_current_admin,
)


# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()


# ==========================================================
# CLOUDINARY CONFIGURATION
# ==========================================================

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter(
    prefix="/marketplace",
    tags=["Marketplace"],
)


# ==========================================================
# DATABASE
# ==========================================================

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

    # ------------------------------------------------------
    # CLEAN PHONE NUMBER FOR WHATSAPP
    # ------------------------------------------------------

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
    #
    # 08023456789
    #       ↓
    # 2348023456789
    #
    # Also supports numbers already beginning with 234.

    if whatsapp_number.startswith("0"):

        whatsapp_number = (
            "234" + whatsapp_number[1:]
        )

    elif whatsapp_number.startswith("234"):

        pass

    elif len(whatsapp_number) == 11:

        whatsapp_number = (
            "234" + whatsapp_number
        )

    whatsapp_url = (
        f"https://wa.me/{whatsapp_number}"
        if whatsapp_number
        else None
    )

    # ------------------------------------------------------
    # PHONE URL
    # ------------------------------------------------------

    phone_url = (
        f"tel:{product.phone}"
        if product.phone
        else None
    )

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

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

        # --------------------------------------------------
        # CLOUDINARY IMAGE URLS
        # --------------------------------------------------

        "images": [
            image.image_url
            for image in product.images
            if image.image_url
        ],
    }


# ==========================================================
# GET ALL AVAILABLE PRODUCTS
# SEARCH + FILTER + PAGINATION + SORTING
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
        .filter(
            Product.status == "available"
        )
    )

    # ------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------

    if search:

        search_term = (
            f"%{search.strip()}%"
        )

        query = query.filter(
            Product.title.ilike(search_term)
            |
            Product.description.ilike(search_term)
            |
            Product.category.ilike(search_term)
            |
            Product.location.ilike(search_term)
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

    # ------------------------------------------------------
    # PAGINATION
    # ------------------------------------------------------

    offset = (
        (page - 1) * limit
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

            # --------------------------------------------------
            # CLOUDINARY IMAGE URLS
            # --------------------------------------------------

            "images": [
                image.image_url
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

    current_user=Depends(
        get_current_farmer
    ),

    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # SECURITY CHECK
    # ------------------------------------------------------

    if current_user.id != owner_id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You are not allowed "
                "to view these products."
            ),
        )

    # ------------------------------------------------------
    # GET PRODUCTS
    # ------------------------------------------------------

    products = (
        db.query(Product)
        .filter(
            Product.owner_id == owner_id
        )
        .order_by(
            Product.created_at.desc()
        )
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

            # --------------------------------------------------
            # CLOUDINARY IMAGE URLS
            # --------------------------------------------------

            "images": [
                image.image_url
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

    images: list[UploadFile] = File(
    ...,
    description="Upload one or more product images"
),
    current_user=Depends(
        get_current_farmer
    ),

    db: Session = Depends(get_db),
):

    # ======================================================
    # CREATE PRODUCT
    # ======================================================

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

    # ======================================================
    # UPLOAD IMAGES TO CLOUDINARY
    # ======================================================

    uploaded_images = []

    try:

        for image in images:

            # --------------------------------------------------
            # SKIP EMPTY FILES
            # --------------------------------------------------

            if not image.filename:

                continue

            # --------------------------------------------------
            # UPLOAD TO CLOUDINARY
            # --------------------------------------------------

            upload_result = (
                cloudinary.uploader.upload(

                    image.file,

                    folder="agric-ai/products",

                    public_id=(
                        f"product_{product.id}_"
                        f"{uuid.uuid4().hex}"
                    ),

                    resource_type="image",
                )
            )

            # --------------------------------------------------
            # GET CLOUDINARY DATA
            # --------------------------------------------------

            image_url = upload_result.get(
                "secure_url"
            )

            cloudinary_public_id = upload_result.get(
                "public_id"
            )

            if not image_url:

                raise Exception(
                    "Cloudinary did not return "
                    "a secure image URL."
                )

            if not cloudinary_public_id:

                raise Exception(
                    "Cloudinary did not return "
                    "a public ID."
                )

            # --------------------------------------------------
            # SAVE IMAGE INFORMATION
            # --------------------------------------------------

            product_image = ProductImage(

                image_url=image_url,

                cloudinary_public_id=(
                    cloudinary_public_id
                ),

                product_id=product.id,
            )

            db.add(product_image)
            uploaded_images.append(
                image_url
            )

               # ------------------------------------------------------
        # COMMIT IMAGE RECORDS
        # ------------------------------------------------------

        db.commit()

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Product was created but image "
                "upload failed: "
                f"{str(e)}"
            ),
        )

    # ======================================================
    # RESPONSE
    # ======================================================

    return {

        "message": (
            "Product created successfully"
        ),

        "product_id": product.id,

        "images": uploaded_images,
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

    current_user=Depends(
        get_current_farmer
    ),

    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # FIND PRODUCT
    # ------------------------------------------------------

    product = (
        db.query(Product)
        .filter(

            Product.id == product_id,

            Product.owner_id ==
            current_user.id,

        )
        .first()
    )

    if not product:

        raise HTTPException(

            status_code=404,

            detail=(
                "Product not found or does not "
                "belong to this seller."
            ),
        )

    # ------------------------------------------------------
    # UPDATE PRODUCT
    # ------------------------------------------------------

    product.title = title

    product.description = description

    product.category = category

    product.price = price

    product.quantity = quantity

    product.unit = unit

    product.location = location

    product.phone = phone

    product.whatsapp = whatsapp

    # ------------------------------------------------------
    # SAVE
    # ------------------------------------------------------

    db.commit()

    db.refresh(product)

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    return {

        "message": (
            "Product updated successfully"
        ),

        "product_id": product.id,
    }

# ==========================================================
# DELETE PRODUCT
# ==========================================================

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user=Depends(
        get_current_farmer
    ),
    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # FIND PRODUCT
    # ------------------------------------------------------

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
            detail="Product not found or you are not the owner.",
        )

    # ------------------------------------------------------
    # GET PRODUCT IMAGES
    # ------------------------------------------------------

    product_images = (
        db.query(ProductImage)
        .filter(
            ProductImage.product_id == product.id
        )
        .all()
    )

    # ------------------------------------------------------
    # DELETE IMAGES FROM CLOUDINARY
    # ------------------------------------------------------

    cloudinary_errors = []

    for product_image in product_images:

        public_id = (
            product_image.cloudinary_public_id
        )

        # Older images may not have a public ID
        if not public_id:
            continue

        try:

            result = cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
            )

            if result.get("result") not in [
                "ok",
                "not found",
            ]:

                cloudinary_errors.append({
                    "public_id": public_id,
                    "result": result,
                })

        except Exception as e:

            cloudinary_errors.append({
                "public_id": public_id,
                "error": str(e),
            })

    # ------------------------------------------------------
    # DELETE PRODUCT FROM DATABASE
    # ------------------------------------------------------

    db.delete(product)

    db.commit()

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    response = {
        "message": "Product deleted successfully.",
        "product_id": product_id,
    }

    # ------------------------------------------------------
    # CLOUDINARY WARNINGS
    # ------------------------------------------------------

    if cloudinary_errors:
        response["cloudinary_warnings"] = cloudinary_errors

    return response


# ==========================================================
# ADMIN DELETE ANY PRODUCT
# ==========================================================

@router.delete("/admin/products/{product_id}")
def admin_delete_product(
    product_id: int,
    current_user=Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # FIND PRODUCT
    # ------------------------------------------------------

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    # ------------------------------------------------------
    # GET PRODUCT IMAGES
    # ------------------------------------------------------

    product_images = (
        db.query(ProductImage)
        .filter(
            ProductImage.product_id == product.id
        )
        .all()
    )

    # ------------------------------------------------------
    # DELETE IMAGES FROM CLOUDINARY
    # ------------------------------------------------------

    cloudinary_errors = []

    for product_image in product_images:

        public_id = (
            product_image.cloudinary_public_id
        )

        # Older images may not have a public ID
        if not public_id:
            continue

        try:

            result = cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
            )

            if result.get("result") not in [
                "ok",
                "not found",
            ]:

                cloudinary_errors.append({
                    "public_id": public_id,
                    "result": result,
                })

        except Exception as e:

            cloudinary_errors.append({
                "public_id": public_id,
                "error": str(e),
            })

    # ------------------------------------------------------
    # DELETE PRODUCT FROM DATABASE
    # ------------------------------------------------------

    db.delete(product)

    db.commit()

    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    response = {
        "message": (
            "Product deleted successfully by admin."
        ),
        "product_id": product_id,
        "deleted_by_admin": current_user.id,
    }

    # ------------------------------------------------------
    # CLOUDINARY WARNINGS
    # ------------------------------------------------------

    if cloudinary_errors:
        response["cloudinary_warnings"] = (
            cloudinary_errors
        )

    return response

