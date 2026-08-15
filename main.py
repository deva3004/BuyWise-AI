from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ProductVariant, Watchlist
from app.schemas import WatchlistCreate, WatchlistOut


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