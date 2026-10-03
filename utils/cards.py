from aiogram import Bot

from database import queries as q
from keyboards.user_kb import movie_kb, series_kb
from utils.helpers import esc


async def movie_caption(m) -> str:
    avg, cnt = await q.get_rating(m["id"])
    desc = (m["description"] or "")[:550]
    return (
        f"🎬 <b>{esc(m['title'])}</b>\n\n"
        f"🔑 Kod: <code>{esc(m['code'])}</code>\n"
        f"🎭 Janr: {esc(m['genre'])}\n"
        f"🌐 Til: {esc(m['language'])}\n"
        f"📺 Sifat: {esc(m['quality'])}\n"
        f"📅 Yil: {esc(m['year'])}\n"
        f"⭐ Reyting: {avg:.1f} ({cnt} ovoz)\n"
        f"👁 Ko'rishlar: {m['views']}\n\n"
        f"📝 {esc(desc)}"
    )


async def send_card(bot: Bot, chat_id: int, user_id: int, m):
    faved = await q.is_fav(bot.id, user_id, m["id"])
    kb = movie_kb(m["id"], faved)
    cap = await movie_caption(m)
    if m["poster_file_id"]:
        await bot.send_photo(chat_id, m["poster_file_id"], caption=cap, reply_markup=kb)
    else:
        await bot.send_message(chat_id, cap, reply_markup=kb)


async def send_series_card(bot: Bot, chat_id: int, s):
    seasons = await q.seasons(s["id"])
    cap = (
        f"📺 <b>{esc(s['title'])}</b>\n\n"
        f"🔑 Kod: <code>{esc(s['code'])}</code>\n"
        f"🎭 Janr: {esc(s['genre'])}\n📅 Yil: {esc(s['year'])}\n\n"
        f"📝 {esc((s['description'] or '')[:600])}\n\n"
        f"{'Sezonni tanlang 👇' if seasons else 'Hozircha seriyalar yoʻq.'}"
    )
    kb = series_kb(s["id"], seasons)
    if s["poster_file_id"]:
        await bot.send_photo(chat_id, s["poster_file_id"], caption=cap, reply_markup=kb)
    else:
        await bot.send_message(chat_id, cap, reply_markup=kb)


async def send_video(bot: Bot, chat_id: int, m):
    me = await bot.me()
    title = esc(m["title"])
    cap = f"🎬 <b>{title}</b>\n🔑 Kod: <code>{esc(m['code'])}</code>\n\n🤖 @{me.username}"
    if m["video_kind"] == "document":
        await bot.send_document(chat_id, m["video_file_id"], caption=cap)
    else:
        await bot.send_video(chat_id, m["video_file_id"], caption=cap)
    await q.inc_views(m["id"])
