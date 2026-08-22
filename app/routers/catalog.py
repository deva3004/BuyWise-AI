from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_db
from app.models import Offer, Product, ProductVariant
from app.schemas import OfferOut, ProductOut, SearchRequest, VariantOut
from app.tools import search_offers as search_offers_core

router = APIRouter(tags=["catalog"])


@router.post("/search", response_model=list[OfferOut])
def search_offers(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    result = search_offers_core(db, request.variant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product variant not found")

    return result.offers


@router.get("/products/search", response_model=list[ProductOut])
def search_products(
    q: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    return (
        db.query(Product)
        .filter(or_(Product.name.ilike(f"%{q}%"), Product.brand.ilike(f"%{q}%")))
        .limit(limit)
        .all()
    )


@router.get("/products/{product_id}/offers", response_model=list[OfferOut])
def get_product_offers(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = (
        db.query(Product)
        .filter(Product.product_id == product_id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    offers = (
        db.query(Offer)
        .options(joinedload(Offer.seller))
        .join(ProductVariant, Offer.variant_id == ProductVariant.variant_id)
        .filter(ProductVariant.product_id == product_id)
        .all()
    )
    return offers


@router.get("/products/{product_id}/variants", response_model=list[VariantOut])
def get_product_variants(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = (
        db.query(Product)
        .filter(Product.product_id == product_id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return (
        db.query(ProductVariant)
        .filter(ProductVariant.product_id == product_id)
        .all()
    )
