from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.exc import IntegrityError 
from sqlalchemy.orm import Session

from app.agent import run_agent
from app.database import SessionLocal
from app.models import Offer, Product, ProductVariant, Seller, SellerPolicy, Watchlist
from app.rag import embed_policy, retrieve_policy_chunks
from app.tools import search_offers as search_offers_core
from app.schemas import (
    AgentRequest,
    AgentResponse,
    OfferOut,
    PolicyChunkOut,
    PolicySearchRequest,
    SearchRequest,
    SellerPolicyCreate,
    SellerPolicyOut,
    WatchlistCreate,
    WatchlistOut,
)


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
    result = search_offers_core(db, request.variant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product variant not found")

    return result.offers


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


@app.post("/seller-policies", response_model=SellerPolicyOut)
def create_seller_policy(
    policy: SellerPolicyCreate,
    db: Session = Depends(get_db)
):
    seller_exists = (
        db.query(Seller)
        .filter(Seller.seller_id == policy.seller_id)
        .first()
    )
    if seller_exists is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    db_policy = SellerPolicy(
        seller_id=policy.seller_id,
        policy_type=policy.policy_type,
        category=policy.category,
        policy_text=policy.policy_text,
        source_url=policy.source_url,
    )

    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)

    # Postgres write is the source of truth; embed into Chroma right after
    # so the vector index stays in sync with what was just persisted.
    embed_policy(db_policy)

    return db_policy


@app.post("/seller-policies/search", response_model=list[PolicyChunkOut])
def search_seller_policies(request: PolicySearchRequest):
    return retrieve_policy_chunks(request.query, n_results=request.n_results)


@app.post("/agent", response_model=AgentResponse)
def ask_agent(request: AgentRequest):
    answer = run_agent(request.message)
    return AgentResponse(answer=answer)