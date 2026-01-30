from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import get_session
from app.core.deps import get_current_user
from app.services.parser import parse_task_command
from app.services.weather import weather_service
from app.services.location import location_service
from app.db.models import Task, User
from pydantic import BaseModel
from typing import Optional
from sqlmodel import select

# 定义路由
router = APIRouter(prefix="/tasks", tags=["Tasks"])

# 定义请求体模型
class CommandRequest(BaseModel):
    command: str

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
    
    # --- 1. 获取当前用户 (MVP: 查 demo_user) ---
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


    # --- 3. AI 大脑解析 ---
    print(f"🧠 [Agent] Analyzing: {request.command}")
    parsed = await parse_task_command(request.command)
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
    weather_info = {}
    suggestion = None
    
    if final_location:
        loc_id = await weather_service.get_location_id(final_location)
        if loc_id:
            weather_info = await weather_service.get_weather_forecast(loc_id, parsed.scheduled_time)
            
            # 生成建议
            if weather_info and "text" in weather_info:
                if "雨" in weather_info['text']:
                    suggestion = f"🌧️ {final_location}预报有雨，记得带伞！"
                else:
                    suggestion = f"🌤️ {final_location}天气: {weather_info['text']}"

    # --- 6. 存入数据库 ---
    new_task = Task(
        content=request.command,
        title=parsed.title,
        scheduled_time=parsed.scheduled_time,
        category=parsed.category,
        priority=parsed.priority,
        
        # ✅ 存入位置信息
        location_name=final_location,
        is_auto_located=is_auto,
        
        weather_snapshot=weather_info,
        ai_suggestion=suggestion,
        
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
        "suggestion": suggestion
    }

@router.get("/")
async def list_tasks(
    session: AsyncSession = Depends(get_session)
):
    """
    查看所有任务列表
    """
    statement = select(Task).order_by(Task.scheduled_time)
    result = await session.exec(statement)
    tasks = result.all()
    return tasks