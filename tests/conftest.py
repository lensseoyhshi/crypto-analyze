"""Pytest configuration and fixtures."""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.models import Base


@pytest.fixture(scope="session")
def event_loop():
	"""Create an instance of the default event loop for the test session."""
	loop = asyncio.get_event_loop_policy().new_event_loop()
	yield loop
	loop.close()


@pytest.fixture(scope="function")
async def db_engine():
	"""Create a test database engine."""
	# Use in-memory SQLite for testing
	engine = create_async_engine(
		"sqlite+aiosqlite:///:memory:",
		echo=False
	)
	
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
	
	yield engine
	
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)
	
	await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
	"""Create a test database session."""
	async_session = async_sessionmaker(
		db_engine,
		class_=AsyncSession,
		expire_on_commit=False
	)
	
	async with async_session() as session:
		yield session

