import uuid

import pytest

from app.auth import create_access_token
from app.models import Membership, Team, User, WorkItem


@pytest.fixture
def assignments(client, db_session):
    suffix = uuid.uuid4().hex
    users = {
        role: User(name=f"{role.title()} User", email=f"{role}-{suffix}@example.com", passwaord_hash="unused")
        for role in ["admin", "lead", "member", "viewer", "outsider"]
    }
    team, other = Team(name=f"Assign {suffix}"), Team(name=f"Other {suffix}")
    db_session.add_all([*users.values(), team, other])
    db_session.flush()
    db_session.add_all([
        Membership(user_id=user.id, team_id=team.id if role != "outsider" else other.id, role=role if role != "outsider" else "member")
        for role, user in users.items()
    ])
    item = WorkItem(title="Claim this task", description="Assignment test", item_type="task", team_id=team.id, created_by=users["admin"].id)
    db_session.add(item)
    db_session.flush()
    # Release the fixture savepoint so an endpoint rollback cannot erase setup.
    # conftest's outer transaction still rolls everything back after the test.
    db_session.commit()

    def as_user(role):
        client.headers["Authorization"] = f"Bearer {create_access_token(users[role].id)}"
        return client

    yield as_user, users, team, item
    client.headers.pop("Authorization", None)


def test_member_directory_is_team_scoped(assignments):
    as_user, users, team, _ = assignments
    response = as_user("admin").get(f"/teams/{team.id}/members")
    assert response.status_code == 200
    members = response.json()
    assert {row["id"] for row in members} == {user.id for role, user in users.items() if role != "outsider"}
    assert all(set(row) == {"id", "name", "role"} for row in members)
    assert as_user("outsider").get(f"/teams/{team.id}/members").status_code == 403


@pytest.mark.parametrize("role", ["admin", "lead", "member"])
def test_claim_assigns_current_user_and_records_activity(assignments, role):
    as_user, users, team, item = assignments
    client = as_user(role)
    response = client.patch(f"/items/{item.id}/claim", json={"expected_version": 1, "assignee_id": users["outsider"].id})
    assert response.status_code == 200
    assert response.json()["assignee_id"] == users[role].id
    assert response.json()["version"] == 2
    detail = client.get(f"/items/{item.id}").json()
    assert detail["assignee_name"] == users[role].name
    listed = client.get("/items", params={"team_id": team.id}).json()
    assert listed[0]["assignee_name"] == users[role].name
    activity = client.get(f"/items/{item.id}/activity").json()
    assert len(activity) == 1
    assert activity[0]["action"] == "claimed"
    assert activity[0]["actor_id"] == users[role].id


@pytest.mark.parametrize("role", ["viewer", "outsider"])
def test_claim_denies_read_only_and_nonmembers(assignments, role):
    as_user, _, _, item = assignments
    assert as_user(role).patch(f"/items/{item.id}/claim", json={"expected_version": 1}).status_code == 403
    assert as_user("admin").get(f"/items/{item.id}").json()["assignee_id"] is None


def test_claim_never_steals_assignment_even_with_current_version(assignments):
    as_user, users, _, item = assignments
    assert as_user("member").patch(f"/items/{item.id}/claim", json={"expected_version": 1}).status_code == 200
    for version in [1, 2]:
        assert as_user("admin").patch(f"/items/{item.id}/claim", json={"expected_version": version}).status_code == 409
    assert as_user("admin").get(f"/items/{item.id}").json()["assignee_id"] == users["member"].id
    assert len(as_user("admin").get(f"/items/{item.id}/activity").json()) == 1


def test_stale_claim_does_not_mutate_item(assignments):
    as_user, _, _, item = assignments
    client = as_user("member")
    assert client.patch(f"/items/{item.id}/claim", json={"expected_version": 20}).status_code == 409
    detail = client.get(f"/items/{item.id}").json()
    assert detail["assignee_id"] is None
    assert detail["version"] == 1
    assert client.get(f"/items/{item.id}/activity").json() == []


@pytest.mark.parametrize("role", ["admin", "lead"])
def test_assign_and_reassign_with_version_check(assignments, role):
    as_user, users, _, item = assignments
    client = as_user(role)
    response = client.patch(f"/items/{item.id}/assign", json={"assignee_id": users["member"].id, "expected_version": 1})
    assert response.status_code == 200
    assert response.json()["assignee_id"] == users["member"].id
    assert client.patch(f"/items/{item.id}/assign", json={"assignee_id": users[role].id, "expected_version": 1}).status_code == 409
    assert client.patch(f"/items/{item.id}/assign", json={"assignee_id": users[role].id, "expected_version": 2}).status_code == 200
    assert client.get(f"/items/{item.id}").json()["assignee_id"] == users[role].id


@pytest.mark.parametrize("role", ["member", "viewer", "outsider"])
def test_assignment_requires_assign_permission(assignments, role):
    as_user, users, _, item = assignments
    assert as_user(role).patch(f"/items/{item.id}/assign", json={"assignee_id": users["member"].id, "expected_version": 1}).status_code == 403


def test_cannot_assign_to_another_team(assignments):
    as_user, users, _, item = assignments
    client = as_user("admin")
    assert client.patch(f"/items/{item.id}/assign", json={"assignee_id": users["outsider"].id, "expected_version": 1}).status_code == 400
    assert client.get(f"/items/{item.id}").json()["assignee_id"] is None


def test_claim_validation_and_missing_item(assignments):
    as_user, _, _, item = assignments
    client = as_user("member")
    for payload in [{}, {"expected_version": 0}]:
        assert client.patch(f"/items/{item.id}/claim", json=payload).status_code == 422
    assert client.patch("/items/2147483647/claim", json={"expected_version": 1}).status_code == 404


def test_assignment_endpoints_require_auth(client):
    assert client.get("/teams/1/members").status_code == 401
    assert client.patch("/items/1/claim", json={"expected_version": 1}).status_code == 401
