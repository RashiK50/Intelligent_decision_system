import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch Supabase connection string
# SQLAlchemy requires the dialect to be specified (e.g., postgresql+psycopg2://...)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

# Make sure the URL uses the correct SQLAlchemy dialect if it defaults to 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# 1. Create the SQLAlchemy Engine
# Using pool_pre_ping to check connection health before executing queries (great for Supabase)
engine = create_engine(
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

async def execute_read_query(query: str) -> list[dict]:
    """
    Utility function for the Database Executor Agent.
    Executes SELECT queries asynchronously and returns mapped rows.
    """
    async with engine.begin() as connection:
        # Await the execution of the query
        result = await connection.execute(text(query))
        
        # Fetch column names and map them to the row data
        columns = result.keys()
        
        # Return cleanly formatted list of dictionaries for the Output Agent
        return [dict(zip(columns, row)) for row in result.fetchall()]