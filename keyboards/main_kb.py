from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from locales.uz import texts as uz


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=uz["btn_search"]),
        KeyboardButton(text=uz["btn_add_listing"]),
    )
    builder.row(
        KeyboardButton(text=uz["btn_my_listings"]),
        KeyboardButton(text=uz["btn_settings"]),
    )
    return builder.as_markup(resize_keyboard=True)


def listing_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=uz["btn_sale"], callback_data="ltype:sale"),
        InlineKeyboardButton(text=uz["btn_rent"], callback_data="ltype:rent"),
    )
    builder.row(
        InlineKeyboardButton(text=uz["btn_daily"], callback_data="ltype:daily"),
    )
    builder.row(
        InlineKeyboardButton(text=uz["btn_cancel"], callback_data="cancel"),
    )
    return builder.as_markup()


def property_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=uz["btn_apartment"], callback_data="ptype:apartment"),
        InlineKeyboardButton(text=uz["btn_house"], callback_data="ptype:house"),
    )
    builder.row(
        InlineKeyboardButton(text=uz["btn_room"], callback_data="ptype:room"),
        InlineKeyboardButton(text=uz["btn_commercial"], callback_data="ptype:commercial"),
    )
    builder.row(
        InlineKeyboardButton(text=uz["btn_cancel"], callback_data="cancel"),
    )
    return builder.as_markup()


def cities_kb(for_search: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    cities = uz["cities"]
    prefix = "scity" if for_search else "city"

    for i in range(0, len(cities) - 1, 2):
        row = [InlineKeyboardButton(text=cities[i], callback_data=f"{prefix}:{cities[i]}")]
        if i + 1 < len(cities) - 1:
            row.append(InlineKeyboardButton(text=cities[i+1], callback_data=f"{prefix}:{cities[i+1]}"))
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(text=cities[-1], callback_data=f"{prefix}:other"),
    )
    builder.row(
        InlineKeyboardButton(text=uz["btn_cancel"], callback_data="cancel"),
    )
    return builder.as_markup()


def yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=uz["btn_yes"], callback_data=f"{prefix}:yes"),
        InlineKeyboardButton(text=uz["btn_no"], callback_data=f"{prefix}:no"),
    )
    return builder.as_markup()


def currency_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=uz["btn_usd"], callback_data="currency:USD"),
        InlineKeyboardButton(text=uz["btn_uzs"], callback_data="currency:UZS"),
    )
    return builder.as_markup()


def contact_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=uz["btn_share_contact"], request_contact=True))
    builder.row(KeyboardButton(text=uz["btn_cancel"]))
    return builder.as_markup(resize_keyboard=True)


def listing_nav_kb(listing_id: int, index: int, total: int, show_contact: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton(text=uz["btn_prev"], callback_data=f"nav:{index-1}"))
    if index < total - 1:
        nav.append(InlineKeyboardButton(text=uz["btn_next"], callback_data=f"nav:{index+1}"))
    if nav:
        builder.row(*nav)
    if show_contact:
        builder.row(
            InlineKeyboardButton(text=uz["btn_contact"], callback_data=f"contact:{listing_id}"),
        )
    builder.row(
        InlineKeyboardButton(text=uz["btn_back"], callback_data="back_to_search"),
    )
    return builder.as_markup()


def my_listing_kb(listing_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = uz["btn_deactivate"] if is_active else uz["btn_activate"]
    toggle_cb = f"toggle:{listing_id}"
    builder.row(
        InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb),
        InlineKeyboardButton(text=uz["btn_delete_listing"], callback_data=f"delete:{listing_id}"),
    )
    builder.row(
        InlineKeyboardButton(text=uz["btn_back"], callback_data="my_listings"),
    )
    return builder.as_markup()


remove_kb = ReplyKeyboardRemove()
