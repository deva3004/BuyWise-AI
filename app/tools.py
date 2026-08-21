# app/tools.py
#
# Everything an agent is allowed to call lives here: the actual Python
# functions (the allowlist) and the JSON-Schema descriptions handed to the
# LLM. The LLM only ever proposes a name + arguments — TOOL_REGISTRY is
# what decides what's actually permitted to run.

from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.adapters import MockAdapter
from app.database import SessionLocal
from app.models import Offer, ProductVariant, Watchlist
from app.persistence import persist_offers
from app.rag import retrieve_policy_chunks

MIN_SELLER_RATING = 3.0


@dataclass
class OfferSearchResult:
    offers: list[Offer]
    filtered_out_count: int


def _passes_guardrails(offer: Offer) -> bool:
    """Hard rules, enforced in code, before an offer is visible to any
    caller (endpoint or agent). A seller with no rating yet is not the
    same as a seller with a bad rating, so a missing rating does not
    disqualify an offer — only an explicit low rating or is_blocked does.
    """
    seller = offer.seller
    if seller.is_blocked:
        return False
    if seller.rating is not None and seller.rating < MIN_SELLER_RATING:
        return False
    return True


def search_offers(db: Session, variant_id: int) -> OfferSearchResult | None:
    """Core logic shared by the /search endpoint and the search_offers tool.
    Returns None if variant_id doesn't exist, otherwise an OfferSearchResult
    holding the offers that survive the guardrail filter plus a count of how
    many were filtered out (so callers can tell "nothing found" apart from
    "found offers, but none were eligible").
    """
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.variant_id == variant_id)
        .first()
    )
    if variant is None:
        return None

    query = variant.product.name
    if variant.sku:
        query = f"{query} {variant.sku}"

    adapter = MockAdapter()
    normalized_offers = adapter.search(query)
    persist_offers(db, variant_id, normalized_offers)

    all_offers = (
        db.query(Offer)
        .options(joinedload(Offer.seller))
        .filter(Offer.variant_id == variant_id)
        .all()
    )

    eligible_offers = [o for o in all_offers if _passes_guardrails(o)]

    return OfferSearchResult(
        offers=eligible_offers,
        filtered_out_count=len(all_offers) - len(eligible_offers),
    )


def search_offers_tool(variant_id: int) -> dict:
    """Agent-facing wrapper: owns its own DB session (no request context
    to inject one from) and returns plain JSON-serializable data, not ORM
    objects, since this result goes straight into an LLM message.
    """
    db = SessionLocal()
    try:
        result = search_offers(db, variant_id)
        if result is None:
            return {"error": f"No product variant found with variant_id={variant_id}"}

        if not result.offers and result.filtered_out_count > 0:
            return {
                "offers": [],
                "message": (
                    "I found offers, but none met the seller eligibility "
                    "requirements."
                ),
            }

        return {
            "offers": [
                {
                    "seller_id": offer.seller_id,
                    "current_price": float(offer.current_price),
                    "currency": offer.currency,
                    "availability": offer.availability,
                }
                for offer in result.offers
            ]
        }
    finally:
        db.close()


def search_policies_tool(query: str, n_results: int = 3, seller_id: int | None = None) -> dict:
    return {"results": retrieve_policy_chunks(query, n_results=n_results, seller_id=seller_id)}


def get_user_watchlist(db: Session, user_id: int) -> list[Watchlist]:
    """Core logic shared by GET /watchlist and the get_my_watchlist tool."""
    return (
        db.query(Watchlist)
        .options(joinedload(Watchlist.variant).joinedload(ProductVariant.product))
        .filter(Watchlist.user_id == user_id)
        .all()
    )


def get_my_watchlist_tool(user_id: int) -> dict:
    """Agent-facing wrapper. user_id is injected by _execute_tool_call
    from the authenticated request, never taken from the model's own
    arguments (see GetMyWatchlistArgs) - otherwise the agent could be
    talked into reading a different user's watchlist just by being asked.
    """
    db = SessionLocal()
    try:
        items = get_user_watchlist(db, user_id)
        if not items:
            return {
                "watchlist": [],
                "message": "This user has nothing on their watchlist yet.",
            }

        return {
            "watchlist": [
                {
                    "variant_id": item.variant_id,
                    "product_name": item.variant.product.name,
                    "sku": item.variant.sku,
                    "target_price": (
                        float(item.target_price)
                        if item.target_price is not None
                        else None
                    ),
                }
                for item in items
            ]
        }
    finally:
        db.close()


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_offers",
            "description": (
                "Look up current marketplace offers (seller, price, "
                "currency, availability) for a specific product variant."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "variant_id": {
                        "type": "integer",
                        "description": "The internal ID of the product variant to search offers for.",
                    },
                },
                "required": ["variant_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": (
                "Semantically search seller policy text (return, warranty, "
                "shipping, cancellation policies) for content relevant to "
                "a natural-language question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language question about a seller's policy.",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of policy chunks to retrieve.",
                        "default": 3,
                    },
                    "seller_id": {
                        "type": "integer",
                        "description": "Optional seller ID. Use this once you already know the seller_id so policy results are scoped to that seller.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_watchlist",
            "description": (
                "Get the current signed-in user's watchlist - the product "
                "variants they're tracking and their target prices. Use "
                "this when the user refers to 'my watchlist' or something "
                "they're tracking without naming a variant_id directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

TOOL_REGISTRY = {
    "search_offers": search_offers_tool,
    "search_policies": search_policies_tool,
    "get_my_watchlist": get_my_watchlist_tool,
}
