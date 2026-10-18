
from fastapi import APIRouter, Depends, Query, status
from typing import Literal
from sqlalchemy import or_
from sqlalchemy.orm import Session


from app.database import get_db
from app.auth import get_current_user
from app.permissions import authorize
from app.models import User, WorkItem, ActivityEvent
from app.schemas import WorkItemCreate,WorkItemAssign
from sqlalchemy import select
from sqlalchemy import update
from app.models import Membership


from fastapi import HTTPException,Header
from app.schemas import WorkItemUpdate
from app.workflow import validate_transition
from app.schemas import WorkItemStatusUpdate, WorkItemClaim


from fastapi import Header
from app.idempotency import create_request_hash
from app.models import IdempotencyRecord
from sqlalchemy.exc import IntegrityError
import json


router = APIRouter(
    prefix="/items",
    tags=["Work Items"]
)



@router.post("", status_code=status.HTTP_201_CREATED)
def create_work_item(
    data: WorkItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=255
    )
):
    # 1. Check team permission
    authorize(
        db=db,
        user=current_user,
        team_id=data.team_id,
        action="create"
    )

    # 2. Generate request hash
    request_hash = create_request_hash(data)

    # 3. Try to reserve idempotency key
    record = IdempotencyRecord(
        user_id=current_user.id,
        key=idempotency_key,
        request_hash=request_hash
    )

    try:
        # Savepoint protects the outer transaction
        with db.begin_nested():
            db.add(record)
            db.flush()

    except IntegrityError:
        # Another request already used this key
        existing = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == current_user.id,
                IdempotencyRecord.key == idempotency_key
            )
        )

        if existing is None:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key conflict. Retry request."
            )

        # Same key but different request body
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key reused with different request"
            )

        # Same key and same request
        if existing.response_body is not None:
            return json.loads(existing.response_body)

        raise HTTPException(
            status_code=409,
            detail="Request is already being processed"
        )

    # 4. Create work item
    item = WorkItem(
        title=data.title,
        description=data.description,
        item_type=data.item_type,
        priority=data.priority,
        team_id=data.team_id,
        created_by=current_user.id
    )

    db.add(item)
    db.flush()

    # 5. Record activity
    event = ActivityEvent(
        work_item_id=item.id,
        actor_id=current_user.id,
        action="created",
        details="Work item created"
    )

    db.add(event)

    # 6. Prepare response
    response_body = {
        "id": item.id,
        "title": item.title,
        "status": item.status,
        "team_id": item.team_id,
        "created_by": item.created_by,
        "version": item.version
    }

    # 7. Save response with idempotency record
    record.response_body = json.dumps(response_body)

    # 8. Commit everything together
    db.commit()

    return response_body



@router.patch("/{item_id}/assign")
def assign_work_item(
    item_id: int,
    data: WorkItemAssign,
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

    # 2. Check assigner's permission
    authorize(
        db=db,
        user=current_user,
        team_id=item.team_id,
        action="assign"
    )

    # 3. Check assignee belongs to same team
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == data.assignee_id,
            Membership.team_id == item.team_id
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=400,
            detail="Assignee is not a member of this team"
        )

    # 4. Atomic update with version check
    result = db.execute(
        update(WorkItem)
        .where(
            WorkItem.id == item_id,
            WorkItem.version == data.expected_version
        )
        .values(
            assignee_id=data.assignee_id,
            version=WorkItem.version + 1
        )
        .returning(
            WorkItem.id,
            WorkItem.version,
            WorkItem.assignee_id
        )
    )

    updated = result.first()

    if updated is None:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Version conflict. Refresh and retry."
        )

    # 5. Save activity event
    event = ActivityEvent(
        work_item_id=item_id,
        actor_id=current_user.id,
        action="assigned",
        details=f"Assigned to user {data.assignee_id}"
    )

    db.add(event)
    db.commit()

    return {
        "id": updated.id,
        "assignee_id": updated.assignee_id,
        "version": updated.version,
        "message": "Work item assigned successfully"
    }








@router.patch("/{item_id}/claim")
def claim_work_item(
    item_id: int,
    data: WorkItemClaim,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    authorize(db=db, user=current_user, team_id=item.team_id, action="claim")
    # Assignment and version are checked together so competing claims cannot steal ownership.
    updated = db.execute(
        update(WorkItem)
        .where(
            WorkItem.id == item_id,
            WorkItem.version == data.expected_version,
            WorkItem.assignee_id.is_(None),
        )
        .values(assignee_id=current_user.id, version=WorkItem.version + 1)
        .returning(WorkItem.id, WorkItem.assignee_id, WorkItem.version)
    ).first()
    if updated is None:
        db.rollback()
        raise HTTPException(status_code=409, detail="This item changed or has already been assigned. Refresh and retry.")
    db.add(ActivityEvent(
        work_item_id=item_id,
        actor_id=current_user.id,
        action="claimed",
        details=f"{current_user.name} claimed this work item",
    ))
    db.commit()
    return {
        "id": updated.id,
        "assignee_id": updated.assignee_id,
        "version": updated.version,
        "message": "Work item claimed successfully",
    }


@router.get("")
def get_work_items(
    team_id: int = Query(..., gt=0),
    status: Literal["open", "in_progress", "resolved", "closed"] | None = None,
    priority: Literal["low", "medium", "high", "critical"] | None = None,
    item_type: Literal["incident", "customer_issue", "payment", "compliance", "task"] | None = None,
    q: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    authorize(
        db=db,
        user=current_user,
        team_id=team_id,
        action="view"
    )

    query = select(WorkItem, User.name).outerjoin(
        User, User.id == WorkItem.assignee_id
    ).where(WorkItem.team_id == team_id)
    if status is not None:
        query = query.where(WorkItem.status == status)
    if priority is not None:
        query = query.where(WorkItem.priority == priority)
    if item_type is not None:
        query = query.where(WorkItem.item_type == item_type)
    if q and q.strip():
        # Treat SQL wildcard characters as literal search text.
        search = q.strip()
        query = query.where(or_(
            WorkItem.title.icontains(search, autoescape=True),
            WorkItem.description.icontains(search, autoescape=True),
        ))
    items = db.execute(query.order_by(WorkItem.id.desc())).all()

    return [
        {
            "id": item.id,
            "title": item.title,
            "status": item.status,
            "priority": item.priority,
            "item_type": item.item_type,
            "assignee_id": item.assignee_id,
            "assignee_name": assignee_name,
            "created_at": item.created_at,
            "team_id": item.team_id,
            "version": item.version
        }
        for item, assignee_name in items
    ]









@router.get("/{item_id}")
def get_work_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the work item
    item = db.get(WorkItem, item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Work item not found"
        )

    # Check permission for item's team
    authorize(
        db=db,
        user=current_user,
        team_id=item.team_id,
        action="view"
    )

    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "item_type": item.item_type,
        "priority": item.priority,
        "status": item.status,
        "team_id": item.team_id,
        "assignee_id": item.assignee_id,
        "assignee_name": db.get(User, item.assignee_id).name if item.assignee_id else None,
        "created_by": item.created_by,
        "version": item.version
    }




@router.patch("/{item_id}")
def update_work_item(
    item_id: int,
    data: WorkItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.get(WorkItem, item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Work item not found"
        )

    # Check permission
    authorize(
        db=db,
        user=current_user,
        team_id=item.team_id,
        action="edit"
    )

    # Only update fields supplied by user
    changes = data.model_dump(
        exclude_unset=True,
        exclude={"expected_version"}
    )

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    if any(value is None for value in changes.values()):
        raise HTTPException(
            status_code=422,
            detail="Updated fields cannot be null"
        )

    # Atomic version check and update
    result = db.execute(
        update(WorkItem)
        .where(
            WorkItem.id == item_id,
            WorkItem.version == data.expected_version
        )
        .values(
            **changes,
            version=WorkItem.version + 1
        )
        .returning(WorkItem.id, WorkItem.version)
    )

    updated = result.first()

    if updated is None:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Version conflict. Refresh and retry."
        )

    event = ActivityEvent(
        work_item_id=item_id,
        actor_id=current_user.id,
        action="updated",
        details=f"Updated fields: {', '.join(changes.keys())}"
    )

    db.add(event)
    db.commit()

    return {
        "id": updated.id,
        "version": updated.version,
        "message": "Work item updated successfully"
    }




@router.patch("/{item_id}/status")
def change_work_item_status(
    item_id: int,
    data: WorkItemStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Find item
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
        action="edit"
    )

    # Keep the original value: the ORM synchronizes item.status during update.
    previous_status = item.status
    # 3. Validate status transition
    validate_transition(
        current_status=item.status,
        new_status=data.status
    )

    # 4. Atomic update with version check
    result = db.execute(
        update(WorkItem)
        .where(
            WorkItem.id == item_id,
            WorkItem.version == data.expected_version,
            WorkItem.status == item.status
        )
        .values(
            status=data.status,
            version=WorkItem.version + 1
        )
        .returning(
            WorkItem.id,
            WorkItem.status,
            WorkItem.version
        )
    )

    updated = result.first()

    if updated is None:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Item changed. Refresh and retry."
        )

    # 5. Record activity
    event = ActivityEvent(
        work_item_id=item_id,
        actor_id=current_user.id,
        action="status_changed",
        details=f"{previous_status} -> {data.status}"
    )

    db.add(event)
    db.commit()

    return {
        "id": updated.id,
        "status": updated.status,
        "version": updated.version,
        "message": "Status updated successfully"
    }



