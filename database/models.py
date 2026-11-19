from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum,
    Float, ForeignKey, Integer, JSON, String, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ListingType(str, PyEnum):
    SALE = "sale"           # Sotish
    RENT = "rent"           # Uzoq muddatli ijara
    DAILY = "daily"         # Kunlik ijara


class PropertyType(str, PyEnum):
    APARTMENT = "apartment"   # Kvartira
    HOUSE = "house"           # Uy
    ROOM = "room"             # Xona
    COMMERCIAL = "commercial" # Tijorat


class ListingStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram user_id
    username = Column(String(64), nullable=True)
    full_name = Column(String(128))
    phone = Column(String(20), nullable=True)
    language = Column(String(2), default="uz")  # uz / ru
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    listings = relationship("Listing", back_populates="owner")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"))

    listing_type = Column(Enum(ListingType))
    property_type = Column(Enum(PropertyType))
    status = Column(Enum(ListingStatus), default=ListingStatus.ACTIVE)

    # Joylashuv
    city = Column(String(64))          # Shahar
    district = Column(String(64))      # Tuman
    address = Column(String(256), nullable=True)

    # Uy haqida
    rooms = Column(Integer)            # Xonalar soni
    floor = Column(Integer, nullable=True)
    total_floors = Column(Integer, nullable=True)
    area = Column(Float)               # Maydon (m²)

    # Narx
    price = Column(Float)
    price_currency = Column(String(3), default="USD")  # USD / UZS
    is_negotiable = Column(Boolean, default=False)

    # Tavsif
    description_uz = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)

    # Rasmlar (Telegram file_id lar)
    photos = Column(JSON, default=[])

    # Murojaat
    contact_phone = Column(String(20))
    show_username = Column(Boolean, default=True)

    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="listings")
