from app.agent import run_agent
from app.database import SessionLocal
from app.models import Seller


MOCK_SELLERS = ["MockSeller A", "MockSeller B", "MockSeller C"]


def _get_or_create_seller(db, name):
    seller = db.query(Seller).filter(Seller.name == name).first()

    if seller is None:
        seller = Seller(name=name, platform="mock", rating=None, is_blocked=False)
        db.add(seller)
        db.flush()

    return seller


def set_seller_state(rating: float, blocked_sellers: set[str] = frozenset()):
    """Fixture setup: force every mock seller into a known rating/blocked
    state before a case runs, so guardrail filtering behaves the same way
    every time regardless of what earlier runs left sitting in the DB.
    """
    db = SessionLocal()

    try:
        for name in MOCK_SELLERS:
            seller = _get_or_create_seller(db, name)
            seller.rating = rating
            seller.is_blocked = name in blocked_sellers

        db.commit()

    finally:
        db.close()


CASES = [
    {
        "name": "all sellers eligible",
        "variant_id": 1,
        "message": "Should I buy product variant_id=1? Give a clear decision.",
        "fixture": lambda: set_seller_state(rating=4.5),
        "expected": {"BUY"},
    },
    {
        "name": "all sellers blocked -> no eligible offers",
        "variant_id": 1,
        "message": "Should I buy product variant_id=1? Give a clear decision.",
        "fixture": lambda: set_seller_state(rating=4.5, blocked_sellers=set(MOCK_SELLERS)),
        "expected": {"WAIT", "RE-EVALUATE"},
    },
]


def main():
    passed = 0

    for i, case in enumerate(CASES, start=1):
        case["fixture"]()

        result = run_agent(case["message"])

        actual = result.decision
        expected = case["expected"]

        if actual in expected:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(
            f"[{status}] Case {i} ({case['name']}): "
            f"expected one of {sorted(expected)}, actual={actual}"
        )
        print(f"    reasoning: {result.reasoning}")

    print(f"\n{passed}/{len(CASES)} cases passed")


if __name__ == "__main__":
    main()
