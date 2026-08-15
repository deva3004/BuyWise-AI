from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WatchlistCreate(BaseModel):
    user_id: str
    variant_id: int
    target_price: float | None = None


class WatchlistOut(BaseModel):
    watchlist_id: int
    user_id: str
    variant_id: int
    target_price: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)