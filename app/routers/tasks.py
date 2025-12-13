from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.cache.decorators import async_cached
from app.database import get_db
from app.models import Task, TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@async_cached(lambda task_id, *_ , **__: f"task:{task_id}", l2_ttl=120)
async def cached_get_task(task_id: int, db: AsyncSession):
    print("sdf")
    result = await db.exec(select(Task).where(Task.id == task_id))
    task = result.first()
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task"""
    task = Task.model_validate(task_data)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    completed: Optional[bool] = None,
    priority: Optional[str] = Query(default=None, regex="^(low|medium|high)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get all tasks with filtering and pagination"""
    query = select(Task)

    # Apply filters
    if completed is not None:
        query = query.where(Task.completed == completed)
    if priority:
        query = query.where(Task.priority == priority)

    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific task by ID"""

    task = await cached_get_task(task_id, db)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int, task_data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a task (partial update)"""
    result = await db.exec(select(Task).where(Task.id == task_id))
    task = result.first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    # Update only provided fields
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    # Update timestamp with timezone-aware datetime
    task.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a task"""
    result = await db.exec(select(Task).where(Task.id == task_id))
    task = result.first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    await db.delete(task)
    await db.commit()


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def mark_task_complete(task_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a task as completed"""
    result = await db.exec(select(Task).where(Task.id == task_id))
    task = result.first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    task.completed = True
    task.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)
    return task
