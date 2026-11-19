from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.main_kb import main_menu_kb
from locales.uz import texts as uz

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)
    if not user:
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        session.add(user)
        await session.commit()

    await message.answer(
        uz["welcome"],
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await message.answer(uz["choose_action"], reply_markup=main_menu_kb())
