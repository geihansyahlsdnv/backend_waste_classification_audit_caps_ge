import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.db.models import User
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./waste.db")

async def get_users():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("Belum ada user yang terdaftar di database.")
        else:
            print(f"Total {len(users)} user terdaftar:\n")
            print(f"{'ID':<38} | {'Username':<15} | {'Email':<25} | {'Role'}")
            print("-" * 90)
            for user in users:
                print(f"{str(user.id):<38} | {user.username:<15} | {user.email:<25} | {user.role}")

if __name__ == "__main__":
    asyncio.run(get_users())
