from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now():
    return datetime.now(timezone.utc)


class TaskBase(SQLModel):
    """Base model with shared fields"""

    title: str = Field(min_length=1, max_length=200, index=True)
    description: str | None = Field(default=None, sa_column_kwargs={"nullable": True})
    priority: str = Field(default="medium", regex="^(low|medium|high)$")


class Task(TaskBase, table=True):
    """Database model"""

    __tablename__ = "tasks"

    id: int | None = Field(default=None, primary_key=True)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime | None = Field(default=None, nullable=True)


class TaskCreate(TaskBase):
    """Schema for creating a task"""

    pass


class TaskUpdate(SQLModel):
    """Schema for updating a task - all fields optional"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None
    priority: str | None = Field(default=None, regex="^(low|medium|high)$")


class TaskResponse(TaskBase):
    """Schema for task responses"""

    id: int
    completed: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
