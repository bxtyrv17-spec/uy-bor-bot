from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.main_kb import main_menu_kb
from locales.uz import texts as uz

router = Router()


class RegisterState(StatesGroup):
    waiting_phone = State()


def phone_request_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(
        text="📱 Raqamimni ulashish",
        request_contact=True,
    ))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    user = await session.get(User, message.from_user.id)

    if user and user.phone:
        # Allaqachon ro'yxatdan o'tgan
        await message.answer(
            uz["welcome"],
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        return

    if not user:
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        session.add(user)
        await session.flush()

    # Telefon so'rash
    await state.set_state(RegisterState.waiting_phone)
    await message.answer(
        "👋 <b>Uy Bor</b> ga xush kelibsiz!\n\n"
        "🏠 Bu platforma — <b>maklerсiz</b> uy egalaridan to'g'ridan-to'g'ri.\n\n"
        "✅ Davom etish uchun Telegram raqamingizni ulashing.\n"
        "Bu orqali siz <b>haqiqiy egasiz</b> deb tasdiqlanasiz.",
        reply_markup=phone_request_kb(),
        parse_mode="HTML",
    )


@router.message(RegisterState.waiting_phone, F.contact)
async def receive_phone(message: Message, state: FSMContext, session: AsyncSession):
    # Faqat o'z raqamini ulashishi kerak
    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Iltimos, faqat <b>o'z raqamingizni</b> ulashing!",
            parse_mode="HTML",
        )
        return

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    user = await session.get(User, message.from_user.id)
    if user:
        user.phone = phone
        user.username = message.from_user.username
        user.full_name = message.from_user.full_name

    await state.clear()
    await message.answer(
        f"✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n"
        f"📱 Raqamingiz: <code>{phone}</code>\n\n"
        "Endi e'lon qo'yganingizda bu raqam avtomatik ishlatiladi.\n"
        "Hech kim boshqa raqam yoza olmaydi — bu maklerlardan himoya! 🛡",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await message.answer(uz["choose_action"], reply_markup=main_menu_kb())
