from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
from pgvector.sqlalchemy import Vector

class TaskStatus(str, Enum):
    TODO = "TODO",
    IN_PROGRESS = "IN_PROGRESS",
    DONE = "DONE",
    SKIPPED = "SKIPPED"

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    #核心内容
    content: str
    title: str

    #智能分析结果
    category: str = Field(default="General")
    priority: str = Field(default="Medium")
    scheduled_time: Optional[datetime] = Field(default=None, index=True)

    #位置信息
    location_name: Optional[str] = None
    is_auto_located: bool = Field(default=False)

    #状态管理
    status: TaskStatus = Field(default=TaskStatus.TODO)
    skip_reason: Optional[str] = None

    #天气信息与建议
    weather_snapshot: Optional[Dict] = Field(default={}, sa_column=Column(JSON))
    ai_suggestion: Optional[str] = None

    #关联用户
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="tasks")


    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str = Field(nullable=False)
    email: Optional[str] = Field(default=None, index=True)
    #没有定位到ip时的兜底城市
    default_city: str = Field(default="Beijing")

    memories: List["UserMemory"] = Relationship(back_populates="user")
    tasks: List["Task"] = Relationship(back_populates="user")
    created_at: datetime = Field(default_factory=datetime.now)

class UserMemory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    content: str
    embedding: List[float] = Field(sa_column=Column(Vector(1024)))

    user_id: int = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="memories")

    created_at: datetime = Field(default_factory=datetime.now)

class TaskUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    location_name: Optional[str] = None