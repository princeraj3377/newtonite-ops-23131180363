
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User, IdempotencyRecord


# Connect only to the test database
env_path = Path(__file__).resolve().parents[1] / ".env.test"
database_url = dotenv_values(env_path).get("DATABASE_URL")

if not database_url:
    raise RuntimeError("Test DATABASE_URL is missing")

if make_url(database_url).database != "newtonite_ops_test":
    raise RuntimeError("Refusing to use a non-test database")

engine = create_engine(database_url)


@pytest.fixture
def db():
    # Begin an isolated database transaction
    with engine.connect() as connection:
        transaction = connection.begin()

        try:
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint"
            ) as session:
                yield session
        finally:
            transaction.rollback()


def test_idempotency_unique_constraint(db):
    # 1. Create a temporary user
    user = User(
        name="Test User",
        email="pytest@example.com",
        passwaord_hash="test-password-hash"
    )

    db.add(user)
    db.flush()

    # 2. Save the first idempotency record
    first = IdempotencyRecord(
        user_id=user.id,
        key="test-key-001",
        request_hash="a" * 64,
        response_body='{"id": 1}'
    )

    db.add(first)
    db.flush()

    assert first.id is not None

    # 3. Try the same key for the same user
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            duplicate = IdempotencyRecord(
                user_id=user.id,
                key="test-key-001",
                request_hash="a" * 64,
                response_body='{"id": 2}'
            )

            db.add(duplicate)
            db.flush()

    # 4. Verify only one record exists
    records = db.scalars(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user.id,
            IdempotencyRecord.key == "test-key-001"
        )
    ).all()

    assert len(records) == 1
