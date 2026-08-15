# `app/adapters.py`

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NormalizedOffer:
    seller: str
    price: float
    currency: str
    availability: str
    url: str


class PriceSourceAdapter(ABC):

    @abstractmethod
    def search(self, query: str) -> list[NormalizedOffer]:
        """
        Search for a product and return normalized offers.
        """
        pass


class MockAdapter(PriceSourceAdapter):

    def search(self, query: str) -> list[NormalizedOffer]:
        return [
            NormalizedOffer(
                seller="MockSeller A",
                price=44999.0,
                currency="INR",
                availability="in_stock",
                url="https://example.com/product-a",
            ),
            NormalizedOffer(
                seller="MockSeller B",
                price=45999.0,
                currency="INR",
                availability="in_stock",
                url="https://example.com/product-b",
            ),
            NormalizedOffer(
                seller="MockSeller C",
                price=43999.0,
                currency="INR",
                availability="out_of_stock",
                url="https://example.com/product-c",
            ),
        ]
