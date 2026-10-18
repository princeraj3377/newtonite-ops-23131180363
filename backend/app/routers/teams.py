from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Membership, Team, User
from app.permissions import ROLE_PERMISSIONS, authorize

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("/{team_id}/members")
def get_team_members(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    authorize(db=db, user=current_user, team_id=team_id, action="view")
    members = db.execute(
        select(User.id, User.name, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.team_id == team_id)
        .order_by(User.name, User.id)
    ).all()
    return [{"id": member.id, "name": member.name, "role": member.role} for member in members]


@router.get("")
def get_my_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memberships = db.execute(
        select(Team, Membership.role)
        .join(Membership, Membership.team_id == Team.id)
        .where(Membership.user_id == current_user.id)
        .order_by(Team.name, Team.id)
    ).all()
    return [
        {
            "id": team.id,
            "name": team.name,
            "role": role,
            "permissions": sorted(ROLE_PERMISSIONS.get(role, set())),
        }
        for team, role in memberships
        if "view" in ROLE_PERMISSIONS.get(role, set())
    ]
