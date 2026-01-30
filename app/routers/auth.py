from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.database import get_session
from app.db.models import User
from app.core.security import verity_password, create_access_token, get_password_hash
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])

class UserRegister(BaseModel):
    username: str
    password: str
    email: str
    default_city: str = "Beijing"


@router.post("/register")
async def register(user_data: UserRegister, session: AsyncSession = Depends(get_session)):
    """用户注册接口"""
    result = await session.exec(select(User).where(User.username == user_data.username))
    if result.first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    print(f"DEBUG: Hashing password: {user_data.password} (Type: {type(user_data.password)})")
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        default_city=user_data.default_city
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {"msg": "User created successfully"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                session: AsyncSession = Depends(get_session)
                ):
    """
    OAuth2 标准登录接口
    Swagger UI 自动通过form_data发送用户名和密码
    """
    
    result = await session.exec(select(User).where(User.username == form_data.username))
    user = result.first()
    
    if not user or not verity_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.username)
    
    return {"access_token": access_token, "token_type": "bearer"}