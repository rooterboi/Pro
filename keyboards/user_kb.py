from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder

BTN_SEARCH = "🔎 Qidirish"
BTN_TOP = "🔥 Top"
BTN_GENRES = "🎭 Janrlar"
BTN_YEARS = "📅 Yillar"
BTN_FAV = "⭐ Saqlanganlar"
BTN_NEW = "🆕 Yangilar"
BTN_ADMIN = "🛠 Admin panel"


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_SEARCH), KeyboardButton(text=BTN_TOP)],
        [KeyboardButton(text=BTN_GENRES), KeyboardButton(text=BTN_YEARS)],
        [KeyboardButton(text=BTN_FAV), KeyboardButton(text=BTN_NEW)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def movie_kb(mid: int, faved: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📥 Yuklab olish", callback_data=f"dl:{mid}"))
    b.row(InlineKeyboardButton(
        text="❌ Saqlanganlardan olib tashlash" if faved else "⭐ Saqlash", callback_data=f"fav:{mid}"))
    b.row(*[InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rt:{mid}:{i}") for i in range(1, 6)])
    return b.as_markup()


def series_kb(sid: int, seasons) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in seasons:
        b.button(text=f"{s['season']}-sezon ({s['c']} seriya)", callback_data=f"ss:{sid}:{s['season']}")
    b.adjust(1)
    return b.as_markup()


def episodes_kb(sid: int, eps) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for e in eps:
        b.button(text=f"▶️ {e['episode']}-seriya", callback_data=f"ep:{e['id']}")
    b.adjust(3)
    b.row(InlineKeyboardButton(text="⬅️ Sezonlar", callback_data=f"s:{sid}"))
    return b.as_markup()


def items_kb(items) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for label, cb in items:
        b.button(text=label[:60], callback_data=cb)
    b.adjust(1)
    return b.as_markup()


def sub_kb(missing) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in missing:
        if c["link"]:
            b.row(InlineKeyboardButton(text=f"📢 {c['title']}", url=c["link"]))
    b.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="chk"))
    return b.as_markup()
