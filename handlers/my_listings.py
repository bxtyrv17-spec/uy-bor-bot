from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Listing, ListingStatus
from keyboards.main_kb import main_menu_kb, my_listing_kb
from locales.uz import texts as uz
from handlers.search import format_listing

router = Router()


@router.message(F.text == uz["btn_my_listings"])
async def show_my_listings(message: Message, session: AsyncSession):
    result = await session.execute(
        select(Listing)
        .where(Listing.owner_id == message.from_user.id)
        .where(Listing.status != ListingStatus.SOLD)
        .order_by(Listing.created_at.desc())
    )
    listings = result.scalars().all()

    if not listings:
        await message.answer(uz["my_listings_empty"], reply_markup=main_menu_kb())
        return

    await message.answer(f"📋 Sizning e'lonlaringiz: <b>{len(listings)} ta</b>", parse_mode="HTML")

    for listing in listings:
        status_icon = "✅" if listing.status == ListingStatus.ACTIVE else "⏸"
        text = f"{status_icon} #{listing.id}\n" + format_listing(listing)
        kb = my_listing_kb(listing.id, listing.status == ListingStatus.ACTIVE)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_listing(callback: CallbackQuery, session: AsyncSession):
    listing_id = int(callback.data.split(":")[1])
    listing = await session.get(Listing, listing_id)

    if not listing or listing.owner_id != callback.from_user.id:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    if listing.status == ListingStatus.ACTIVE:
        listing.status = ListingStatus.INACTIVE
        msg = "⏸ E'lon to'xtatildi."
    else:
        listing.status = ListingStatus.ACTIVE
        msg = "✅ E'lon faollashtirildi."

    await session.commit()
    kb = my_listing_kb(listing.id, listing.status == ListingStatus.ACTIVE)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(msg)


@router.callback_query(F.data.startswith("delete:"))
async def delete_listing(callback: CallbackQuery, session: AsyncSession):
    listing_id = int(callback.data.split(":")[1])
    listing = await session.get(Listing, listing_id)

    if not listing or listing.owner_id != callback.from_user.id:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    await session.delete(listing)
    await session.commit()
    await callback.message.delete()
    await callback.answer(uz["listing_deleted"])


@router.callback_query(F.data == "my_listings")
async def back_to_my_listings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.delete()
    await show_my_listings(callback.message, session)
    await callback.answer()
