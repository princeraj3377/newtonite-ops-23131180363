from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Membership, User


ROLE_PERMISSIONS = {
    "admin": {
        "view", "create", "edit",
        "assign", "manage_members"
    },
    "lead": {
        "view", "create", "edit", "assign"
    },
    "member": {
        "view", "create", "edit_own"
    },
    "viewer": {
        "view"
    }
}


def authorize(
    db: Session,
    user: User,
    team_id: int,
    action: str
) -> Membership:

    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.team_id == team_id
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this team"
        )

    permissions = ROLE_PERMISSIONS.get(
        membership.role, set()
    )

    if action not in permissions:
        raise HTTPException(
            status_code=403,
            detail="Permission denied"
        )

    return membership