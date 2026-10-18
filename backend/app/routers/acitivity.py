
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.permissions import authorize
from app.models import User, WorkItem, ActivityEvent

router = APIRouter(
    prefix="/items",
    tags=["Activity History"]
)


@router.get("/{item_id}/activity")
def get_item_activity(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Find work item
    item = db.get(WorkItem, item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Work item not found"
        )

    # 2. Check team permission
    authorize(
        db=db,
        user=current_user,
        team_id=item.team_id,
        action="view"
    )

    # 3. Fetch activity history
    events = db.execute(
        select(ActivityEvent, User.name)
        .join(User, User.id == ActivityEvent.actor_id)
        .where(ActivityEvent.work_item_id == item_id)
        .order_by(
            ActivityEvent.created_at.asc(),
            ActivityEvent.id.asc()
        )
    ).all()

    return [
        {
            "id": event.id,
            "work_item_id": event.work_item_id,
            "actor_id": event.actor_id,
            "actor_name": actor_name,
            "action": event.action,
            "details": event.details,
            "created_at": event.created_at
        }
        for event, actor_name in events
    ]
