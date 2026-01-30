from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import async_session
from app.db.models import Task, TaskStatus
from sqlmodel import select
from datetime import datetime, timedelta

scheduler = AsyncIOScheduler()

async def check_upcoming_tasks():
    """
    【定时任务】每隔5分钟执行一次
    扫描未来1小时内需要执行的任务，并发送提醒
    """
    print(f"⏰ [Scheduler] Scanning for upcoming tasks at {datetime.now()}...")
    async with async_session() as session:
        now = datetime.now()
        one_hour_later = now + timedelta(hours=1)

        statement = select(Task).where(
            Task.status == TaskStatus.TODO,
            Task.scheduled_time >= now,
            Task.scheduled_time <= one_hour_later
        )

        result = await session.exec(statement)
        tasks = result.all()

        if not tasks:
            print("💤 No upcoming tasks found.")
            return
        
        for task in tasks:
            print(f"""
            🔔 【提醒】任务即将开始！
            --------------------------------
            标题: {task.title}
            时间: {task.scheduled_time}
            建议: {task.ai_suggestion}
            --------------------------------
            """)
            # (进阶功能: 这里可以再次调用 WeatherService 检查实时天气，如果下雨了就发警告)

def start_scheduler():
    """启动调度器"""
    # 1分钟1次，为了测试
    scheduler.add_job(check_upcoming_tasks, "interval", minutes=1)
    scheduler.start()
    print("🚀 APScheduler started!")