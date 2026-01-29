from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    TODO = "TODO",
    IN_PROGRESS = "IN_PROGRESS",
    DONE = "DONE",
    SKIPPED = "SKIPPED"

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    content: str
    title: str
    category: str = Field(default="General")
    priority: str = Field(default="Medium")
    scheduled_time: Optional[datetime] = Field(default=None, index=True)
    status: TaskStatus = Field(default=TaskStatus.TODO)
    skip_reason: Optional[str] = None
    weather_snapshot: Optional[Dict] = Field(default={}, sa_column=Column(JSON))
    ai_suggestion: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)