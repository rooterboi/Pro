from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.user_kb import (BTN_FAV, BTN_GENRES, BTN_NEW, BTN_SEARCH, BTN_TOP, BTN_YEARS,
                               episodes_kb, items_kb, main_menu, movie_kb)
from utils.cards import send_card, send_series_card, send_video

router = Router()

WELCOME = ("🎬 <b>Kino botga xush kelibsiz!</b>\n\nKino yoki serial <b>kodini</b>, <b>nomini</b>, "
           "<b>janrini</b> yoki <b>yilini</b> yuboring.")


async def open_code(msg: Message, bot: Bot, code: str) -> bool:
    m = await q.get_movie_by_code(bot.id, code)
    if m:
        if m["series_id"]:
            await send_video(bot, msg.chat.id, m)
        else:
            await send_card(bot, msg.chat.id, msg.from_user.id, m)
        return True
    s = await q.get_series_by_code(bot.id, code)
    if s:
        await send_series_card(bot, msg.chat.id, s)
        return True
    return False


async def reply_results(msg: Message, movies, series, title="Natijalar"):
    if not movies and not series:
        return await msg.answer("😔 Hech narsa topilmadi. Boshqa so'z yoki kod bilan urinib ko'ring.")
    items = [(f"🎬 {m['title']}" + (f" ({m['year']})" if m["year"] else ""), f"m:{m['id']}") for m in movies]
    items += [(f"📺 {s['title']}" + (f" ({s['year']})" if s["year"] else ""), f"s:{s['id']}") for s in series]
    await msg.answer(f"🔎 <b>{title}:</b>", reply_markup=items_kb(items))


@router.message(CommandStart())
async def start(msg: Message, command: CommandObject, bot: Bot, state: FSMContext, is_admin: bool = False):
    await state.clear()
    if command.args and await open_code(msg, bot, command.args.strip()):
        return
    await msg.answer(WELCOME, reply_markup=main_menu(is_admin))


@router.message(F.text == BTN_SEARCH)
async def b_search(msg: Message):
    await msg.answer("🔎 Kino nomi, kodi, janri yoki yilini yozing:")


@router.message(F.text == BTN_TOP)
async def b_top(msg: Message, bot_id: int):
    await reply_results(msg, await q.top_movies(bot_id), [], "🔥 Eng ko'p ko'rilganlar")


@router.message(F.text == BTN_NEW)
async def b_new(msg: Message, bot_id: int):
    await reply_results(msg, await q.new_movies(bot_id), await q.new_series(bot_id), "🆕 Yangi qo'shilganlar")


@router.message(F.text == BTN_FAV)
async def b_fav(msg: Message, bot_id: int):
    favs = await q.list_favs(bot_id, msg.from_user.id)
    if not favs:
        return await msg.answer("⭐ Saqlanganlar bo'sh. Kino kartasidagi «⭐ Saqlash» tugmasini bosing.")
    await reply_results(msg, favs, [], "⭐ Saqlanganlar")


@router.message(F.text == BTN_GENRES)
async def b_genres(msg: Message, bot_id: int):
    gs = await q.genres(bot_id)
    if not gs:
        return await msg.answer("Janrlar hali yo'q.")
    await msg.answer("🎭 Janrni tanlang:", reply_markup=items_kb([(g, f"gn:{i}") for i, g in enumerate(gs)]))


@router.message(F.text == BTN_YEARS)
async def b_years(msg: Message, bot_id: int):
    ys = await q.years(bot_id)
    if not ys:
        return await msg.answer("Yillar hali yo'q.")
    await msg.answer("📅 Yilni tanlang:", reply_markup=items_kb([(y, f"yr:{y}") for y in ys]))


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def universal(msg: Message, bot: Bot, bot_id: int):
    text = msg.text.strip()
    if await open_code(msg, bot, text):
        return
    movies, series = await q.search(bot_id, text)
    await reply_results(msg, movies, series)


# ---------- callbacklar ----------
@router.callback_query(F.data.startswith("gn:"))
async def c_genre(cb: CallbackQuery, bot_id: int):
    gs = await q.genres(bot_id)
    i = int(cb.data.split(":")[1])
    if i >= len(gs):
        return await cb.answer("Janr topilmadi", show_alert=True)
    movies, series = await q.search(bot_id, gs[i])
    await cb.answer()
    await reply_results(cb.message, movies, series, f"🎭 {gs[i]}")


@router.callback_query(F.data.startswith("yr:"))
async def c_year(cb: CallbackQuery, bot_id: int):
    movies, series = await q.by_year(bot_id, cb.data.split(":")[1])
    await cb.answer()
    await reply_results(cb.message, movies, series, f"📅 {cb.data.split(':')[1]}")


@router.callback_query(F.data.startswith("m:"))
async def c_movie(cb: CallbackQuery, bot: Bot):
    m = await q.get_movie(int(cb.data.split(":")[1]))
    await cb.answer()
    if m:
        await send_card(bot, cb.message.chat.id, cb.from_user.id, m)


@router.callback_query(F.data.startswith("s:"))
async def c_series(cb: CallbackQuery, bot: Bot):
    s = await q.get_series(int(cb.data.split(":")[1]))
    await cb.answer()
    if s:
        await send_series_card(bot, cb.message.chat.id, s)


@router.callback_query(F.data.startswith("ss:"))
async def c_season(cb: CallbackQuery):
    _, sid, season = cb.data.split(":")
    eps = await q.episodes(int(sid), int(season))
    await cb.answer()
    await cb.message.answer(f"📺 <b>{season}-sezon</b> — seriyani tanlang:", reply_markup=episodes_kb(int(sid), eps))


@router.callback_query(F.data.startswith(("dl:", "ep:")))
async def c_download(cb: CallbackQuery, bot: Bot):
    m = await q.get_movie(int(cb.data.split(":")[1]))
    if not m:
        return await cb.answer("Topilmadi", show_alert=True)
    await cb.answer("📥 Yuborilmoqda...")
    await send_video(bot, cb.message.chat.id, m)


@router.callback_query(F.data.startswith("fav:"))
async def c_fav(cb: CallbackQuery, bot_id: int):
    mid = int(cb.data.split(":")[1])
    now = await q.toggle_fav(bot_id, cb.from_user.id, mid)
    try:
        await cb.message.edit_reply_markup(reply_markup=movie_kb(mid, now))
    except Exception:
        pass
    await cb.answer("⭐ Saqlandi" if now else "Olib tashlandi")


@router.callback_query(F.data.startswith("rt:"))
async def c_rate(cb: CallbackQuery, bot_id: int):
    _, mid, score = cb.data.split(":")
    await q.set_rating(bot_id, cb.from_user.id, int(mid), int(score))
    avg, cnt = await q.get_rating(int(mid))
    await cb.answer(f"Rahmat! Baho: {score}⭐ (o'rtacha {avg:.1f}, {cnt} ovoz)", show_alert=True)
