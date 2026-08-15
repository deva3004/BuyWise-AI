# app/persistence.py

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters import NormalizedOffer
from app.models import Seller, Offer, PriceHistory


def persist_offers(
    db: Session,
    variant_id: int,
    offers: list[NormalizedOffer],
) -> None:

    for normalized_offer in offers:

        # 1. Get-or-create the seller
        seller = (
            db.query(Seller)
            .filter(Seller.name == normalized_offer.seller)
            .first()
        )

        if seller is None:
            seller = Seller(
                name=normalized_offer.seller,
                platform="mock",
                rating=None,
                is_blocked=False,
            )

            db.add(seller)
            db.flush()

        # 2. Find the existing offer for this variant + seller
        offer = (
            db.query(Offer)
            .filter(
                Offer.variant_id == variant_id,
                Offer.seller_id == seller.seller_id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if offer is None:
            # No existing offer → create one
            offer = Offer(
                variant_id=variant_id,
                seller_id=seller.seller_id,
                current_price=normalized_offer.price,
                currency=normalized_offer.currency,
                availability=normalized_offer.availability,
                product_url=normalized_offer.url,
                last_checked_at=now,
            )

            db.add(offer)

        else:
            # Existing offer → update current state
            offer.current_price = normalized_offer.price
            offer.currency = normalized_offer.currency
            offer.availability = normalized_offer.availability
            offer.product_url = normalized_offer.url
            offer.last_checked_at = now

        # Make sure offer_id exists before creating PriceHistory
        db.flush()

        # 3. Always record a price observation
        price_history = PriceHistory(
            offer_id=offer.offer_id,
            price=normalized_offer.price,
            recorded_at=now,
        )

        db.add(price_history)

    # Commit all changes together
    db.commit()
