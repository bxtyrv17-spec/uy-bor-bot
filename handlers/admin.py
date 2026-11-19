from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Listing, ListingStatus

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.message(Command("admin"))
async def admin_panel(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    result = await session.execute(
        select(Listing).where(Listing.status == ListingStatus.inactive).order_by(Listing.id.desc())
    )
    listings = result.scalars().all()
    if not listings:
        await message.answer("✅ Kutayotgan e'lonlar yo'q.")
        return
    await message.answer(f"⏳ Kutayotgan e'lonlar: <b>{len(listings)}</b>", parse_mode="HTML")


@router.callback_query(F.data.startswith("approve_"))
async def approve_listing(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        return
    listing_id = int(callback.data.split("_")[1])
    listing = await session.get(Listing, listing_id)
    if not listing:
        await callback.answer("E'lon topilmadi!")
        return
    listing.status = ListingStatus.active
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>TASDIQLANDI</b>", parse_mode="HTML"
    )
    await callback.answer("✅ Tasdiqlandi!")

    # Egasiga xabar
    try:
        await callback.bot.send_message(
            listing.owner_id,
            f"✅ E'loningiz #{listing_id} tasdiqlandi va faollashtirildi!\n\n"
            "Endi boshqalar uni ko'ra oladi. Rahmat!"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("reject_"))
async def reject_listing(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        return
    listing_id = int(callback.data.split("_")[1])
    listing = await session.get(Listing, listing_id)
    if not listing:
        await callback.answer("E'lon topilmadi!")
        return
    listing.status = ListingStatus.sold  # "rejected" sifatida ishlatamiz
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>RAD ETILDI</b>", parse_mode="HTML"
    )
    await callback.answer("❌ Rad etildi!")

    # Egasiga xabar
    try:
        await callback.bot.send_message(
            listing.owner_id,
            f"❌ E'loningiz #{listing_id} rad etildi.\n\n"
            "Sabab: qoidalarga mos kelmadi yoki makler e'loni.\n"
            "Savollar uchun adminга murojaat qiling."
        )
    except Exception:
        pass
