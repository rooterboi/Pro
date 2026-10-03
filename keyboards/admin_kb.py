from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M
from aiogram.utils.keyboard import InlineKeyboardBuilder

HOME = B(text="🏠 Admin panel", callback_data="a:home")

FIELDS = [("title", "Nomi"), ("code", "Kodi"), ("genre", "Janr"), ("language", "Til"),
          ("quality", "Sifat"), ("year", "Yil"), ("description", "Tavsif"),
          ("poster_file_id", "Poster"), ("video_file_id", "Video")]


def panel_kb(is_parent: bool) -> M:
    rows = [
        [B(text="🎬 Kino qo'shish", callback_data="a:addmovie")],
        [B(text="✏️ Tahrirlash", callback_data="a:editmovie"), B(text="🗑 O'chirish", callback_data="a:delmovie")],
        [B(text="📺 Seriallar", callback_data="a:series")],
        [B(text="📢 Avto-post kanal", callback_data="a:autopost"), B(text="🔒 Majburiy obuna", callback_data="a:fsub")],
        [B(text="📊 Statistika", callback_data="a:stats"), B(text="📨 Rassilka", callback_data="a:bcast")],
    ]
    if is_parent:
        rows.append([B(text="⚙️ Sozlamalar / Sub-botlar", callback_data="a:settings")])
    return M(inline_keyboard=rows)


def series_menu() -> M:
    return M(inline_keyboard=[
        [B(text="➕ Serial yaratish", callback_data="a:newseries")],
        [B(text="🎞 Seriya qo'shish", callback_data="a:addep")],
        [B(text="🗑 Serial o'chirish", callback_data="a:delseries")],
        [HOME]])


def edit_fields_kb() -> M:
    b = InlineKeyboardBuilder()
    for f, label in FIELDS:
        b.button(text=label, callback_data=f"ef:{f}")
    b.adjust(3)
    b.row(B(text="✅ Tugatish", callback_data="ef:done"))
    return b.as_markup()


def autopost_kb(on: bool, teaser: bool, has_ch: bool) -> M:
    rows = [
        [B(text="📍 Kanalni belgilash", callback_data="ap:set")],
        [B(text=f"Avto-post: {'✅ YOQIQ' if on else '⛔ O‘CHIQ'}", callback_data="ap:toggle")],
        [B(text=f"Teaser (30s): {'✅ YOQIQ' if teaser else '⛔ O‘CHIQ'}", callback_data="ap:teaser")],
    ]
    if has_ch:
        rows.append([B(text="🗑 Kanalni olib tashlash", callback_data="ap:clear")])
    rows.append([HOME])
    return M(inline_keyboard=rows)


def fsub_kb(channels) -> M:
    rows = [[B(text=f"🗑 {c['title']}", callback_data=f"fs:del:{c['id']}")] for c in channels]
    rows.append([B(text="➕ Kanal qo'shish", callback_data="fs:add")])
    rows.append([HOME])
    return M(inline_keyboard=rows)


def settings_kb() -> M:
    return M(inline_keyboard=[
        [B(text="✏️ Yashirin buyruq nomi", callback_data="st:cmd")],
        [B(text="🔑 PIN-kodni o'zgartirish", callback_data="st:pin")],
        [B(text="🤖 Sub-botlar ro'yxati", callback_data="st:bots")],
        [HOME]])
