
import uuid

import pytest
from sqlalchemy import select, func

from app.auth import create_access_token
from app.models import (
    User,
    Team,
    Membership,
    WorkItem
)


@pytest.fixture
def authenticated_client(client, db_session):
    # Create a unique test user
    unique_id = uuid.uuid4().hex

    user = User(
        name="API Test User",
        email=f"test-{unique_id}@example.com",
        passwaord_hash="test-hash"
    )

    db_session.add(user)
    db_session.flush()

    # Create a test team
    team = Team(
        name=f"Test Team {unique_id}"
    )

    db_session.add(team)
    db_session.flush()

    # Give user permission to create items
    membership = Membership(
        user_id=user.id,
        team_id=team.id,
        role="admin"
    )

    db_session.add(membership)
    db_session.flush()

    # Generate a real JWT token
    token = create_access_token(user.id)

    client.headers.update({
        "Authorization": f"Bearer {token}"
    })

    yield client, db_session, team.id

    client.headers.pop("Authorization", None)


def make_payload(team_id):
    return {
        "title": "Payment Gateway Failure",
        "description": "Payment processing error",
        "item_type": "payment",
        "priority": "high",
        "team_id": team_id
    }


def test_new_key_creates_work_item(authenticated_client):
    client, db, team_id = authenticated_client

    response = client.post(
        "/items",
        headers={"Idempotency-Key": "test-new-key"},
        json=make_payload(team_id)
    )

    assert response.status_code == 201, response.text
    assert response.json()["title"] == "Payment Gateway Failure"


def test_same_key_returns_same_item(authenticated_client):
    client, db, team_id = authenticated_client

    headers = {"Idempotency-Key": "test-same-key"}
    payload = make_payload(team_id)

    first = client.post(
        "/items",
        headers=headers,
        json=payload
    )

    second = client.post(
        "/items",
        headers=headers,
        json=payload
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    assert first_id == second_id

    count = db.scalar(
        select(func.count())
        .select_from(WorkItem)
        .where(WorkItem.id == first_id)
    )

    assert count == 1


def test_same_key_different_body_returns_409(authenticated_client):
    client, db, team_id = authenticated_client

    headers = {"Idempotency-Key": "test-conflict-key"}

    first_payload = make_payload(team_id)

    second_payload = make_payload(team_id)
    second_payload["title"] = "Different Payment Issue"

    first = client.post(
        "/items",
        headers=headers,
        json=first_payload
    )

    second = client.post(
        "/items",
        headers=headers,
        json=second_payload
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
