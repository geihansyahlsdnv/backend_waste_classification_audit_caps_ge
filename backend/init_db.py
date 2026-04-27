import asyncio
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())

from app.db.session import engine

async def create_tables_manual():
    async with engine.begin() as conn:
        print("Force creating 'detection' table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS detection (
                id UUID PRIMARY KEY,
                result_id UUID NOT NULL REFERENCES classificationresult(id) ON DELETE CASCADE,
                label VARCHAR(50) NOT NULL,
                confidence FLOAT NOT NULL,
                box_2d VARCHAR(100),
                CONSTRAINT fk_result FOREIGN KEY(result_id) REFERENCES classificationresult(id)
            );
        """))
        await conn.execute(text("ALTER TABLE detection OWNER TO hargai_user;"))
    print("Done! Coba cek \dt lagi.")

if __name__ == "__main__":
    asyncio.run(create_tables_manual())