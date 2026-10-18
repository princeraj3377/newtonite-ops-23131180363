import uuid

import pytest

from app.auth import create_access_token
from app.models import Membership, Team, User, WorkItem


@pytest.fixture
def discussion(client, db_session):
    suffix = uuid.uuid4().hex
    user = User(name="Discussion User", email=f"discussion-{suffix}@example.com", passwaord_hash="unused")
    team = Team(name=f"Discussion {suffix}")
    other_team = Team(name=f"Private {suffix}")
    db_session.add_all([user, team, other_team])
    db_session.flush()
    membership = Membership(team_id=team.id, user_id=user.id, role="admin")
    item = WorkItem(title="Discussion item", description="Details", item_type="task", team_id=team.id, created_by=user.id)
    other = WorkItem(title="Private item", description="Details", item_type="task", team_id=other_team.id, created_by=user.id)
    db_session.add_all([membership, item, other])
    db_session.flush()
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"
    yield client, item, other, membership, db_session
    client.headers.pop("Authorization", None)


def test_comment_returns_author_timestamp_and_creates_activity(discussion):
    client, item, _, _, _ = discussion
    response = client.post(f"/items/{item.id}/comments", json={"content": "  First update\nSecond line  "})
    assert response.status_code == 201
    comment = response.json()
    assert comment["content"] == "First update\nSecond line"
    assert comment["author_name"] == "Discussion User"
    assert comment["created_at"]
    listed = client.get(f"/items/{item.id}/comments").json()
    assert len(listed) == 1
    assert listed[0]["id"] == comment["id"]
    assert listed[0]["created_at"] == comment["created_at"]
    assert listed[0]["author_name"] == comment["author_name"]
    activity = client.get(f"/items/{item.id}/activity").json()
    assert len(activity) == 1
    assert activity[0]["action"] == "commented"
    assert activity[0]["actor_name"] == "Discussion User"
    assert activity[0]["created_at"]


@pytest.mark.parametrize("content", ["", "   ", "\n\t", "x" * 2001])
def test_invalid_comments_do_not_create_comments_or_events(discussion, content):
    client, item, _, _, _ = discussion
    assert client.post(f"/items/{item.id}/comments", json={"content": content}).status_code == 422
    assert client.get(f"/items/{item.id}/comments").json() == []
    assert client.get(f"/items/{item.id}/activity").json() == []


def test_comment_order_and_maximum_length(discussion):
    client, item, _, _, _ = discussion
    ids = []
    for content in ["First", "x" * 2000]:
        response = client.post(f"/items/{item.id}/comments", json={"content": content})
        assert response.status_code == 201
        ids.append(response.json()["id"])
    assert [entry["id"] for entry in client.get(f"/items/{item.id}/comments").json()] == ids


def test_status_activity_keeps_original_status(discussion):
    client, item, _, _, _ = discussion
    response = client.patch(f"/items/{item.id}/status", json={"status": "in_progress", "expected_version": item.version})
    assert response.status_code == 200
    activity = client.get(f"/items/{item.id}/activity").json()
    assert activity[0]["details"] == "open -> in_progress"
    assert activity[0]["actor_name"] == "Discussion User"


@pytest.mark.parametrize("method,path", [("get", "comments"), ("post", "comments"), ("get", "activity")])
def test_discussion_respects_team_access(discussion, method, path):
    client, _, other, _, _ = discussion
    kwargs = {"json": {"content": "Not permitted"}} if method == "post" else {}
    assert getattr(client, method)(f"/items/{other.id}/{path}", **kwargs).status_code == 403


def test_viewer_can_comment_under_existing_view_permission(discussion):
    client, item, _, membership, db = discussion
    membership.role = "viewer"
    db.flush()
    assert client.post(f"/items/{item.id}/comments", json={"content": "Viewer update"}).status_code == 201


@pytest.mark.parametrize("method,path", [("get", "comments"), ("post", "comments"), ("get", "activity")])
def test_missing_item_returns_404(discussion, method, path):
    client, _, _, _, _ = discussion
    kwargs = {"json": {"content": "Missing"}} if method == "post" else {}
    assert getattr(client, method)(f"/items/2147483647/{path}", **kwargs).status_code == 404


@pytest.mark.parametrize("method,path", [("get", "comments"), ("post", "comments"), ("get", "activity")])
def test_discussion_requires_authentication(client, method, path):
    kwargs = {"json": {"content": "Anonymous"}} if method == "post" else {}
    assert getattr(client, method)(f"/items/1/{path}", **kwargs).status_code == 401
