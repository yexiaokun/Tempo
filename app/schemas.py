from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TaskExtraction(BaseModel):
    title: str = Field(description="任务的简短标题，动词开头，例如'晨跑'")
    scheduled_time: datetime = Field(description="推断出的具体执行时间（ISO格式）。如果用户没说年份，默认用今年。")
    category: str = Field(description="任务分类，可选值: Work, Personal, Health, Learning, Errand")
    priority: str = Field(description="优先级，基于语气判断：High, Medium, Low", default="Medium")
    location: Optional[str] = Field(description="任务发生的地点（如果有），默认是用户的当前城市", default=None)
    reasoning: Optional[str] = Field(default=None, description="AI调整建议")
    suggested_titles: List[str] = Field(default=[], description="AI建议的替代方案标题列表，可以有多个 (例如 ['哈尔滨室内游泳', '哈尔滨雪地漫步'])")