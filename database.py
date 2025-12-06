import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///simpleisp.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def init_db():
    # Import models here so SQLModel creates tables (lazy import to avoid circular dependency)
    from modules.auth.models import User  # noqa: F401
    from modules.clients.models import Client  # noqa: F401
    from modules.routers.models import Router  # noqa: F401
    from modules.billing.models import Payment  # noqa: F401
    from modules.settings.models import Settings  # noqa: F401
    
    # Create all tables in the database
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
