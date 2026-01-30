from fastapi import APIRouter, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import get_session
from app.services.parser import parse_task_command
from app.services.weather import weather_service
from app.db.models import Task
from pydantic import BaseModel
from typing import Optional
from sqlmodel import select

# 定义路由
router = APIRouter(prefix="/tasks", tags=["Tasks"])

# 定义请求体模型
class CommandRequest(BaseModel):
    command: str
    # 默认定位，实际项目中应由前端传入，这里为了演示默认给个 Beijing
    user_location: str = "Beijing" 

@router.post("/create")
async def create_task_from_natural_language(
    request: CommandRequest,
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
    
    # --- 1. AI 大脑解析 ---
    print(f"🧠 [Agent] Analyzing: {request.command}")
    parsed_data = await parse_task_command(request.command)
    
    if not parsed_data:
        raise HTTPException(status_code=400, detail="AI 无法解析该指令，请尝试换个说法")

    print(f"✅ [Agent] Parsed: {parsed_data.title} @ {parsed_data.scheduled_time}")

    # --- 2. 天气感官查询 ---
    weather_info = {}
    ai_suggestion = None
    
    # 确定查询地点：如果 AI 解析出了地点(如"去三亚")就用解析的，否则用用户默认的
    search_city = parsed_data.location if parsed_data.location else request.user_location
    
    # 只有当确实有地点信息时才查天气
    if search_city:
        # A. 换取 Location ID
        loc_id = await weather_service.get_location_id(search_city)
        
        if loc_id:
            # B. 查询对应日期的天气
            weather_info = await weather_service.get_weather_forecast(loc_id, parsed_data.scheduled_time)
            
            # --- 3. 生成规则建议 (MVP 简化版) ---
            # 如果查到了天气数据，根据天气情况生成一句话建议
            if weather_info:
                weather_text = weather_info.get("text", "未知")
                max_temp = weather_info.get("temp_max", "N/A")
                
                if "雨" in weather_text:
                    ai_suggestion = f"🌧️ {search_city}预报有{weather_text}，出门请记得带伞！"
                elif "雪" in weather_text:
                    ai_suggestion = f"❄️ {search_city}预报有{weather_text}，路面湿滑请注意安全。"
                elif max_temp != "N/A" and int(max_temp) > 30:
                    ai_suggestion = f"🥵 天气炎热(最高{max_temp}°C)，户外活动请注意防暑。"
                else:
                    ai_suggestion = f"🌤️ 天气不错({weather_text})，适合按计划执行！"
            else:
                print("⚠️ [Weather] No forecast data available (maybe date out of range)")

    # --- 4. 写入数据库 ---
    new_task = Task(
        user_id="demo_user_001", # MVP 固定一个用户ID
        content=request.command, # 原始指令
        
        # AI 解析出的字段
        title=parsed_data.title,
        scheduled_time=parsed_data.scheduled_time,
        category=parsed_data.category,
        priority=parsed_data.priority,
        
        # 天气与建议
        weather_snapshot=weather_info, # 存入 JSON
        ai_suggestion=ai_suggestion
    )
    
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    
    return {
        "status": "success",
        "task_id": new_task.id,
        "parsed_title": new_task.title,
        "scheduled_time": new_task.scheduled_time,
        "location_used": search_city,
        "weather": weather_info.get("text", "N/A"),
        "suggestion": new_task.ai_suggestion
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