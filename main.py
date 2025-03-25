from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from database import create_tables, delete_tables
from router import router as links_router
from auth import auth_router
from contextlib import asynccontextmanager
from repository import delete_expired_links
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await delete_tables()
    logger.info("База очищена")
    await create_tables()
    logger.info("База готова к работе")

    asyncio.create_task(delete_expired_links())

    yield
    logger.info("Выключение")

app = FastAPI(lifespan=lifespan)
app.include_router(links_router)
app.include_router(auth_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="URL Shortener API",
        version="1.0.0",
        description="API для сокращения ссылок",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/auth/token",
                    "scopes": {}
                }
            }
        }
    }

    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi