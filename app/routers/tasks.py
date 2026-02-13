from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import get_session
from app.core.deps import get_current_user
from app.services.parser import parse_task_command
from app.services.weather import weather_service
from app.services.location import location_service
from app.db.models import Task, User, TaskStatus, UserMemory, TaskUpdate
from pydantic import BaseModel
from typing import Optional, List
from sqlmodel import select
from app.services.memory import memory_service
import numpy as np


# 定义路由
router = APIRouter(prefix="/tasks", tags=["Tasks"])

# 定义请求体模型
class CommandRequest(BaseModel):
    command: str

class MemoryCreate(BaseModel):
    content: str

@router.post("/create")
async def create_task_from_natural_language(
    request: CommandRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    【核心接口】
    1. 接收自然语言指令 ("明天下午去公园")
    2. 调用 AI 解析出结构化数据 (时间、地点)
    3. 调用和风天气查询天气状况
    4. 生成简单的行动建议
    5. 写入数据库
    """
    
    # --- 1. 获取当前用户 ---
    print(f"👤 [Auth] User: {current_user.username} is creating a task.")

    # --- 2. 自动定位 (Auto-Location) ---
    # 获取 IP
    client_ip = req.headers.get("x-forwarded-for")
    if not client_ip:
        client_ip = req.client.host
    # 处理多重代理 IP 格式 (如: "203.x.x.x, 192.x.x.x")
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    # 调用服务查城市
    auto_city = await location_service.get_city_from_ip(client_ip)

    # 搜索用户记忆
    print(f"🔍 [Memory] Searching relevant memories for: {request.command}")
    relevant_context = await memory_service.search_relevant_memories(
        session, current_user.id, request.command
    )
    if relevant_context:
        print(f"🧠 [Memory] Found context: {relevant_context}")
    

    # --- 3. AI 大脑解析 ---
    print(f"🤖 [Agent] Analyzing with Context...")
    parsed = await parse_task_command(request.command, user_context=relevant_context)

    if not parsed:
        raise HTTPException(status_code=400, detail="AI Parse Error")

    # --- 4. 确定最终地点 (核心决策树) ---
    # A. AI 解析出地点 (用户明确说了 "去上海") -> 优先级最高
    # B. IP 自动定位出城市 -> 优先级中
    # C. 用户默认设置 (兜底) -> 优先级最低
    
    final_location = None
    is_auto = False

    if parsed.location:
        final_location = parsed.location
        is_auto = False # 用户指定的，不算自动
    elif auto_city:
        final_location = auto_city
        is_auto = True
    else:
        final_location = current_user.default_city
        is_auto = True 

    print(f"📍 Location Decision: {final_location} (Auto: {is_auto})")

    # --- 5. 查天气 & 建议 ---
    weather_msg = ""
    
    if final_location:
        loc_id = await weather_service.get_location_id(final_location)
        if loc_id:
            weather_info = await weather_service.get_weather_forecast(loc_id, parsed.scheduled_time)
            # 生成建议
            if weather_info and "text" in weather_info:
                weather_msg = f"🌤️ {final_location}天气: {weather_info['text']}"
    
    suggestion_parts = []

    if parsed.reasoning:
        suggestion_parts.append(f"💡 {parsed.reasoning}")
    if weather_msg:
        suggestion_parts.append(weather_msg)
    
    final_suggestion = "\n".join(suggestion_parts)

    clean_time = parsed.scheduled_time.replace(tzinfo=None) if parsed.scheduled_time.tzinfo else parsed.scheduled_time

    # --- 6. 存入数据库 ---
    new_task = Task(
        content=request.command,
        title=parsed.title,
        scheduled_time=clean_time,
        category=parsed.category,
        priority=parsed.priority,
        
        # ✅ 存入位置信息
        location_name=final_location,
        is_auto_located=is_auto,
        
        weather_snapshot=weather_info,
        ai_suggestion=final_suggestion,
        
        # ✅ 关联用户
        user_id=current_user.id
    )
    
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    
    return {
        "status": "success", 
        "location_source": "User_Command" if parsed.location else ("IP_Auto" if auto_city else "Default_Setting"),
        "final_location": final_location,
        "task_id": new_task.id,
        "suggestion": final_suggestion,
        "suggested_titles": parsed.suggested_titles,
        "has_conflict": len(parsed.suggested_titles) > 0
    }

@router.get("/", response_model=List[Task])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    查看【我的】所有任务列表
    自动过滤别人的任务
    """
    statement = select(Task).where(Task.user_id == current_user.id).order_by(Task.scheduled_time)
    result = await session.exec(statement)
    tasks = result.all()
    return tasks

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    删除任务
    只能删除自己的任务，删别人的会报错
    """
    task = await session.get(Task, task_id)

    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found(or you don't have permission)")
    
    await session.delete(task)
    await session.commit()
    return {"status": "deleted", "id": task_id}

@router.post("/{task_id}/done")
async def mark_task_one(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    将任务标记为完成
    """
    task = await session.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = TaskStatus.DONE
    session.add(task)
    await session.commit()
    return {"status": "success", "message": f"Task '{task.title}' marked as DONE"}

@router.post("/memories")
async def create_memory(
    memory_data: MemoryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    告诉 AI 一个关于你的秘密(习惯)
    例如：“我不吃辣”， “周三晚上要陪女朋友”
    """
    await memory_service.add_memory(session, current_user.id, memory_data.content)
    return {"status": "success", "msg": "Memory stored."}

@router.get("/memories", response_model=List[UserMemory])
async def list_memories(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    查看我的所有记忆/偏好
    """
    statement = select(UserMemory).where(UserMemory.user_id == current_user.id).order_by(UserMemory.created_at.desc())
    result = await session.exec(statement)
    memories = result.all()
    #将numpy array 转换成list，否则json序列化会报错
    for mem in memories:
        if hasattr(mem.embedding, "tolist"):
            mem.embedding = mem.embedding.tolist()
        elif isinstance(mem.embedding, list):
            pass
    
    return memories

@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    memory = await session.get(UserMemory, memory_id)
    if not memory or memory.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Memory not found")
    await session.delete(memory)
    await session.commit()
    return {"status": "deleted"}



@router.patch("/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    🛠️ 通用修改接口
    """
    task = await session.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # ✅ 标准写法：前端传什么字段，就更新什么字段
    # 不再需要 if 'content' in update_data: ... 这种魔法了
    update_data = task_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        # 安全检查：确保 Task 模型里有这个字段
        if hasattr(task, key):
            setattr(task, key, value)
    
    session.add(task)
    await session.commit()
    await session.refresh(task)
    
    return task