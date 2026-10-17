
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.permissions import authorize
from app.models import User, WorkItem, Comment
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

    # 3. Create comment
    comment = Comment(
        work_item_id=item.id,
        author_id=current_user.id,
        content=data.content
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "work_item_id": comment.work_item_id,
        "author_id": comment.author_id,
        "content": comment.content
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

    comments = db.scalars(
        select(Comment)
        .where(Comment.work_item_id == item_id)
        .order_by(Comment.id.asc())
    ).all()

    return [
        {
            "id": comment.id,
            "author_id": comment.author_id,
            "content": comment.content
        }
        for comment in comments
    ]
