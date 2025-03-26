import secrets
import string
from fastapi import HTTPException
from sqlalchemy import select, update, delete
from database import new_session, LinkOrm
from schemas import SLinkAdd, SLinkResponse
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    return unquote(url).lower().strip()


class LinkRepository:
    @staticmethod
    def generate_short_code(length: int = 8) -> str:
        """
        Генерация короткого кода для URL.
        """
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))


    @classmethod
    async def add_one(cls, data: SLinkAdd, user_id: Optional[int] = None) -> SLinkResponse:
        """
        Добавление новой ссылки в БД.
        """
        async with new_session() as session:
            try:
                normalized_url = normalize_url(str(data.original_url))

                if data.custom_alias:
                    existing_link = await cls.find_by_short_code(data.custom_alias)
                    if existing_link:
                        raise HTTPException(
                            status_code=400,
                            detail="Пользовательский алиас уже занят."
                        )
                    short_code = data.custom_alias
                else:
                    while True:
                        short_code = cls.generate_short_code()
                        existing_link = await cls.find_by_short_code(short_code)
                        if not existing_link:
                            break

                expires_at = data.expires_at if data.expires_at else datetime.utcnow() + timedelta(days=30)

                link = LinkOrm(
                    original_url=normalized_url,
                    short_code=short_code,
                    user_id=user_id,
                    expires_at=expires_at,
                )
                session.add(link)
                await session.flush()
                await session.commit()

                logger.debug(f"Link created: {link}")
                return SLinkResponse(
                    id=link.id,
                    original_url=link.original_url,
                    short_code=link.short_code,
                    created_at=link.created_at,
                    expires_at=link.expires_at,
                    user_id=link.user_id,
                    click_count=link.click_count,
                    short_url=None,
                )
            except HTTPException as e:
                raise e
            except Exception as e:
                logger.error(f"Error adding link: {e}")
                await session.rollback()
                raise HTTPException(status_code=500, detail="Internal Server Error")


    @classmethod
    async def find_by_short_code(cls, short_code: str) -> LinkOrm:
        """
        Поиск по короткому коду.
        """
        async with new_session() as session:
            query = select(LinkOrm).where(LinkOrm.short_code == short_code)
            result = await session.execute(query)
            return result.scalars().first()


    @classmethod
    async def find_by_original_url(cls, original_url: str) -> Optional[SLinkResponse]:
        """
        Поиск по оригинальному URL.
        """
        async with new_session() as session:
            normalized_url = normalize_url(original_url)
            logger.debug(f"Normalized URL: {normalized_url}")

            query = select(LinkOrm).where(LinkOrm.original_url == normalized_url)
            result = await session.execute(query)
            link = result.scalars().first()

            if link:
                logger.debug(f"Found link: {link.original_url}")
            else:
                logger.debug("Link not found")

            if not link:
                return None

            return SLinkResponse(
                id=link.id,
                original_url=link.original_url,
                short_code=link.short_code,
                created_at=link.created_at,
                expires_at=link.expires_at,
                user_id=link.user_id,
                click_count=link.click_count,
                short_url=f"http://127.0.0.1:8000/links/{link.short_code}",
            )


    @classmethod
    async def delete_by_short_code(cls, short_code: str, user_id: int):
        """
        Удаление ссылки по короткому коду.
        """
        async with new_session() as session:
            query = delete(LinkOrm).where(
                (LinkOrm.short_code == short_code) & (LinkOrm.user_id == user_id)
            )
            await session.execute(query)
            await session.commit()


    @classmethod
    async def update_original_url(cls, short_code: str, new_url: str, user_id: int) -> LinkOrm:
        """
        Обновление оригинального URL.
        """
        async with new_session() as session:
            try:
                normalized_url = normalize_url(new_url)

                query = update(LinkOrm).where(
                    (LinkOrm.short_code == short_code) & (LinkOrm.user_id == user_id)
                ).values(original_url=normalized_url)
                await session.execute(query)
                await session.commit()

                updated_link = await cls.find_by_short_code(short_code)
                if not updated_link:
                    logger.error(f"Failed to fetch updated link: short_code={short_code}")
                    return None

                return updated_link
            except Exception as e:
                logger.error(f"Error updating link in database: {e}")
                await session.rollback()
                return None


    @classmethod
    async def increment_click_count(cls, link_id: int):
        """
        Счетчик переходов по ссылке.
        """
        async with new_session() as session:
            query = update(LinkOrm).where(LinkOrm.id == link_id).values(click_count=LinkOrm.click_count + 1)
            await session.execute(query)
            await session.commit()


async def delete_expired_links():
    """
    Фоновая задача для удаления истекших ссылок.
    """
    while True:
        async with new_session() as session:
            try:
                query = delete(LinkOrm).where(LinkOrm.expires_at < datetime.utcnow())
                await session.execute(query)
                await session.commit()
                logger.info("Expired links deleted")
            except Exception as e:
                logger.error(f"Error deleting expired links: {e}")
                await session.rollback()

        await asyncio.sleep(1800)