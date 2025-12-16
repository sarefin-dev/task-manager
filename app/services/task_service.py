from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.cache.decorators import async_cached, async_cached_expire
from app.models import Task, TaskCreate, TaskUpdate


class TaskService:
    @staticmethod
    async def create_task(task_data: TaskCreate, db: AsyncSession):
        task = Task.model_validate(task_data)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_all_tasks(
        db: AsyncSession,
        skip: int,
        limit: int,
        completed: bool | None = None,
        priority: str | None = None,
    ):
        query = select(Task)
        if completed is not None:
            query = query.where(Task.completed == completed)
        if priority:
            query = query.where(Task.priority == priority)
        query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())

        result = await db.exec(query)
        tasks = result.all()
        return tasks

    @staticmethod
    @async_cached(lambda task_id, *_, **__: f"task:{task_id}", l2_ttl=120)
    async def get_task(task_id: int, db: AsyncSession):
        task = await db.get(Task, task_id)
        return task

    # write through validation as well.
    @staticmethod
    @async_cached_expire(lambda task_id, *_, **__: f"task:{task_id}")
    async def update_task(task_id: int, task_data: TaskUpdate, db: AsyncSession):
        task = await db.get(Task, task_id)
        if not task:
            return None
        update_data = task_data.model_dump(exclude_unset=True)
        task.sqlmodel_update(update_data)
        task.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    @async_cached_expire(lambda task_id, *_, **__: f"task:{task_id}")
    async def delete_task(task_id: int, db: AsyncSession):
        task = await db.get(Task, task_id)
        if not task:
            return False
        await db.delete(task)
        await db.commit()
        return True

    @staticmethod
    @async_cached_expire(lambda task_id, *_, **__: f"task:{task_id}")
    async def complete_task(task_id: int, db: AsyncSession):
        task = await db.get(Task, task_id)
        if not task:
            return None

        task.completed = True
        task.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(task)
        return task
