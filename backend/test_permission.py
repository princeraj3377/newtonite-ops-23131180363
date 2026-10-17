
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.permissions import authorize

with SessionLocal() as db:
    user = db.scalar(
        select(User).where(
            User.email == "demo@example.com"
        )
    )

    if user is None:
        raise RuntimeError("Demo user not found")

    membership = authorize(
        db=db,
        user=user,
        team_id=1,
        action="create"
    )

    print("Authorization successful!")
    print("Role:", membership.role)
