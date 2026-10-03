"""Yangi kino yuklanganda kanalga avtomatik post (teaser bilan)."""
import logging
import os
import uuid

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from config import TEASER_SECONDS, TMP_DIR
from database import queries as q
from utils.ffmpeg_utils import ffmpeg_available, make_teaser
from utils.helpers import esc

log = logging.getLogger(__name__)


async def post_movie(bot: Bot, bot_id: int, movie_id: int, notify_chat: int | None = None):
    if await q.get_setting(bot_id, "autopost_on", "0") != "1":
        return
    channel = await q.get_setting(bot_id, "autopost_channel", "")
    if not channel:
        return
    m = await q.get_movie(movie_id)
    if not m:
        return
    me = await bot.me()
    chat_id = int(channel)
    caption = (
        f"🎬 <b>{esc(m['title'])}</b>\n\n"
        f"🔑 Kino kodi: <code>{esc(m['code'])}</code>\n"
        f"🎭 {esc(m['genre'])} | 🌐 {esc(m['language'])} | 📺 {esc(m['quality'])}\n\n"
        f"📥 To'liq ko'rish: @{me.username}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶️ Kinoni ko'rish", url=f"https://t.me/{me.username}?start={m['code']}")
    ]])

    src = dst = None
    status = ""
    try:
        if await q.get_setting(bot_id, "teaser_on", "1") == "1" and ffmpeg_available():
            os.makedirs(TMP_DIR, exist_ok=True)
            uid = uuid.uuid4().hex
            src, dst = f"{TMP_DIR}/{uid}.src", f"{TMP_DIR}/{uid}.mp4"
            await bot.download(m["video_file_id"], destination=src)  # cloud API: <=20MB
            await make_teaser(src, dst, TEASER_SECONDS)
            await bot.send_video(chat_id, FSInputFile(dst), caption=caption,
                                 reply_markup=kb, supports_streaming=True)
            status = "✅ Teaser bilan kanalga joylandi."
        else:
            raise RuntimeError("teaser o'chiq yoki ffmpeg topilmadi")
    except Exception as e:
        log.warning("Teaser ishlamadi (%s) — poster bilan post qilinadi", e)
        try:
            if m["poster_file_id"]:
                await bot.send_photo(chat_id, m["poster_file_id"], caption=caption, reply_markup=kb)
            else:
                await bot.send_message(chat_id, caption, reply_markup=kb)
            status = f"⚠️ Teaser yaratilmadi ({str(e)[:80]}). Poster bilan joylandi."
        except Exception as e2:
            status = f"❌ Kanalga yuborib bo'lmadi: {e2}"
    finally:
        for p in (src, dst):
            if p and os.path.exists(p):
                os.remove(p)
    if notify_chat:
        try:
            await bot.send_message(notify_chat, f"📢 Avto-post: {status}")
        except Exception:
            pass
