from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Listing, ListingStatus, ListingType, PropertyType, User
from keyboards.main_kb import cities_kb, listing_nav_kb, listing_type_kb
from locales.uz import texts as uz

router = Router()

PROPERTY_ICONS = {
    "apartment": "🏢",
    "house": "🏡",
    "room": "🛏",
    "commercial": "🏪",
}

LISTING_TYPE_NAMES = {
    "sale": "Sotiladi",
    "rent": "Ijaraga beriladi",
    "daily": "Kunlik ijara",
}


class SearchState(StatesGroup):
    listing_type = State()
    city = State()
    rooms = State()
    price_min = State()
    price_max = State()
    viewing = State()


def format_listing(listing: Listing) -> str:
    icon = PROPERTY_ICONS.get(listing.property_type, "🏠")
    ltype = LISTING_TYPE_NAMES.get(listing.listing_type, "")
    ptype_names = {
        "apartment": "Kvartira",
        "house": "Uy",
        "room": "Xona",
        "commercial": "Tijorat mulki",
    }
    ptype = ptype_names.get(listing.property_type, "")

    floor_info = ""
    if listing.floor is not None and listing.total_floors:
        floor_info = f" | {listing.floor}/{listing.total_floors}-qavat"

    negotiable = " (Muzokarali)" if listing.is_negotiable else ""

    price_str = f"{listing.price:,.0f}".replace(",", " ")

    desc = ""
    if listing.description_uz:
        desc = f"\n📝 {listing.description_uz}"

    return (
        f"{icon} <b>{ptype}</b> — {ltype}\n\n"
        f"📍 {listing.city}, {listing.district}\n"
        f"🛏 {listing.rooms} xona | 📐 {listing.area} m²{floor_info}\n"
        f"💰 <b>{price_str} {listing.price_currency}</b>{negotiable}"
        f"{desc}\n\n"
        f"👁 Ko'rishlar: {listing.views}"
    )


@router.message(F.text == uz["btn_search"])
async def start_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.listing_type)
    await message.answer(uz["search_type"], reply_markup=listing_type_kb())


@router.callback_query(SearchState.listing_type, F.data.startswith("ltype:"))
async def search_listing_type(callback: CallbackQuery, state: FSMContext):
    ltype = callback.data.split(":")[1]
    await state.update_data(listing_type=ltype, results=[], page=0)
    await state.set_state(SearchState.city)
    await callback.message.edit_text(uz["search_city"], reply_markup=cities_kb(for_search=True))


@router.callback_query(SearchState.city, F.data.startswith("scity:"))
async def search_city(callback: CallbackQuery, state: FSMContext):
    city = callback.data.split(":")[1]
    # "other" tanlansa, barcha shaharlar
    await state.update_data(city=None if city == "other" else city)
    await state.set_state(SearchState.rooms)
    await callback.message.edit_text(
        "Xonalar sonini kiriting (1-10), yoki 0 — hammasi:"
    )


@router.message(SearchState.rooms)
async def search_rooms(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (0 <= int(message.text) <= 10):
        await message.answer(uz["error_invalid_number"])
        return
    rooms = int(message.text)
    await state.update_data(rooms=None if rooms == 0 else rooms)
    await state.set_state(SearchState.price_min)
    await message.answer("Minimal narx kiriting (0 = cheksiz):")


@router.message(SearchState.price_min)
async def search_price_min(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer(uz["error_invalid_number"])
        return
    await state.update_data(price_min=None if val == 0 else val)
    await state.set_state(SearchState.price_max)
    await message.answer("Maksimal narx kiriting (0 = cheksiz):")


@router.message(SearchState.price_max)
async def search_price_max(message: Message, state: FSMContext, session: AsyncSession):
    try:
        val = float(message.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer(uz["error_invalid_number"])
        return
    await state.update_data(price_max=None if val == 0 else val)

    data = await state.get_data()
    listings = await _do_search(session, data)

    if not listings:
        await state.clear()
        await message.answer(uz["no_results"])
        return

    await state.update_data(result_ids=[l.id for l in listings], page=0)
    await state.set_state(SearchState.viewing)

    await message.answer(
        uz["search_results"].format(count=len(listings)),
        parse_mode="HTML",
    )
    await show_listing(message, listings[0], 0, len(listings))

    # Ko'rishlar sonini oshirish
    listings[0].views += 1
    await session.commit()


async def _do_search(session: AsyncSession, data: dict) -> list[Listing]:
    conditions = [Listing.status == ListingStatus.ACTIVE]

    if data.get("listing_type"):
        conditions.append(Listing.listing_type == data["listing_type"])
    if data.get("city"):
        conditions.append(Listing.city == data["city"])
    if data.get("rooms"):
        conditions.append(Listing.rooms == data["rooms"])
    if data.get("price_min"):
        conditions.append(Listing.price >= data["price_min"])
    if data.get("price_max"):
        conditions.append(Listing.price <= data["price_max"])

    result = await session.execute(
        select(Listing)
        .where(and_(*conditions))
        .order_by(Listing.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


async def show_listing(message: Message, listing: Listing, index: int, total: int):
    text = format_listing(listing)
    kb = listing_nav_kb(listing.id, index, total)

    if listing.photos:
        if len(listing.photos) == 1:
            await message.answer_photo(
                photo=listing.photos[0],
                caption=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
        else:
            media = [InputMediaPhoto(media=p) for p in listing.photos[:10]]
            media[0].caption = text
            media[0].parse_mode = "HTML"
            await message.answer_media_group(media=media)
            await message.answer("👆 Yuqoridagi e'lon", reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(SearchState.viewing, F.data.startswith("nav:"))
async def navigate_listings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    index = int(callback.data.split(":")[1])
    data = await state.get_data()
    result_ids = data.get("result_ids", [])

    if index < 0 or index >= len(result_ids):
        await callback.answer()
        return

    listing = await session.get(Listing, result_ids[index])
    if not listing:
        await callback.answer("E'lon topilmadi")
        return

    listing.views += 1
    await session.commit()

    await state.update_data(page=index)
    text = format_listing(listing)
    kb = listing_nav_kb(listing.id, index, len(result_ids))

    if listing.photos:
        try:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("contact:"))
async def show_contact(callback: CallbackQuery, session: AsyncSession):
    listing_id = int(callback.data.split(":")[1])
    listing = await session.get(Listing, listing_id)
    if not listing:
        await callback.answer("E'lon topilmadi", show_alert=True)
        return

    owner = await session.get(User, listing.owner_id)
    contact_text = f"📞 Telefon: <code>{listing.contact_phone}</code>"
    if listing.show_username and owner and owner.username:
        contact_text += f"\n💬 Telegram: @{owner.username}"

    await callback.answer()
    await callback.message.answer(contact_text, parse_mode="HTML")


@router.callback_query(SearchState.viewing, F.data == "back_to_search")
async def back_to_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(uz["choose_action"])
    await callback.answer()
