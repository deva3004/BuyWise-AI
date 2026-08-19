from datetime import datetime
from typing import Literal

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


class SearchRequest(BaseModel):
    variant_id: int


class OfferOut(BaseModel):
    offer_id: int
    variant_id: int
    seller_id: int
    current_price: float
    currency: str
    availability: str
    product_url: str | None
    last_checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SellerPolicyCreate(BaseModel):
    seller_id: int
    policy_type: str
    category: str | None = None
    policy_text: str
    source_url: str | None = None


class SellerPolicyOut(BaseModel):
    policy_id: int
    seller_id: int
    policy_type: str
    category: str | None
    policy_text: str
    source_url: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicySearchRequest(BaseModel):
    query: str
    n_results: int = 3
    seller_id: int | None = None


class PolicyChunkOut(BaseModel):
    text: str
    metadata: dict


class AgentRequest(BaseModel):
    message: str


class AgentResponse(BaseModel):
    decision: Literal["BUY", "WAIT", "RE-EVALUATE", "unable_to_decide"]
    reasoning: str