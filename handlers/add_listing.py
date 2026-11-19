from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Listing, ListingStatus, ListingType, PropertyType, User
from keyboards.main_kb import (
    cities_kb, currency_kb,
    listing_type_kb, property_type_kb, yes_no_kb,
)
from aiogram.types import ReplyKeyboardRemove
from locales.uz import texts as uz

router = Router()


class AddListing(StatesGroup):
    listing_type = State()
    property_type = State()
    city = State()
    district = State()
    rooms = State()
    area = State()
    floor = State()
    total_floors = State()
    price = State()
    currency = State()
    negotiable = State()
    description = State()
    photos = State()
    confirm = State()


@router.message(F.text == uz["btn_add_listing"])
async def start_add_listing(message: Message, state: FSMContext, session: AsyncSession):
    # Telefon tasdiqlanganmi?
    user = await session.get(User, message.from_user.id)
    if not user or not user.phone:
        await message.answer(
            "⚠️ E'lon qo'yish uchun avval ro'yxatdan o'ting.\n\n"
            "Botni qayta ishga tushiring: /start"
        )
        return

    # Maksimal e'lon tekshiruvi
    count = await session.scalar(
        select(func.count()).where(
            Listing.owner_id == message.from_user.id,
            Listing.status != ListingStatus.SOLD,
        )
    )
    if count >= settings.MAX_LISTING_PER_USER:
        await message.answer(
            uz["error_too_many_listings"].format(max=settings.MAX_LISTING_PER_USER)
        )
        return

    await state.set_state(AddListing.listing_type)
    await message.answer(uz["add_listing_type"], reply_markup=listing_type_kb())


@router.callback_query(AddListing.listing_type, F.data.startswith("ltype:"))
async def choose_listing_type(callback: CallbackQuery, state: FSMContext):
    ltype = callback.data.split(":")[1]
    await state.update_data(listing_type=ltype)
    await state.set_state(AddListing.property_type)
    await callback.message.edit_text(uz["add_property_type"], reply_markup=property_type_kb())


@router.callback_query(AddListing.property_type, F.data.startswith("ptype:"))
async def choose_property_type(callback: CallbackQuery, state: FSMContext):
    ptype = callback.data.split(":")[1]
    await state.update_data(property_type=ptype)
    await state.set_state(AddListing.city)
    await callback.message.edit_text(uz["add_city"], reply_markup=cities_kb())


@router.callback_query(AddListing.city, F.data.startswith("city:"))
async def choose_city(callback: CallbackQuery, state: FSMContext):
    city = callback.data.split(":")[1]
    await state.update_data(city=city)
    await state.set_state(AddListing.district)
    await callback.message.edit_text(uz["add_district"])


@router.message(AddListing.district)
async def enter_district(message: Message, state: FSMContext):
    await state.update_data(district=message.text)
    await state.set_state(AddListing.rooms)
    await message.answer(uz["add_rooms"])


@router.message(AddListing.rooms)
async def enter_rooms(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 10):
        await message.answer(uz["error_invalid_number"])
        return
    await state.update_data(rooms=int(message.text))
    await state.set_state(AddListing.area)
    await message.answer(uz["add_area"])


@router.message(AddListing.area)
async def enter_area(message: Message, state: FSMContext):
    try:
        area = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer(uz["error_invalid_number"])
        return
    await state.update_data(area=area)
    await state.set_state(AddListing.floor)
    await message.answer(uz["add_floor"])


@router.message(AddListing.floor)
async def enter_floor(message: Message, state: FSMContext):
    if not message.text.lstrip("-").isdigit():
        await message.answer(uz["error_invalid_number"])
        return
    await state.update_data(floor=int(message.text))
    await state.set_state(AddListing.total_floors)
    await message.answer(uz["add_total_floors"])


@router.message(AddListing.total_floors)
async def enter_total_floors(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(uz["error_invalid_number"])
        return
    await state.update_data(total_floors=int(message.text))
    await state.set_state(AddListing.price)
    await message.answer(uz["add_price"])


@router.message(AddListing.price)
async def enter_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer(uz["error_invalid_number"])
        return
    await state.update_data(price=price)
    await state.set_state(AddListing.currency)
    await message.answer(uz["add_currency"], reply_markup=currency_kb())


@router.callback_query(AddListing.currency, F.data.startswith("currency:"))
async def choose_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split(":")[1]
    await state.update_data(currency=currency)
    await state.set_state(AddListing.negotiable)
    await callback.message.edit_text(uz["add_negotiable"], reply_markup=yes_no_kb("neg"))


@router.callback_query(AddListing.negotiable, F.data.startswith("neg:"))
async def choose_negotiable(callback: CallbackQuery, state: FSMContext):
    is_neg = callback.data.split(":")[1] == "yes"
    await state.update_data(is_negotiable=is_neg)
    await state.set_state(AddListing.description)
    await callback.message.edit_text(uz["add_description"])


@router.message(AddListing.description)
async def enter_description(message: Message, state: FSMContext):
    desc = None if message.text == "/skip" else message.text
    await state.update_data(description=desc)
    await state.set_state(AddListing.photos)
    await message.answer(uz["add_photos"])


@router.message(AddListing.photos, F.photo)
async def add_photo(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)

    if len(photos) >= settings.MAX_PHOTOS:
        await _save_listing(message, state, session, bot)
    else:
        await message.answer(f"✅ Rasm {len(photos)}/{settings.MAX_PHOTOS} qo'shildi. /done")


@router.message(AddListing.photos, F.text == "/done")
async def photos_done(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    await _save_listing(message, state, session, bot)


async def _save_listing(message: Message, state: FSMContext, session: AsyncSession, bot: Bot = None):
    data = await state.get_data()

    # Telefon raqamini DB dan olish (tasdiqlangan raqam)
    user = await session.get(User, message.from_user.id)
    phone = user.phone if user and user.phone else "noma'lum"

    listing = Listing(
        owner_id=message.from_user.id,
        listing_type=ListingType(data["listing_type"]),
        property_type=PropertyType(data["property_type"]),
        city=data["city"],
        district=data["district"],
        rooms=data["rooms"],
        area=data["area"],
        floor=data.get("floor"),
        total_floors=data.get("total_floors"),
        price=data["price"],
        price_currency=data.get("currency", "USD"),
        is_negotiable=data.get("is_negotiable", False),
        description_uz=data.get("description"),
        photos=data.get("photos", []),
        contact_phone=phone,
    )
    listing.status = ListingStatus.inactive  # Admin tasdiqlagunicha yashirin
    session.add(listing)
    await session.flush()
    listing_id = listing.id

    await state.clear()
    await message.answer(
        "✅ E'loningiz qabul qilindi!\n\n"
        "⏳ Admin tekshiruvidan o'tgach e'loningiz faollashadi (odatda 1-2 soat ichida).\n\n"
        f"E'lon #{listing_id}",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    # Adminlarga xabar yuborish
    if settings.ADMIN_IDS and bot:
        prop_map = {"apartment": "Kvartira", "house": "Uy", "room": "Xona", "commercial": "Tijorat"}
        type_suffix = {"sale": "sotiladi", "rent": "ijaraga beriladi", "daily": "kunlik ijaraga"}
        prop_name = prop_map.get(data['property_type'], data['property_type'])
        ltype = type_suffix.get(data['listing_type'], data['listing_type'])
        floor_str = f"{data.get('floor', '?')}/{data.get('total_floors', '?')}" if data.get("floor") else "—"
        price_str = f"{data['price']:,.0f}".replace(",", " ")
        neg = " (Kelishiladi)" if data.get("is_negotiable") else ""

        admin_text = (
            f"⚪️ <b>{prop_name} egasi raqami bilan joylandi</b>\n\n"
            f"🔘Shahar: #{data['city'].replace(' ', '')}\n"
            f"🔘Tuman: #{data['district'].replace(' ', '')}\n"
            f"🔘Xonalar: {data['rooms']}\n"
            f"🔘Qavat: {floor_str}\n"
            f"🔘Maydon: {data['area']} m²\n"
            f"{'🔘' + data.get('description', '') + chr(10) if data.get('description') else ''}"
            f"\n💸Narx: {price_str} {data.get('currency', 'USD')}{neg}\n"
            f"\n📞 {phone} ✅\n"
            f"👤 <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{listing_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{listing_id}"),
        ]])
        photos = data.get("photos", [])
        for admin_id in settings.ADMIN_IDS:
            try:
                if photos:
                    await bot.send_photo(admin_id, photos[0], caption=admin_text, reply_markup=kb, parse_mode="HTML")
                else:
                    await bot.send_message(admin_id, admin_text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass


# Bekor qilish
@router.callback_query(F.data == "cancel")
async def cancel_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(uz["cancel"])
    await callback.message.answer(uz["choose_action"])
