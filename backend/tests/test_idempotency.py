
from app.schemas import WorkItemCreate
from app.idempotency import create_request_hash


def make_item(title="Payment Failed"):
    return WorkItemCreate(
        title=title,
        description="Gateway error",
        item_type="payment",
        priority="high",
        team_id=1
    )


def test_same_request_same_hash():
    first = make_item()
    second = make_item()

    assert create_request_hash(first) == create_request_hash(second)


def test_different_request_different_hash():
    first = make_item("Payment Failed")
    second = make_item("Server Failed")

    assert create_request_hash(first) != create_request_hash(second)


def test_hash_length():
    item = make_item()

    result = create_request_hash(item)

    assert len(result) == 64
