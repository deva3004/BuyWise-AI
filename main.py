from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters import MockAdapter
from app.database import SessionLocal
from app.models import Offer, Product, ProductVariant, Watchlist
from app.persistence import persist_offers
from app.schemas import OfferOut, SearchRequest, WatchlistCreate, WatchlistOut


app = FastAPI()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@app.post("/watchlist", response_model=WatchlistOut)
def create_watchlist(
    watchlist: WatchlistCreate,
    db: Session = Depends(get_db)
):
    variant_exists = (
        db.query(ProductVariant)
        .filter(ProductVariant.variant_id == watchlist.variant_id)
        .first()
    )
    if variant_exists is None:
        raise HTTPException(status_code=404, detail="Product variant not found")

    db_watchlist = Watchlist(
        user_id=watchlist.user_id,
        variant_id=watchlist.variant_id,
        target_price=watchlist.target_price
    )

    db.add(db_watchlist)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This user is already watching this variant"
        )
    db.refresh(db_watchlist)

    return db_watchlist


@app.post("/search", response_model=list[OfferOut])
def search_offers(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.variant_id == request.variant_id)
        .first()
    )
    if variant is None:
        raise HTTPException(status_code=404, detail="Product variant not found")

    query = variant.product.name
    if variant.sku:
        query = f"{query} {variant.sku}"

    adapter = MockAdapter()
    normalized_offers = adapter.search(query)

    persist_offers(db, request.variant_id, normalized_offers)

    offers = (
        db.query(Offer)
        .filter(Offer.variant_id == request.variant_id)
        .all()
    )
    return offers


@app.get("/products/{product_id}/offers", response_model=list[OfferOut])
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
        .join(ProductVariant, Offer.variant_id == ProductVariant.variant_id)
        .filter(ProductVariant.product_id == product_id)
        .all()
    )
    return offers