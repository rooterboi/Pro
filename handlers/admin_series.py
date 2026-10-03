from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import queries as q
from handlers.filters import IsAdmin
from keyboards.admin_kb import HOME, series_menu
from states.states import AddEpisode, AddSeries
from utils.cards import send_series_card
from utils.helpers import extract_video

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

S_ORDER = ["title", "code", "genre", "year", "description", "poster"]
S_PROMPTS = {
    "code": "🔑 Serial kodini yuboring:",
    "genre": "🎭 Janr yoki «-» :",
    "year": "📅 Yil yoki «-» :",
    "description": "📝 Tavsif yoki «-» :",
    "poster": "🖼 Serial posterini yuboring (yoki «-»):",
}


@router.callback_query(F.data == "a:series")
async def menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("📺 <b>Seriallar bo'limi</b>", reply_markup=series_menu())
    await cb.answer()


# ---------- serial yaratish ----------
@router.callback_query(F.data == "a:newseries")
async def new_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddSeries.title)
    await cb.message.answer("📺 Serial nomini yuboring:\n(/cancel)")
    await cb.answer()


async def _nxt(msg, state, cur):
    n = S_ORDER[S_ORDER.index(cur) + 1]
    await state.set_state(getattr(AddSeries, n))
    await msg.answer(S_PROMPTS[n])


@router.message(AddSeries.title, F.text)
async def s_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    await _nxt(msg, state, "title")


@router.message(AddSeries.code, F.text)
async def s_code(msg: Message, state: FSMContext, bot_id: int):
    code = msg.text.strip()
    if " " in code or await q.code_exists(bot_id, code):
        return await msg.answer("⚠️ Kod band. Boshqa kod yuboring:")
    await state.update_data(code=code)
    await _nxt(msg, state, "code")


@router.message(StateFilter(AddSeries.genre, AddSeries.year, AddSeries.description), F.text)
async def s_text(msg: Message, state: FSMContext):
    cur = (await state.get_state()).split(":")[1]
    v = msg.text.strip()
    await state.update_data(**{cur: None if v == "-" else v})
    await _nxt(msg, state, cur)


@router.message(AddSeries.poster, F.photo | (F.text == "-"))
async def s_poster(msg: Message, state: FSMContext, bot: Bot, bot_id: int):
    d = await state.get_data()
    await state.clear()
    sid = await q.add_series(bot_id, d["code"], d["title"], d.get("genre"), d.get("year"),
                             d.get("description"), msg.photo[-1].file_id if msg.photo else None)
    await msg.answer("✅ Serial yaratildi! Endi «🎞 Seriya qo'shish» orqali seriyalarni biriktiring.")
    await send_series_card(bot, msg.chat.id, await q.get_series(sid))


# ---------- seriya qo'shish (sezon -> seriyalar tartib bilan) ----------
@router.callback_query(F.data == "a:addep")
async def ep_pick(cb: CallbackQuery, state: FSMContext, bot_id: int):
    await state.clear()
    items = await q.list_series(bot_id)
    if not items:
        await cb.message.answer("Avval serial yarating.")
        return await cb.answer()
    b = InlineKeyboardBuilder()
    for s in items:
        b.button(text=f"📺 {s['title']}", callback_data=f"ae:{s['id']}")
    b.adjust(1)
    await cb.message.answer("Qaysi serialga seriya qo'shamiz?", reply_markup=b.as_markup())
    await cb.answer()


@router.callback_query(F.data.startswith("ae:"))
async def ep_series(cb: CallbackQuery, state: FSMContext):
    await state.update_data(sid=int(cb.data.split(":")[1]))
    await state.set_state(AddEpisode.season)
    await cb.message.answer("Sezon raqamini yuboring (masalan: 1):")
    await cb.answer()


async def _ask_code(msg: Message, state: FSMContext):
    d = await state.get_data()
    n = await q.next_episode(d["sid"], d["season"])
    await state.update_data(episode=n)
    await state.set_state(AddEpisode.code)
    await msg.answer(f"🎞 <b>{d['season']}-sezon, {n}-seriya</b>\nShu seriya uchun KOD yuboring (tugatish: /done):")


@router.message(AddEpisode.season, F.text)
async def ep_season(msg: Message, state: FSMContext):
    if not msg.text.strip().isdigit() or int(msg.text) < 1:
        return await msg.answer("❌ Raqam yuboring (1, 2, 3...).")
    await state.update_data(season=int(msg.text))
    await _ask_code(msg, state)


@router.message(Command("done"), StateFilter(AddEpisode.code))
async def ep_done(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("✅ Seriyalar qo'shish yakunlandi.", reply_markup=None)


@router.message(AddEpisode.code, F.text)
async def ep_code(msg: Message, state: FSMContext, bot_id: int):
    code = msg.text.strip()
    if " " in code or await q.code_exists(bot_id, code):
        return await msg.answer("⚠️ Kod band. Boshqa kod yuboring:")
    await state.update_data(code=code)
    await state.set_state(AddEpisode.video)
    await msg.answer("🎥 Seriya videosini yuboring:")


@router.message(AddEpisode.video, F.video | F.document)
async def ep_video(msg: Message, state: FSMContext, bot_id: int):
    fid, kind = extract_video(msg)
    if not fid:
        return await msg.answer("❌ Bu video emas.")
    d = await state.get_data()
    s = await q.get_series(d["sid"])
    await q.add_movie(
        bot_id, code=d["code"], title=f"{s['title']} — {d['season']}-sezon {d['episode']}-seriya",
        genre=s["genre"], year=s["year"], poster_file_id=s["poster_file_id"],
        video_file_id=fid, video_kind=kind, series_id=s["id"], season=d["season"], episode=d["episode"])
    await msg.answer(f"✅ {d['season']}-sezon {d['episode']}-seriya saqlandi.")
    await _ask_code(msg, state)  # keyingi seriya, tartib bilan


# ---------- serial o'chirish ----------
@router.callback_query(F.data == "a:delseries")
async def del_pick(cb: CallbackQuery, bot_id: int):
    items = await q.list_series(bot_id)
    if not items:
        await cb.message.answer("Seriallar yo'q.")
        return await cb.answer()
    b = InlineKeyboardBuilder()
    for s in items:
        b.button(text=f"🗑 {s['title']}", callback_data=f"ds:{s['id']}")
    b.adjust(1)
    b.row(HOME)
    await cb.message.answer("Qaysi serialni o'chiramiz? (barcha seriyalari bilan)", reply_markup=b.as_markup())
    await cb.answer()


@router.callback_query(F.data.startswith("ds:"))
async def del_do(cb: CallbackQuery):
    await q.delete_series(int(cb.data.split(":")[1]))
    await cb.message.answer("🗑 Serial o'chirildi.")
    await cb.answer()
