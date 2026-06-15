import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base
from app.models import (
    TransparenciaCargaJob,
    TransparenciaCargaJobItem,
    Estado,
    Municipio,
)

# Use SQLite in-memory for testing, with shared cache so multiple connections see the same DB
SYNC_TEST_DATABASE_URL = "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"
ASYNC_TEST_DATABASE_URL = "sqlite+aiosqlite:///file:memdb1?mode=memory&cache=shared&uri=true"

# Removed mock_datacrypt_schema fixture

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        SYNC_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    for table in Base.metadata.tables.values():
        table.schema = None
        
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def db(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    session.begin_nested()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="session")
def async_engine(engine):
    async_eng = create_async_engine(
        ASYNC_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield async_eng

@pytest.fixture(scope="function")
async def async_db(async_engine):
    TestingAsyncSessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=async_engine,
        class_=AsyncSession
    )
    
    async with TestingAsyncSessionLocal() as session:
        await session.begin_nested()
        yield session
        await session.rollback()
