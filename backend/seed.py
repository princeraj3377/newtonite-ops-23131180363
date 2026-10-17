
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User, Team, Membership
from app.auth import hash_password


with SessionLocal() as db:

    # Step 1: Find or create demo user
    user = db.scalar(
        select(User).where(User.email == "demo@example.com")
    )

    if user is None:
        user = User(
            name="Demo User",
            email="demo@example.com",
            passwaord_hash=hash_password("Demo@12345")
        )
        db.add(user)
        db.flush()
        print("Demo user created")
    else:
        print("Demo user already exists")

    # Step 2: Find or create Engineering team
    team = db.scalar(
        select(Team).where(Team.name == "Engineering")
    )

    if team is None:
        team = Team(name="Engineering")
        db.add(team)
        db.flush()
        print("Engineering team created")

    # Step 3: Find or create admin membership
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.team_id == team.id
        )
    )

    if membership is None:
        membership = Membership(
            user_id=user.id,
            team_id=team.id,
            role="admin"
        )
        db.add(membership)
        print("Admin membership created")

    db.commit()

    print("Demo user, team and membership are ready")
    print("User ID:", user.id)
    print("Team ID:", team.id)
