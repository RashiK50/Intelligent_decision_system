import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

# Make sure the URL uses the correct SQLAlchemy dialect if it defaults to 'postgres://'
if "postgresql://" in DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
# Debug: show the target host without leaking credentials into logs
_safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
print(f"DEBUG: Initializing SQLAlchemy against: {_safe_url}")

# 1. Create the SQLAlchemy Engine
# Using pool_pre_ping to check connection health before executing queries (great for Supabase)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True 
)

# 2. Create a configured Async Session class
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession
)

async def get_db_connection():
    """
    Dependency generator for FastAPI endpoints.
    Yields an async database session and safely closes it automatically.
    """
    async with AsyncSessionLocal() as session:
        yield session

async def execute_read_query(sql_query: str) -> list[dict]:
    """
    Executes a SELECT query asynchronously and returns a list of dictionaries.
    """
    try:
        # Use the async session maker directly
        async with AsyncSessionLocal() as session:
            # You must await the execution!
            result = await session.execute(text(sql_query))
            
            # .mappings() converts the raw SQLAlchemy rows into dictionary-like objects
            rows = result.mappings().all()
            return [dict(row) for row in rows]
            
    except Exception as e:
        raise e