"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from ..core.config import settings

# Synchronous engine for Alembic migrations
sync_engine = create_engine(
	settings.DATABASE_URL.replace("aiomysql", "pymysql"),
	pool_pre_ping=True,
	pool_size=5,
	max_overflow=10
)

# Async engine for application use
async_engine = create_async_engine(
	settings.DATABASE_URL,
	pool_pre_ping=True,
	pool_size=5,
	max_overflow=10,
	echo=False
)

# Synchronous session for migrations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Async session for application
AsyncSessionLocal = async_sessionmaker(
	async_engine,
	class_=AsyncSession,
	expire_on_commit=False,
	autocommit=False,
	autoflush=False
)

Base = declarative_base()


def get_db():
	"""Synchronous DB session dependency (for migrations and sync operations)."""
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


async def get_async_session():
	"""Async DB session dependency for FastAPI routes and background tasks."""
	async with AsyncSessionLocal() as session:
		try:
			yield session
		except Exception:
			await session.rollback()
			raise
		finally:
			await session.close()

