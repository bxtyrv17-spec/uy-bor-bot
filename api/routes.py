from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from database.db import async_session
from database.models import Listing, ListingStatus, ListingType, PropertyType, User

router = APIRouter(prefix="/api")


async def get_db():
    async with async_session() as session:
        yield session


# --- Schemas ---

class ListingOut(BaseModel):
    id: int
    listing_type: str
    property_type: str
    city: str
    district: str
    rooms: int
    area: float
    floor: Optional[int]
    total_floors: Optional[int]
    price: float
    price_currency: str
    is_negotiable: bool
    description_uz: Optional[str]
    photos: list
    contact_phone: str
    views: int

    class Config:
        from_attributes = True


class ListingCreate(BaseModel):
    owner_id: int
    listing_type: str
    property_type: str
    city: str
    district: str
    rooms: int
    area: float
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    price: float
    price_currency: str = "USD"
    is_negotiable: bool = False
    description_uz: Optional[str] = None
    photos: list[str] = []
    contact_phone: str


# --- Endpoints ---

@router.get("/listings", response_model=list[ListingOut])
async def get_listings(
    listing_type: Optional[str] = None,
    city: Optional[str] = None,
    rooms: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    limit: int = Query(20, le=50),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    conditions = [Listing.status == ListingStatus.ACTIVE]
    if listing_type:
        conditions.append(Listing.listing_type == listing_type)
    if city:
        conditions.append(Listing.city == city)
    if rooms:
        conditions.append(Listing.rooms == rooms)
    if price_min:
        conditions.append(Listing.price >= price_min)
    if price_max:
        conditions.append(Listing.price <= price_max)

    result = await db.execute(
        select(Listing)
        .where(and_(*conditions))
        .order_by(Listing.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/listings/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: int, db: AsyncSession = Depends(get_db)):
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Topilmadi")
    listing.views += 1
    await db.commit()
    return listing


@router.post("/listings", response_model=ListingOut)
async def create_listing(data: ListingCreate, db: AsyncSession = Depends(get_db)):
    listing = Listing(**data.model_dump())
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


@router.get("/cities")
async def get_cities():
    return [
        "Toshkent", "Samarqand", "Buxoro", "Namangan",
        "Andijon", "Farg'ona", "Qarshi", "Nukus",
        "Termiz", "Jizzax", "Navoiy", "Urganch",
    ]
