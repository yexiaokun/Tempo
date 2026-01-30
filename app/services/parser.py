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
    temperature=0,
    # ⚠️ 关键修改：不要在这里强制指定 response_format，防止 API 报错
)

# 2. 初始化通用解析器
parser = PydanticOutputParser(pydantic_object=TaskExtraction)

async def parse_task_command(user_input: str) -> TaskExtraction:
    """
    通用版解析逻辑：不依赖 API 的 Function Calling 功能
    """
    # 获取当前时间
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    
    # 3. 构建提示词 (注入格式说明)
    # {format_instructions} 会自动生成一段话："The output should be formatted as a JSON instance..."
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        你是一个智能日程助手。当前时间是: {now_str}。
        请根据用户的输入，提取任务的关键信息。
        
        【重要规则】
        1. 如果是"明天"、"后天"等相对时间，请基于当前时间计算出准确的 ISO 时间 (YYYY-MM-DDTHH:MM:SS)。
        2. 如果用户没有指定具体时间点(只说了'晚上')，请给出一个合理的默认值(如 20:00:00)。
        3. 必须输出标准的 JSON 格式，不要包含任何 Markdown 标记（如 ```json）。
        
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
            "now_str": now_str
        })
        return result
    except Exception as e:
        print(f"AI 解析失败: {e}")
        # 如果解析失败，这里可以返回 None 或者抛出异常让上层处理
        return None