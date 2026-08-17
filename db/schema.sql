-- Abstract product (e.g. "iPhone 15") — no price, no stock. Those belong
-- further down the chain because they vary by variant AND by seller AND by time.
CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The actually-purchasable SKU (e.g. "iPhone 15, 128GB, Blue").
-- attributes is JSONB because different product categories have different
-- variant dimensions (storage/color for phones, size/color for shoes, etc.)
-- — modeling every possible attribute as its own column doesn't scale.
CREATE TABLE product_variants (
    variant_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    sku VARCHAR(100),
    attributes JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Who is offering a variant for sale. rating/is_blocked exist specifically
-- so the guardrail layer (Phase 3, Day 8) can filter on hard rules in code
-- BEFORE the agent/LLM ever sees the offer.
CREATE TABLE sellers (
    seller_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    rating NUMERIC(3, 2),
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A specific seller's CURRENT listing for a specific variant. One row per
-- (variant, seller) pair — updated in place as price/availability change.
CREATE TABLE offers (
    offer_id BIGSERIAL PRIMARY KEY,
    variant_id BIGINT NOT NULL REFERENCES product_variants(variant_id) ON DELETE CASCADE,
    seller_id BIGINT NOT NULL REFERENCES sellers(seller_id) ON DELETE CASCADE,
    current_price NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    availability VARCHAR(20) NOT NULL DEFAULT 'unknown',
    product_url TEXT,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (variant_id, seller_id)
);

-- Append-only time series of what an offer's price was at each check.
-- Never updated in place — a new row per observed price, so we can chart
-- price history and compute "is this actually a good deal right now."
CREATE TABLE price_history (
    history_id BIGSERIAL PRIMARY KEY,
    offer_id BIGINT NOT NULL REFERENCES offers(offer_id) ON DELETE CASCADE,
    price NUMERIC(10, 2) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Free-text seller policy content (return/warranty/shipping/cancellation).
-- Source of truth for the RAG layer: Postgres holds the raw text,
-- ChromaDB holds a derived, rebuildable vector index over chunks of it.
-- category is nullable — NULL means the policy applies to all of the
-- seller's products; a value scopes it to one product category.
CREATE TABLE seller_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL REFERENCES sellers(seller_id) ON DELETE CASCADE,
    policy_type VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    policy_text TEXT NOT NULL,
    source_url TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- What a user is tracking. user_id is a plain string for now — no auth
-- system in scope yet, just a stable identifier.
CREATE TABLE watchlists (
    watchlist_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    variant_id BIGINT NOT NULL REFERENCES product_variants(variant_id) ON DELETE CASCADE,
    target_price NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, variant_id)
);
