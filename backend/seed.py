
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User, Team, Membership
from app.auth import hash_password


demo_users = [
    ("Demo Admin", "demo@example.com", "Demo@12345", "admin"),
    ("Priya Lead", "lead@example.com", "Lead@12345", "lead"),
    ("Amit Member", "member@example.com", "Member@12345", "member"),
    ("Neha Viewer", "viewer@example.com", "Viewer@12345", "viewer"),
]


with SessionLocal() as db:
    team = db.scalar(
        select(Team).where(Team.name == "Engineering")
    )

    if team is None:
        team = Team(name="Engineering")
        db.add(team)
        db.flush()
        print("Engineering team created")

    for name, email, password, role in demo_users:
        user = db.scalar(
            select(User).where(User.email == email)
        )

        if user is None:
            user = User(
                name=name,
                email=email,
                passwaord_hash=hash_password(password)
            )
            db.add(user)
            db.flush()
            print(f"Created user: {email}")
        else:
            print(f"User already exists: {email}")

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
                role=role
            )
            db.add(membership)
            print(f"Added {email} as {role}")
        else:
            print(f"Membership already exists: {email}")

    db.commit()
    print("All demo users are ready!")
