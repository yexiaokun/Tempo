from openai import AsyncOpenAI
import os
from typing import List
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, col
from app.db.models import UserMemory
from dotenv import load_dotenv

load_dotenv()

class MemoryService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("EMBEDDING_API_KEY"),
            base_url=os.getenv("EMBEDDING_BASE_URL")
        )
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        调用 OpenAI 获取文本向量
        """
        try:
            response = await self.client.embeddings.create(
                input=text,
                model="BAAI/bge-m3"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ [Embedding Error] {e}")
            raise e
    
    async def add_memory(self, session: AsyncSession, user_id: int, content: str):
        """
        写入一条新记忆
        """
        vector = await self.get_embedding(content)
        memory = UserMemory(
            content=content,
            embedding=vector,
            user_id=user_id
        )
        session.add(memory)
        await session.commit()
        return memory
    
    async def search_relevant_memories(self, session: AsyncSession, user_id: int, query_text: str, limit: int = 3) -> str:
        """
        RAG 核心：搜索最相关的记忆，并拼成字符串返回
        """
        query_vector = await self.get_embedding(query_text)
        statement = select(UserMemory).where(
            UserMemory.user_id == user_id
        ).order_by(
            UserMemory.embedding.l2_distance(query_vector)
        ).limit(limit)

        results = await session.exec(statement)
        memories = results.all()

        if not memories:
            return ""
        
        context_str = ";".join([f"{m.content}" for m in memories])
        return context_str

memory_service = MemoryService()