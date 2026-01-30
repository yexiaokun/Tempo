from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TaskExtraction(BaseModel):
    title: str = Field(description="任务的简短标题，动词开头，例如'晨跑'")
    scheduled_time: datetime = Field(description="推断出的具体执行时间（ISO格式）。如果用户没说年份，默认用今年。")
    category: str = Field(description="任务分类，可选值: Work, Personal, Health, Learning, Errand")
    priority: str = Field(description="优先级，基于语气判断：High, Medium, Low", default="Medium")
    location: Optional[str] = Field(description="任务发生的地点（如果有），默认是用户的当前城市", default=None)