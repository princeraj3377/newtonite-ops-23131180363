
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.permissions import authorize
from app.models import User, WorkItem, Comment, ActivityEvent
from app.schemas import CommentCreate

router = APIRouter(
    prefix="/items",
    tags=["Comments"]
)


@router.post("/{item_id}/comments", status_code=201)
def create_comment(
    item_id: int,
    data: CommentCreate,
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

    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Comment cannot be blank")

    # Save the comment and its activity event in one transaction.
    comment = Comment(
        work_item_id=item.id,
        author_id=current_user.id,
        content=content
    )

    db.add(comment)
    db.add(ActivityEvent(
        work_item_id=item.id,
        actor_id=current_user.id,
        action="commented",
        details="Added a comment",
    ))
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "work_item_id": comment.work_item_id,
        "author_id": comment.author_id,
        "content": comment.content,
        "author_name": current_user.name,
        "created_at": comment.created_at,
    }


@router.get("/{item_id}/comments")
def get_comments(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.get(WorkItem, item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Work item not found"
        )

    authorize(
        db=db,
        user=current_user,
        team_id=item.team_id,
        action="view"
    )

    comments = db.execute(
        select(Comment, User.name)
        .join(User, User.id == Comment.author_id)
        .where(Comment.work_item_id == item_id)
        .order_by(Comment.id.asc())
    ).all()

    return [
        {
            "id": comment.id,
            "author_id": comment.author_id,
            "content": comment.content,
            "author_name": author_name,
            "created_at": comment.created_at,
        }
        for comment, author_name in comments
    ]
