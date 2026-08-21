from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.agent import run_agent
from app.auth import create_access_token, get_current_user_id, hash_password, verify_password
from app.database import SessionLocal
from app.models import Offer, Product, ProductVariant, Seller, SellerPolicy, User, Watchlist
from app.rag import embed_policy, retrieve_policy_chunks
from app.tools import get_user_watchlist, search_offers as search_offers_core
from app.schemas import (
    AgentRequest,
    AgentResponse,
    LoginRequest,
    OfferOut,
    PolicyChunkOut,
    PolicySearchRequest,
    ProductOut,
    SearchRequest,
    SellerPolicyCreate,
    SellerPolicyOut,
    Token,
    UserCreate,
    UserOut,
    VariantOut,
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


@app.post("/auth/signup", response_model=UserOut, status_code=201)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        username=user.username,
        password_hash=hash_password(user.password),
    )

    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    db.refresh(db_user)

    return db_user


@app.post("/auth/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    db_user = (
        db.query(User)
        .filter(User.username == request.username)
        .first()
    )
    if db_user is None or not verify_password(request.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return Token(access_token=create_access_token(db_user.user_id))


@app.post("/watchlist", response_model=WatchlistOut)
def create_watchlist(
    watchlist: WatchlistCreate,
    user_id: int = Depends(get_current_user_id),
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
        user_id=user_id,
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
            detail="You're already watching this variant"
        )
    db.refresh(db_watchlist)

    return db_watchlist


@app.get("/watchlist", response_model=list[WatchlistOut])
def list_watchlist(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return get_user_watchlist(db, user_id)


@app.post("/search", response_model=list[OfferOut])
def search_offers(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    result = search_offers_core(db, request.variant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product variant not found")

    return result.offers


@app.get("/products/search", response_model=list[ProductOut])
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
        .options(joinedload(Offer.seller))
        .join(ProductVariant, Offer.variant_id == ProductVariant.variant_id)
        .filter(ProductVariant.product_id == product_id)
        .all()
    )
    return offers


@app.get("/products/{product_id}/variants", response_model=list[VariantOut])
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
    return retrieve_policy_chunks(request.query, n_results=request.n_results, seller_id=request.seller_id)


@app.post("/agent", response_model=AgentResponse)
def ask_agent(
    request: AgentRequest,
    user_id: int = Depends(get_current_user_id),
):
    decision = run_agent(request.message, user_id=user_id)
    return AgentResponse(decision=decision.decision, reasoning=decision.reasoning)