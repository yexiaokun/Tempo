from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.database import get_session
from app.core.security import SECRET_KEY, ALGORITHM
from app.db.models import User

# 🌟 关键配置：告诉 Swagger UI，Token 接口的地址在哪里
# 这里的 tokenUrl 必须和 router 里的路径一致
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    核心依赖：
    1. 从请求头解析 Token
    2. 验证 Token 有效性
    3. 从数据库查出 User 对象
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解码 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # 查数据库
    result = await session.exec(select(User).where(User.username == username))
    user = result.first()
    if user is None:
        raise credentials_exception
        
    return user