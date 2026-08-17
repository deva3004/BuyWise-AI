# app/tools.py
#
# Everything an agent is allowed to call lives here: the actual Python
# functions (the allowlist) and the JSON-Schema descriptions handed to the
# LLM. The LLM only ever proposes a name + arguments — TOOL_REGISTRY is
# what decides what's actually permitted to run.

from sqlalchemy.orm import Session

from app.adapters import MockAdapter
from app.database import SessionLocal
from app.models import Offer, ProductVariant
from app.persistence import persist_offers
from app.rag import retrieve_policy_chunks


def search_offers(db: Session, variant_id: int) -> list[Offer] | None:
    """Core logic shared by the /search endpoint and the search_offers tool.
    Returns None if variant_id doesn't exist, otherwise the persisted offers.
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

    return (
        db.query(Offer)
        .filter(Offer.variant_id == variant_id)
        .all()
    )


def search_offers_tool(variant_id: int) -> dict:
    """Agent-facing wrapper: owns its own DB session (no request context
    to inject one from) and returns plain JSON-serializable data, not ORM
    objects, since this result goes straight into an LLM message.
    """
    db = SessionLocal()
    try:
        offers = search_offers(db, variant_id)
        if offers is None:
            return {"error": f"No product variant found with variant_id={variant_id}"}

        return {
            "offers": [
                {
                    "seller_id": offer.seller_id,
                    "current_price": float(offer.current_price),
                    "currency": offer.currency,
                    "availability": offer.availability,
                }
                for offer in offers
            ]
        }
    finally:
        db.close()


def search_policies_tool(query: str, n_results: int = 3) -> dict:
    return {"results": retrieve_policy_chunks(query, n_results=n_results)}


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
                },
                "required": ["query"],
            },
        },
    },
]

TOOL_REGISTRY = {
    "search_offers": search_offers_tool,
    "search_policies": search_policies_tool,
}
