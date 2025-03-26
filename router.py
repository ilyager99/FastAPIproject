from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import RedirectResponse
from repository import LinkRepository
from schemas import SLinkAdd, SLinkResponse, UserResponse, SLinkStatsResponse
from auth import get_current_user
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/links",
    tags=["Ссылки"],
)

@router.get("/search", response_model=SLinkResponse)
async def search_link_by_original_url(
    original_url: str,
    request: Request,
):
    """
    Поиск ссылки по оригинальному URL.
    """
    link = await LinkRepository.find_by_original_url(original_url)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    link.short_url = f"{request.base_url}links/{link.short_code}"
    return link


@router.post("/shorten", response_model=SLinkResponse)
async def shorten_link(
    request: Request,
    original_url: str = Form(...),
    custom_alias: Optional[str] = Form(None),
    expires_at: Optional[datetime] = Form(None),
    user: Optional[UserResponse] = Depends(get_current_user),
) -> SLinkResponse:
    """
    Создание короткой ссылки для оригинального URL.
    """
    try:
        user_id = user.id if user else None
        link_data = SLinkAdd(original_url=original_url, custom_alias=custom_alias, expires_at=expires_at)
        link = await LinkRepository.add_one(link_data, user_id=user_id)
        return SLinkResponse(
            id=link.id,
            original_url=link.original_url,
            short_code=link.short_code,
            created_at=link.created_at,
            expires_at=link.expires_at,
            user_id=link.user_id,
            click_count=link.click_count,
            short_url=f"{request.base_url}links/{link.short_code}",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating link: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/{short_code}")
async def redirect_link(short_code: str):
    """
    Перенаправление на оригинальный URL по короткой ссылке.
    """
    link = await LinkRepository.find_by_short_code(short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    await LinkRepository.increment_click_count(link.id)
    return RedirectResponse(url=link.original_url)


@router.delete("/{short_code}")
async def delete_link(
    short_code: str,
    user: Optional[UserResponse] = Depends(get_current_user),
):
    """
    Удаление короткой ссылки.
    """
    if user is None:
        raise HTTPException(status_code=403, detail="Необходима авторизация для удаления ссылки")

    link = await LinkRepository.find_by_short_code(short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    if link.user_id != user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления ссылки")

    await LinkRepository.delete_by_short_code(short_code, user.id)
    return {"ok": True}


@router.put("/{short_code}", response_model=SLinkResponse)
async def update_link(
    short_code: str,
    new_url: str = Form(...),
    user: Optional[UserResponse] = Depends(get_current_user),
) -> SLinkResponse:
    """
    Обновление оригинального URL для короткой ссылки.
    """
    if user is None:
        raise HTTPException(status_code=403, detail="Необходима авторизация для изменения ссылки")

    link = await LinkRepository.find_by_short_code(short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    if link.user_id != user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для обновления ссылки")

    updated_link = await LinkRepository.update_original_url(short_code, new_url, user.id)
    if not updated_link:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении ссылки")

    return SLinkResponse(
        id=updated_link.id,
        original_url=updated_link.original_url,
        short_code=updated_link.short_code,
        created_at=updated_link.created_at,
        expires_at=updated_link.expires_at,
        user_id=updated_link.user_id,
        click_count=updated_link.click_count,
        short_url=None,
    )


@router.get("/{short_code}/stats", response_model=SLinkStatsResponse)
async def link_stats(short_code: str) -> SLinkStatsResponse:
    """
    Статистика по короткой ссылке.
    """
    link = await LinkRepository.find_by_short_code(short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    return SLinkStatsResponse(
        original_url=link.original_url,
        created_at=link.created_at,
        click_count=link.click_count,
        last_used_at=link.last_used_at,
    )
