
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db


# Load the dedicated test database URL
env_path = Path(__file__).resolve().parents[1] / ".env.test"
test_url = dotenv_values(env_path).get("DATABASE_URL")

if not test_url:
    raise RuntimeError("DATABASE_URL missing in .env.test")

# Never run these tests against the main database
if make_url(test_url).database != "newtonite_ops_test":
    raise RuntimeError("Refusing to use a non-test database")

test_engine = create_engine(test_url, pool_pre_ping=True)


@pytest.fixture
def db_session():
    # Create a transaction for each test
    with test_engine.connect() as connection:
        transaction = connection.begin()

        try:
            with Session(
                bind=connection,
                autoflush=False,
                join_transaction_mode="create_savepoint"
            ) as session:
                yield session
        finally:
            transaction.rollback()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
