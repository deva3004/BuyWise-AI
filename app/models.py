from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Numeric,
    Boolean,
    ForeignKey,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id = Column(BigInteger, primary_key=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(100))
    category = Column(String(100))
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    variants = relationship(
        "ProductVariant",
        back_populates="product"
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    variant_id = Column(BigInteger, primary_key=True)

    product_id = Column(
        BigInteger,
        ForeignKey("products.product_id", ondelete="CASCADE"),
        nullable=False
    )

    sku = Column(String(100))

    attributes = Column(
        JSONB,
        nullable=False,
        default=dict
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    product = relationship(
        "Product",
        back_populates="variants"
    )

    offers = relationship(
        "Offer",
        back_populates="variant"
    )

    watchlists = relationship(
        "Watchlist",
        back_populates="variant"
    )


class Seller(Base):
    __tablename__ = "sellers"

    seller_id = Column(BigInteger, primary_key=True)
    name = Column(String(150), nullable=False)
    platform = Column(String(50), nullable=False)
    rating = Column(Numeric(3, 2))
    is_blocked = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    offers = relationship(
        "Offer",
        back_populates="seller"
    )


class Offer(Base):
    __tablename__ = "offers"

    offer_id = Column(BigInteger, primary_key=True)

    variant_id = Column(
        BigInteger,
        ForeignKey(
            "product_variants.variant_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    seller_id = Column(
        BigInteger,
        ForeignKey(
            "sellers.seller_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    current_price = Column(
        Numeric(10, 2),
        nullable=False
    )

    currency = Column(
        String(3),
        nullable=False,
        default="INR"
    )

    availability = Column(
        String(20),
        nullable=False,
        default="unknown"
    )

    product_url = Column(Text)

    last_checked_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    variant = relationship(
        "ProductVariant",
        back_populates="offers"
    )

    seller = relationship(
        "Seller",
        back_populates="offers"
    )

    price_history = relationship(
        "PriceHistory",
        back_populates="offer"
    )

    __table_args__ = (
        UniqueConstraint("variant_id", "seller_id"),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    history_id = Column(BigInteger, primary_key=True)

    offer_id = Column(
        BigInteger,
        ForeignKey(
            "offers.offer_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    price = Column(
        Numeric(10, 2),
        nullable=False
    )

    recorded_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    offer = relationship(
        "Offer",
        back_populates="price_history"
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    watchlist_id = Column(BigInteger, primary_key=True)

    user_id = Column(
        String(100),
        nullable=False
    )

    variant_id = Column(
        BigInteger,
        ForeignKey(
            "product_variants.variant_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    target_price = Column(
        Numeric(10, 2)
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    variant = relationship(
        "ProductVariant",
        back_populates="watchlists"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "variant_id"),
    )