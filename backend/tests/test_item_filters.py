import uuid

import pytest

from app.auth import create_access_token
from app.models import Membership, Team, User, WorkItem


@pytest.fixture
def workspace(client, db_session):
    unique = uuid.uuid4().hex
    user = User(name="Filter user", email=f"filters-{unique}@example.com", passwaord_hash="unused")
    team = Team(name=f"Filter team {unique}")
    other = Team(name=f"Other team {unique}")
    viewer = Team(name=f"Viewer team {unique}")
    db_session.add_all([user, team, other, viewer])
    db_session.flush()
    db_session.add_all([
        Membership(user_id=user.id, team_id=team.id, role="admin"),
        Membership(user_id=user.id, team_id=viewer.id, role="viewer"),
    ])
    items = [
        WorkItem(title="Payment gateway", description="Checkout failure", item_type="payment", priority="high", status="open", team_id=team.id, created_by=user.id),
        WorkItem(title="Deploy task", description="PAYMENT follow-up", item_type="task", priority="low", status="in_progress", team_id=team.id, created_by=user.id),
        WorkItem(title="100%_complete", description="Literal characters", item_type="task", priority="high", status="resolved", team_id=team.id, created_by=user.id),
        WorkItem(title="Payment gateway", description="Other team's private item", item_type="payment", priority="high", status="open", team_id=other.id, created_by=user.id),
    ]
    db_session.add_all(items)
    db_session.flush()
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"
    yield client, team, other, viewer, items
    client.headers.pop("Authorization", None)


def test_team_list_contains_only_memberships_and_permissions(workspace):
    client, team, other, viewer, _ = workspace
    response = client.get("/teams")
    assert response.status_code == 200
    teams = {entry["id"]: entry for entry in response.json()}
    assert set(teams) == {team.id, viewer.id}
    assert other.id not in teams
    assert "create" in teams[team.id]["permissions"]
    assert teams[viewer.id]["permissions"] == ["view"]


def test_list_is_team_scoped_newest_first_and_contains_ui_fields(workspace):
    client, team, _, _, items = workspace
    response = client.get("/items", params={"team_id": team.id})
    assert response.status_code == 200
    rows = response.json()
    assert [item["id"] for item in rows] == [items[2].id, items[1].id, items[0].id]
    assert {"item_type", "created_at", "assignee_id", "version"} <= rows[0].keys()


@pytest.mark.parametrize("filters,indexes", [
    ({"q": "  pAyMeNt  "}, [1, 0]),
    ({"status": "in_progress"}, [1]),
    ({"priority": "high"}, [2, 0]),
    ({"item_type": "task"}, [2, 1]),
    ({"q": "gateway", "status": "open", "priority": "high", "item_type": "payment"}, [0]),
    ({"q": "%_"}, [2]),
    ({"q": "no matching item"}, []),
])
def test_item_filters(workspace, filters, indexes):
    client, team, _, _, items = workspace
    response = client.get("/items", params={"team_id": team.id, **filters})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [items[index].id for index in indexes]


@pytest.mark.parametrize("filters", [
    {"status": "invalid"}, {"priority": "urgent"}, {"item_type": "unknown"}, {"q": "x" * 201}, {"team_id": 0},
])
def test_invalid_filters_are_rejected(workspace, filters):
    client, team, _, _, _ = workspace
    assert client.get("/items", params={"team_id": team.id, **filters}).status_code == 422


def test_other_teams_cannot_be_queried_even_with_filters(workspace):
    client, _, other, _, _ = workspace
    assert client.get("/items", params={"team_id": other.id, "q": "Payment"}).status_code == 403


def test_viewer_can_read_but_not_create(workspace):
    client, _, _, viewer, _ = workspace
    assert client.get("/items", params={"team_id": viewer.id}).json() == []
    response = client.post("/items", headers={"Idempotency-Key": uuid.uuid4().hex}, json={
        "team_id": viewer.id, "title": "Not allowed", "description": "Test", "item_type": "task", "priority": "low",
    })
    assert response.status_code == 403


def test_teams_require_authentication(client):
    assert client.get("/teams").status_code == 401
