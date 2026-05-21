import asyncio
from decimal import Decimal

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import WasteType


# Edit this list once ML dev confirms the full label set.
# Tuples: (label_name, category, unit, price_per_unit, currency)
# Categories must be either 'recyclable' or 'non-recyclable'.
WASTE_TYPES = [
    # Observed in current audit history
    ("plastic_bottle",          "recyclable",     "kg", Decimal("3000"), "IDR"),
    ("chemical_plastic_gallon", "non-recyclable", "kg", Decimal("1500"), "IDR"),
    ("plastic_cup_lid",         "recyclable",     "kg", Decimal("2000"), "IDR"),
    ("scrap_paper",             "recyclable",     "kg", Decimal("1000"), "IDR"),

    # Add more labels here once confirmed with ML dev
    # Example:
    # ("aluminum_can",          "recyclable",     "kg", Decimal("8000"), "IDR"),
    # ("cardboard",             "recyclable",     "kg", Decimal("1200"), "IDR"),
    # ("glass_bottle",          "recyclable",     "kg", Decimal("500"),  "IDR"),
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
        print(f"\nDone. Added: {added}, Skipped: {skipped}, Total in list: {len(WASTE_TYPES)}")


if __name__ == "__main__":
    asyncio.run(seed())