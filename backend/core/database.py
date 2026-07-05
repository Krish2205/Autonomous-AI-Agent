import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Text, DateTime, PrimaryKeyConstraint, func
import asyncio

logger = logging.getLogger("core.database")

# Detect PostgreSQL connection parameters from environment (Supabase)
# Fallback to local async sqlite: sqlite+aiosqlite:///data/databases/jarvis.db
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgresql://"):
    # SQLAlchemy asyncpg driver replacement
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgres://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")
else:
    from backend.config import DATA_DIR
    db_path = os.path.join(DATA_DIR, "databases", "jarvis.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    ASYNC_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

logger.info(f"Connecting to database via URL: {ASYNC_DATABASE_URL.split('@')[-1] if '@' in ASYNC_DATABASE_URL else ASYNC_DATABASE_URL}")

# Create database engine
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# ── SQLAlchemy Models ────────────────────────────────────────────────
class ProfileConfig(Base):
    __tablename__ = "profile_configs"
    user_id = Column(String, primary_key=True)
    config = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    session_id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(String, default="New Chat")
    messages = Column(Text)
    history_summary = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    user_id = Column(String)
    filename = Column(String)
    chunk_id = Column(String)
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "filename", "chunk_id"),
    )

# Backward compatible connection mock
class SQLiteConnectionCompat:
    """Mock connection context mapping standard sqlite cursor calls to async SQLAlchemy transactions."""
    class MockCursor:
        def __init__(self, session: AsyncSession):
            self.session = session
            self._last_row_count = 0
            self._last_result = []

        def execute(self, sql: str, params=None):
            # Parse parameters to SQL placeholder conversions if using PostgreSQL
            is_postgres = "postgresql" in str(self.session.bind.url)
            if is_postgres:
                sql = sql.replace("?", "%s")
                # Map SQLite INSERT ON CONFLICT parameters to PostgreSQL dialect if required
                if "ON CONFLICT(user_id) DO UPDATE" in sql:
                    sql = sql.replace("excluded.config", "EXCLUDED.config")
                elif "ON CONFLICT(session_id) DO UPDATE" in sql:
                    sql = sql.replace("excluded.messages", "EXCLUDED.messages")
                    sql = sql.replace("excluded.title", "EXCLUDED.title")
                    sql = sql.replace("excluded.history_summary", "EXCLUDED.history_summary")
                
            # Perform query block synchronously wrapped in asyncio runner
            coro = self.session.execute(sql, params or ())
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            res = loop.run_until_complete(coro)
            self._last_row_count = res.rowcount
            if res.returns_rows:
                self._last_result = [dict(row) for row in res.mappings().all()]
            else:
                self._last_result = []

        def fetchone(self):
            return self._last_result[0] if self._last_result else None

        def fetchall(self):
            return self._last_result

        @property
        def description(self):
            return [("column",)] if self._last_result else None

        @property
        def rowcount(self):
            return self._last_row_count

    def __init__(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        self.session = loop.run_until_complete(AsyncSessionLocal().__aenter__())

    def cursor(self):
        return self.MockCursor(self.session)

    def commit(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.session.commit())

    def rollback(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.session.rollback())

    def close(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.session.close())

    def execute(self, sql: str, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur


def get_db_connection():
    """Retrieve backward-compatible wrapper database connection."""
    return SQLiteConnectionCompat()


def init_db() -> None:
    """Initialize relational databases schema on startup."""
    logger.info("Initializing relational database models via SQLAlchemy...")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    loop.run_until_complete(create_tables())
    logger.info("Relational database schemas synced successfully.")
