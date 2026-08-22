from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.dependencies import get_db
from app.models import ProductVariant, Watchlist
from app.rate_limit import limit_by_user, watchlist_limiter
from app.schemas import WatchlistCreate, WatchlistOut
from app.tools import get_user_watchlist

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.post(
    "",
    response_model=WatchlistOut,
    dependencies=[Depends(limit_by_user(watchlist_limiter))],
)
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


@router.get(
    "",
    response_model=list[WatchlistOut],
    dependencies=[Depends(limit_by_user(watchlist_limiter))],
)
def list_watchlist(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return get_user_watchlist(db, user_id)
