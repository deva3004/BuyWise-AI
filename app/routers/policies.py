from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Seller, SellerPolicy
from app.rag import embed_policy, retrieve_policy_chunks
from app.schemas import (
    PolicyChunkOut,
    PolicySearchRequest,
    SellerPolicyCreate,
    SellerPolicyOut,
)

router = APIRouter(prefix="/seller-policies", tags=["seller-policies"])


@router.post("", response_model=SellerPolicyOut)
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


@router.post("/search", response_model=list[PolicyChunkOut])
def search_seller_policies(request: PolicySearchRequest):
    return retrieve_policy_chunks(
        request.query, n_results=request.n_results, seller_id=request.seller_id
    )
