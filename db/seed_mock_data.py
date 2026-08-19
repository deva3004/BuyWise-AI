"""db/seed_mock_data.py — one-time mock catalog seed for local development.

Writes products/variants/sellers/offers/price_history/seller_policies
directly to Postgres via SQLAlchemy, bypassing MockAdapter and
persist_offers entirely. That's deliberate: MockAdapter always returns
the same 3 fixed offers regardless of query, so a rich, varied catalog
has to be seeded directly rather than generated through the adapter
path. Seller policies are embedded into Chroma immediately after commit,
the same way POST /seller-policies does it.

Run once against an empty DB: `uv run python db/seed_mock_data.py`.
Refuses to run again if any products already exist, to avoid duplicate
rows and duplicate Chroma embeddings.
"""

import random
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import Offer, PriceHistory, Product, ProductVariant, Seller, SellerPolicy
from app.rag import embed_policy

random.seed(42)

# Ratings are deliberately mixed: a couple below MIN_SELLER_RATING (3.0,
# see app/tools.py), one is_blocked despite a decent rating, and one with
# no rating at all yet — so the guardrail filter actually has something
# to filter when browsing seeded data, not just an all-eligible catalog.
SELLERS = [
    {"name": "TechBazaar", "platform": "flipkart", "rating": 4.6, "is_blocked": False},
    {"name": "ClickMart", "platform": "amazon", "rating": 4.2, "is_blocked": False},
    {"name": "PrimeGadgets", "platform": "amazon", "rating": 4.8, "is_blocked": False},
    {"name": "ValueElectro", "platform": "meesho", "rating": 2.4, "is_blocked": False},
    {"name": "QuickCart", "platform": "flipkart", "rating": 3.9, "is_blocked": False},
    {"name": "MegaDeals", "platform": "website", "rating": 1.8, "is_blocked": False},
    {"name": "TrustedTech", "platform": "amazon", "rating": 4.5, "is_blocked": False},
    {"name": "BudgetBox", "platform": "meesho", "rating": 3.6, "is_blocked": True},
    {"name": "EliteElectronics", "platform": "website", "rating": 4.9, "is_blocked": False},
    {"name": "FastShop", "platform": "flipkart", "rating": None, "is_blocked": False},
]

PRODUCTS = [
    {"name": "iPhone 15", "brand": "Apple", "category": "Smartphones", "variants": [
        {"sku": "IPH15-128-BLK", "attributes": {"storage": "128GB", "color": "Black"}, "base_price": 69900},
        {"sku": "IPH15-256-BLU", "attributes": {"storage": "256GB", "color": "Blue"}, "base_price": 79900},
    ]},
    {"name": "iPhone 15 Pro", "brand": "Apple", "category": "Smartphones", "variants": [
        {"sku": "IPH15P-256-TIT", "attributes": {"storage": "256GB", "color": "Titanium"}, "base_price": 134900},
    ]},
    {"name": "Galaxy S24", "brand": "Samsung", "category": "Smartphones", "variants": [
        {"sku": "GS24-128-ONX", "attributes": {"storage": "128GB", "color": "Onyx Black"}, "base_price": 74999},
        {"sku": "GS24-256-AMB", "attributes": {"storage": "256GB", "color": "Amber Yellow"}, "base_price": 79999},
    ]},
    {"name": "Galaxy S24 Ultra", "brand": "Samsung", "category": "Smartphones", "variants": [
        {"sku": "GS24U-256-GRY", "attributes": {"storage": "256GB", "color": "Titanium Gray"}, "base_price": 129999},
    ]},
    {"name": "Pixel 8", "brand": "Google", "category": "Smartphones", "variants": [
        {"sku": "PIX8-128-OBS", "attributes": {"storage": "128GB", "color": "Obsidian"}, "base_price": 75999},
    ]},
    {"name": "OnePlus 12", "brand": "OnePlus", "category": "Smartphones", "variants": [
        {"sku": "OP12-256-EMR", "attributes": {"storage": "256GB", "color": "Flowy Emerald"}, "base_price": 64999},
    ]},
    {"name": "MacBook Air M2", "brand": "Apple", "category": "Laptops", "variants": [
        {"sku": "MBA-M2-8-256", "attributes": {"ram": "8GB", "storage": "256GB", "color": "Midnight"}, "base_price": 114900},
        {"sku": "MBA-M2-16-512", "attributes": {"ram": "16GB", "storage": "512GB", "color": "Starlight"}, "base_price": 144900},
    ]},
    {"name": "MacBook Pro 14", "brand": "Apple", "category": "Laptops", "variants": [
        {"sku": "MBP14-16-512", "attributes": {"ram": "16GB", "storage": "512GB", "color": "Space Black"}, "base_price": 199900},
    ]},
    {"name": "Dell XPS 13", "brand": "Dell", "category": "Laptops", "variants": [
        {"sku": "XPS13-16-512", "attributes": {"ram": "16GB", "storage": "512GB", "color": "Platinum"}, "base_price": 129990},
    ]},
    {"name": "ThinkPad X1 Carbon Gen 12", "brand": "Lenovo", "category": "Laptops", "variants": [
        {"sku": "X1C12-16-1TB", "attributes": {"ram": "16GB", "storage": "1TB", "color": "Black"}, "base_price": 159990},
    ]},
    {"name": "Galaxy Book4", "brand": "Samsung", "category": "Laptops", "variants": [
        {"sku": "GB4-16-512", "attributes": {"ram": "16GB", "storage": "512GB", "color": "Silver"}, "base_price": 84990},
    ]},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "category": "Headphones", "variants": [
        {"sku": "WH1000XM5-BLK", "attributes": {"color": "Black"}, "base_price": 29990},
        {"sku": "WH1000XM5-SLV", "attributes": {"color": "Silver"}, "base_price": 29990},
    ]},
    {"name": "AirPods Pro 2", "brand": "Apple", "category": "Headphones", "variants": [
        {"sku": "APP2-USBC", "attributes": {"connector": "USB-C"}, "base_price": 24900},
    ]},
    {"name": "Bose QuietComfort Ultra", "brand": "Bose", "category": "Headphones", "variants": [
        {"sku": "BOSE-QCU-BLK", "attributes": {"color": "Black"}, "base_price": 34900},
    ]},
    {"name": "Galaxy Watch6", "brand": "Samsung", "category": "Smartwatches", "variants": [
        {"sku": "GW6-40-GRP", "attributes": {"size": "40mm", "color": "Graphite"}, "base_price": 29999},
        {"sku": "GW6-44-SLV", "attributes": {"size": "44mm", "color": "Silver"}, "base_price": 32999},
    ]},
    {"name": "Apple Watch Series 9", "brand": "Apple", "category": "Smartwatches", "variants": [
        {"sku": "AWS9-41-MID", "attributes": {"size": "41mm", "color": "Midnight"}, "base_price": 41900},
    ]},
]

POLICIES = [
    {"seller": "TechBazaar", "policy_type": "return_policy", "category": "electronics", "policy_text": (
        "Items can be returned within 10 days of delivery if they are unused and in original "
        "packaging. Refunds are processed to the original payment method within 5-7 business "
        "days after the returned item passes inspection."
    )},
    {"seller": "TechBazaar", "policy_type": "warranty", "category": "electronics", "policy_text": (
        "All electronics sold through TechBazaar carry the standard 1-year manufacturer "
        "warranty. TechBazaar does not offer any extended warranty beyond what the "
        "manufacturer provides."
    )},
    {"seller": "ClickMart", "policy_type": "return_policy", "category": "electronics", "policy_text": (
        "ClickMart accepts returns within 7 days of delivery for a full refund, provided the "
        "product is unopened. Opened electronics can only be exchanged for a replacement of "
        "the same item, not refunded."
    )},
    {"seller": "ClickMart", "policy_type": "shipping", "category": None, "policy_text": (
        "Standard shipping takes 3-5 business days across most of India. Express shipping "
        "(1-2 business days) is available at checkout for an additional fee in metro cities."
    )},
    {"seller": "PrimeGadgets", "policy_type": "return_policy", "category": "electronics", "policy_text": (
        "PrimeGadgets offers a 15-day hassle-free return window on all electronics. Customers "
        "do not need to give a reason for return, and pickup is arranged free of charge."
    )},
    {"seller": "PrimeGadgets", "policy_type": "warranty", "category": "electronics", "policy_text": (
        "In addition to the manufacturer's warranty, PrimeGadgets provides a complimentary "
        "6-month extended protection plan on laptops and smartphones purchased through the "
        "platform."
    )},
    {"seller": "QuickCart", "policy_type": "cancellation_policy", "category": None, "policy_text": (
        "Orders can be cancelled free of charge any time before the item is shipped. Once an "
        "order has been dispatched, it cannot be cancelled and must instead be returned after "
        "delivery."
    )},
    {"seller": "TrustedTech", "policy_type": "return_policy", "category": "electronics", "policy_text": (
        "TrustedTech allows returns within 10 days for a full refund on unopened items. Opened "
        "items are eligible for store credit only, valid for 90 days."
    )},
    {"seller": "EliteElectronics", "policy_type": "warranty", "category": "electronics", "policy_text": (
        "EliteElectronics honors the full manufacturer warranty on every product and "
        "additionally offers on-site technician support for laptops during the first 90 days "
        "after purchase, free of charge."
    )},
    {"seller": "FastShop", "policy_type": "shipping", "category": None, "policy_text": (
        "FastShop ships from regional warehouses, so delivery times vary between 2 and 6 "
        "business days depending on the buyer's location. Tracking information is emailed as "
        "soon as the order is dispatched."
    )},
]

def main():
    db = SessionLocal()

    try:
        if db.query(Product).first() is not None:
            print("Products already exist — refusing to seed again. Nothing changed.")
            return

        seller_rows = {}
        for s in SELLERS:
            seller = Seller(name=s["name"], platform=s["platform"], rating=s["rating"], is_blocked=s["is_blocked"])
            db.add(seller)
            seller_rows[s["name"]] = seller
        db.flush()

        now = datetime.now(timezone.utc)
        variant_count = 0
        offer_count = 0
        history_count = 0

        for p in PRODUCTS:
            product = Product(name=p["name"], brand=p["brand"], category=p["category"])
            db.add(product)
            db.flush()

            for v in p["variants"]:
                variant = ProductVariant(product_id=product.product_id, sku=v["sku"], attributes=v["attributes"])
                db.add(variant)
                db.flush()
                variant_count += 1

                offer_sellers = random.sample(SELLERS, k=random.randint(2, 4))
                for s in offer_sellers:
                    seller = seller_rows[s["name"]]
                    price = round(v["base_price"] * random.uniform(0.93, 1.09), 2)
                    availability = random.choices(["in_stock", "out_of_stock"], weights=[85, 15])[0]

                    offer = Offer(
                        variant_id=variant.variant_id,
                        seller_id=seller.seller_id,
                        current_price=price,
                        currency="INR",
                        availability=availability,
                        product_url=f"https://example.com/{s['name'].lower()}/{v['sku'].lower()}",
                        last_checked_at=now,
                    )
                    db.add(offer)
                    db.flush()
                    offer_count += 1

                    db.add(PriceHistory(offer_id=offer.offer_id, price=round(price * random.uniform(1.0, 1.05), 2), recorded_at=now - timedelta(days=3)))
                    db.add(PriceHistory(offer_id=offer.offer_id, price=price, recorded_at=now))
                    history_count += 2

        db.commit()

        policy_count = 0
        for pol in POLICIES:
            seller = seller_rows[pol["seller"]]
            policy = SellerPolicy(
                seller_id=seller.seller_id,
                policy_type=pol["policy_type"],
                category=pol["category"],
                policy_text=pol["policy_text"],
                source_url=None,
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
            embed_policy(policy)
            policy_count += 1

        print(
            f"Seeded {len(SELLERS)} sellers, {len(PRODUCTS)} products, {variant_count} variants, "
            f"{offer_count} offers, {history_count} price-history rows, {policy_count} seller "
            f"policies (embedded into Chroma)."
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
