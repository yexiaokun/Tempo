# app/services/parser.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser # 👈 改用通用解析器
from app.schemas import TaskExtraction
from datetime import datetime
import os

# 1. 初始化 LLM
llm = ChatOpenAI(
    model="deepseek-chat", 
    temperature=0.6,
    # ⚠️ 关键修改：不要在这里强制指定 response_format，防止 API 报错
)

# 2. 初始化通用解析器
parser = PydanticOutputParser(pydantic_object=TaskExtraction)

async def parse_task_command(user_input: str, user_context: str = "") -> TaskExtraction:
    """
    解析用户指令，提取任务信息，并生成高情商建议。
    """
    # 获取当前时间
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    
    # 3. 构建提示词 (注入格式说明)
    # {format_instructions} 会自动生成一段话："The output should be formatted as a JSON instance..."
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        你是一位**极具洞察力、温暖且风趣且高情商**的智能生活管家 Tempo。
        当前时间: {now_str}。
        
        【用户画像/记忆】
        {user_context}
        
        【任务目标】
        提取任务信息，并基于用户意图生成一句**高情商、有价值**的反馈 (Reasoning)。
        
        【🧠 Reasoning 生成策略 - 核心大脑】
        请先判断用户指令属于以下哪种情况，并按策略生成建议（严禁留空）：
        
        🚨 **情况一：存在冲突或风险 (最高优先级)**
        * **触发条件**：指令与【用户画像】（伤病、生理期、作息习惯）冲突。
        * **执行策略**：
           1. **Data Action**: 保持 'title' 为用户原始意图，但将你建议的**一个或多个**替代方案标题填入 **'suggested_titles'** 列表 (例如 ["去游泳", "去散步"])。
           2. **Reasoning**: 指出风险（语气温柔，像私人医生），提出具体的替代方案，并**必须以询问句结尾**，明确询问修改意向。
        * **话术模版**（必须包含类似意思）：
           "您的[身体部位]有[状况]，[原计划]风险较高。不如试试[替代方案]？**需要帮您将任务改为[替代方案]吗？**"
        
        ✅ **情况二：常规任务 (无冲突)**
        * **执行策略**：
           1. **Data Action**: **'suggested_titles' 必须为空列表 []**。
           2. **Reasoning**: 不要使用固定模版，请从以下维度自由发挥，语气自然活泼：
              - **专注与工作**："深呼吸，保持专注。记得设定番茄钟！"
              - **学习与成长**："积少成多，未来的你会感谢现在的自己。注意用眼哦！"
              - **运动与健康**："运动前记得热身，结束后做组拉伸，线条更漂亮！"
              - **休闲与社交**："太棒了！工作先抛脑后，尽情享受这段时光吧！"
              - **琐事与家务**："放首喜欢的歌边听边做，家务也能变成解压方式。"
              - **深夜任务**："这么晚还在努力？处理完快去休息，身体才是革命的本钱。"

        【通用原则】
        1. **不要**直接修改 'title'，保留用户原始意图（因为我们要先问用户）。
        2. **Reasoning** 必须简练有力（50字以内）。
        3. 遇到健康风险时，将 'priority' 设为 'High'。
        4. 时间处理：根据当前时间推算 ISO 格式时间。
        
        {format_instructions}
        """),
        ("human", "{text}"),
    ])
    
    # 4. 组装链 (Prompt -> LLM -> Parser)
    # 这里通过 partial_variables 注入解析器的指令
    chain = prompt.partial(format_instructions=parser.get_format_instructions()) | llm | parser
    
    # 5. 调用
    try:
        # PydanticOutputParser 会自动尝试修复简单的 JSON 错误
        result = await chain.ainvoke({
            "text": user_input,
            "now_str": now_str,
            "user_context": user_context if user_context else "暂无特殊背景信息"
        })
        return result
    except Exception as e:
        print(f"AI 解析失败: {e}")
        # 如果解析失败，这里可以返回 None 或者抛出异常让上层处理
        return None
    