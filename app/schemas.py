from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    user_id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WatchlistCreate(BaseModel):
    variant_id: int
    target_price: float | None = None


class WatchlistOut(BaseModel):
    watchlist_id: int
    user_id: int
    variant_id: int
    target_price: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    variant_id: int


class ProductOut(BaseModel):
    product_id: int
    name: str
    brand: str | None
    category: str | None

    model_config = ConfigDict(from_attributes=True)


class OfferOut(BaseModel):
    offer_id: int
    variant_id: int
    seller_id: int
    seller_name: str
    current_price: float
    currency: str
    availability: str
    product_url: str | None
    last_checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VariantOut(BaseModel):
    variant_id: int
    product_id: int
    sku: str | None
    attributes: dict

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


class SearchOffersArgs(BaseModel):
    model_config = ConfigDict(strict=True)

    variant_id: int


class SearchPoliciesArgs(BaseModel):
    model_config = ConfigDict(strict=True)

    query: str
    n_results: int = 3
    seller_id: int | None = None


class SubmitDecisionArgs(BaseModel):
    model_config = ConfigDict(strict=True)

    decision: Literal["BUY", "WAIT", "RE-EVALUATE"]
    reasoning: str


class GetMyWatchlistArgs(BaseModel):
    """Deliberately no fields: get_my_watchlist takes no model-supplied
    arguments. Which user's watchlist it returns is injected from the
    authenticated request, never from the LLM - see agent.py.
    """
    model_config = ConfigDict(strict=True)


class AgentResponse(BaseModel):
    decision: Literal["BUY", "WAIT", "RE-EVALUATE", "unable_to_decide"]
    reasoning: str