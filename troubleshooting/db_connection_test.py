"""
Database connection test script to verify SQLAlchemy async setup and connection handling.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.base import Base

async def test_db_connection():
    try:
        # Create async engine
        engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=True)
        
        # Create test session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        print("Testing database connection...")
        
        async with async_session() as session:
            # Try a simple query
            result = await session.execute("SELECT 1")
            print("Database connection successful!")
            print(f"Test query result: {result.scalar()}")

        await engine.dispose()
        
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise

async def verify_greenlet_context():
    """Verify that we're running in the correct greenlet context"""
    from greenlet import getcurrent
    print(f"Current greenlet: {getcurrent()}")
    print(f"Greenlet parent: {getcurrent().parent}")

async def main():
    print("Starting database connection tests...")
    await verify_greenlet_context()
    await test_db_connection()
    print("Tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
