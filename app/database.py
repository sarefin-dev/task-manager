import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncEngine, AsyncSession

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create async engine
engine = AsyncEngine(
    create_async_engine(
        DATABASE_URL,
        echo=True,  # Set to False in production
        future=True,
    )
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Dependency for getting DB session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
