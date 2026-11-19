from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Listing, ListingStatus, User

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


PROP_NAMES = {
    "ru": {"apartment": "Квартира", "house": "Дом", "room": "Комната", "commercial": "Коммерция"},
    "uz": {"apartment": "Kvartira", "house": "Uy", "room": "Xona", "commercial": "Tijorat"},
    "en": {"apartment": "Apartment", "house": "House", "room": "Room", "commercial": "Commercial"},
}
LTYPE_NAMES = {
    "ru": {"sale": "продаётся", "rent": "сдаётся", "daily": "посуточно"},
    "uz": {"sale": "sotiladi", "rent": "ijaraga", "daily": "kunlik ijara"},
    "en": {"sale": "for sale", "rent": "for rent", "daily": "daily rent"},
}
HEADERS = {
    "ru": "🏠 Новое объявление",
    "uz": "🏠 Yangi e'lon",
    "en": "🏠 New listing",
}
BTN_LABELS = {
    "ru": "Смотреть объявление",
    "uz": "E'lonni ko'rish",
    "en": "View listing",
}


def _build_broadcast_text(listing: Listing, lang: str) -> str:
    lang = lang if lang in ("ru", "uz", "en") else "uz"
    prop = PROP_NAMES[lang].get(listing.property_type, listing.property_type)
    ltype = LTYPE_NAMES[lang].get(listing.listing_type, listing.listing_type)
    header = HEADERS[lang]
    floor_str = f"{listing.floor}/{listing.total_floors}" if listing.floor else "—"
    price_str = f"{listing.price:,.0f}".replace(",", " ")
    neg = {
        "ru": " (Договорная)", "uz": " (Kelishiladi)", "en": " (Negotiable)"
    }[lang] if listing.is_negotiable else ""

    desc = ""
    if listing.description_uz:
        desc = f"\n🔘{listing.description_uz}\n"

    return (
        f"⚪️ <b>{header}</b>\n\n"
        f"🔘{prop} — {ltype}\n"
        f"🔘{listing.city}, {listing.district}\n"
        f"🔘{listing.rooms} {'xona' if lang == 'uz' else ('комн.' if lang == 'ru' else 'rooms')}\n"
        f"🔘{'Qavat' if lang == 'uz' else ('Этаж' if lang == 'ru' else 'Floor')}: {floor_str}\n"
        f"🔘{listing.area} m²"
        f"{desc}\n"
        f"💸 <b>{price_str} {listing.price_currency}</b>{neg}"
    )


async def _broadcast_listing(bot, session: AsyncSession, listing: Listing):
    result = await session.execute(select(User))
    users = result.scalars().all()

    webapp_url = settings.WEBAPP_URL or "https://uy-bor-bot.onrender.com"
    app_url = f"{webapp_url}?listing={listing.id}"

    for user in users:
        if user.id == listing.owner_id:
            continue
        lang = user.language or "uz"
        text = _build_broadcast_text(listing, lang)
        btn_label = BTN_LABELS.get(lang, BTN_LABELS["uz"])
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=btn_label, web_app=WebAppInfo(url=app_url))
        ]])
        try:
            if listing.photos:
                await bot.send_photo(user.id, listing.photos[0], caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await bot.send_message(user.id, text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


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
    await session.commit()
    try:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n✅ <b>TASDIQLANDI</b>", parse_mode="HTML"
        )
    except Exception:
        pass
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

    # Barcha foydalanuvchilarga broadcast
    await _broadcast_listing(callback.bot, session, listing)


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
