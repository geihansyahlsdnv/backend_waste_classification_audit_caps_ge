"""
Seed script for the waste_type table.

USAGE:
    docker compose -f docker-compose.production.yml exec backend python seed_waste_types.py

Run this once after deployment to populate the waste_type table.
The script is idempotent — re-running skips existing entries.
Prices are in IDR per kg. Update as needed with supervisor account via PATCH /waste-types/{id}/price.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import WasteType

WASTE_TYPES = [
    # (label_name, category, unit, price_per_kg, currency)
    ("cardboard",  "recyclable",     "kg", Decimal("1500"), "IDR"),
    ("compost",    "non-recyclable", "kg", Decimal("500"),  "IDR"),
    ("glass",      "recyclable",     "kg", Decimal("1000"), "IDR"),
    ("metal",      "recyclable",     "kg", Decimal("8000"), "IDR"),
    ("paper",      "recyclable",     "kg", Decimal("2000"), "IDR"),
    ("plastic",    "recyclable",     "kg", Decimal("3000"), "IDR"),
    ("trash",      "non-recyclable", "kg", Decimal("0"),    "IDR"),
]


async def seed():
    async with AsyncSessionLocal() as db:
        added = 0
        skipped = 0
        for name, category, unit, price, currency in WASTE_TYPES:
            existing = await db.scalar(select(WasteType).where(WasteType.name == name))
            if existing:
                print(f"  [SKIP] {name} already exists")
                skipped += 1
                continue

            wt = WasteType(
                name=name,
                category=category,
                unit=unit,
                current_price=price,
                currency=currency,
            )
            db.add(wt)
            print(f"  [ADD]  {name} = {price} {currency}/{unit}")
            added += 1

        await db.commit()
        print(f"\nDone. Added: {added}, Skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(seed())