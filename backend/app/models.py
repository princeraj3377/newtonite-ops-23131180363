from datetime import datetime,timezone



from sqlalchemy import(
    Integer,
    String,
    DateTime
)
from sqlalchemy import ForeignKey, UniqueConstraint,Text,CheckConstraint

from sqlalchemy.orm import(Mapped,mapped_column)

from app.database import Base



class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    name:Mapped[str]= mapped_column(String(100),nullable=False)
    email:Mapped[str] = mapped_column(String(100),unique=True,nullable=False)
    passwaord_hash:Mapped[str]=mapped_column(String(255),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))



class Team(Base):
    __tablename__="teams"

    id :Mapped[int]= mapped_column(Integer,primary_key=True)
    name:Mapped[str]= mapped_column(String(100),unique=True,nullable=False)


class Membership(Base):
    __tablename__="memberships"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id"),nullable=False)

    team_id:Mapped[int] = mapped_column(ForeignKey("teams.id"),nullable=False)
    role:Mapped[str] = mapped_column(String(20),default="member")
    __table_args__=(UniqueConstraint(
        "user_id",
        "team_id",
        name="uq_user_team"
        ),
    
    )




class WorkItem(Base):
    __tablename__ = "work_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    item_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    priority: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30), default="open", nullable=False
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )

    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint(
            "version >= 1",
            name="ck_work_item_version"
        ),
    )




class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    work_item_id: Mapped[int] = mapped_column(
        ForeignKey("work_items.id"),
        nullable=False,
        index=True
    )

    actor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    details: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    work_item_id: Mapped[int] = mapped_column(
        ForeignKey("work_items.id"),
        nullable=False,
        index=True
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )





class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    key: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )

    response_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "key",
            name="uq_idempotency_user_key"
        ),
    )


