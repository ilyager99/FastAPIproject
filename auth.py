import logging
import hashlib
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from passlib.context import CryptContext
from database import new_session, UserOrm, LinkOrm
from schemas import UserRegister, UserResponse

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

active_users: Dict[str, UserResponse] = {}

auth_router = APIRouter(prefix="/auth",
                        tags=["Аутентификация"])


def generate_user_secret_key(username: str) -> str:
    secret_key = hashlib.sha256(username.encode()).hexdigest()
    return secret_key


class AuthService:
    @classmethod
    async def register_user(cls, user_data: UserRegister) -> UserResponse:
        """
        Регистрация пользователя.
        """
        async with new_session() as session:
            try:
                existing_user = await session.execute(select(UserOrm).where(UserOrm.username == user_data.username))
                if existing_user.scalar():
                    raise HTTPException(status_code=400, detail="Username already exists")

                hashed_password = pwd_context.hash(user_data.password)

                user = UserOrm(username=user_data.username, password_hash=hashed_password)
                session.add(user)
                await session.flush()
                await session.commit()

                logger.info(f"User registered: {user.username}")
                return UserResponse(id=user.id, username=user.username)
            except Exception as e:
                logger.error(f"Error registering user: {e}")
                await session.rollback()
                raise HTTPException(status_code=500, detail="Internal Server Error")


    @classmethod
    async def authenticate_user(cls, username: str, password: str) -> UserOrm:
        """
        Аутентификация пользователя.
        """
        async with new_session() as session:
            user = await session.execute(select(UserOrm).where(UserOrm.username == username))
            user = user.scalar()
            if not user or not pwd_context.verify(password, user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid username or password")
            return user


    @classmethod
    async def get_current_user(cls, token: Optional[str] = Depends(oauth2_scheme)) -> Optional[UserResponse]:

        if token is None:
            logger.debug("Токен отсутствует")
            return None

        user = active_users.get(token)
        if user is None:
            logger.debug(f"Пользователь с токеном {token} не найден")
            return None

        logger.debug(f"Пользователь {user.username} успешно авторизован")
        return user


    @classmethod
    async def update_user_id_for_links(cls, username: str, user_id: int):
        """
        Обновление user_id для всех ссылок, созданных до авторизации.
        """
        async with new_session() as session:
            try:
                query = select(LinkOrm).where(LinkOrm.user_id.is_(None))
                result = await session.execute(query)
                links = result.scalars().all()

                for link in links:
                    link.user_id = user_id

                await session.commit()
                logger.info(f"Updated user_id for {len(links)} links")
            except Exception as e:
                logger.error(f"Error updating user_id for links: {e}")
                await session.rollback()
                raise HTTPException(status_code=500, detail="Internal Server Error")


@auth_router.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
):

    user_data = UserRegister(username=username, password=password)
    return await AuthService.register_user(user_data)


@auth_router.post("/token")
async def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
):

    user = await AuthService.authenticate_user(username, password)
    user_response = UserResponse(id=user.id, username=user.username)

    token = generate_user_secret_key(username)

    active_users[token] = user_response

    await AuthService.update_user_id_for_links(username, user.id)

    return {"access_token": token, "token_type": "bearer"}


get_current_user = AuthService.get_current_user