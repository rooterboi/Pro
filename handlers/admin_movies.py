from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton as B, InlineKeyboardMarkup as M, Message

from database import queries as q
from handlers.filters import IsAdmin
from keyboards.admin_kb import HOME, edit_fields_kb
from states.states import AddMovie, DelMovie, EditMovie
from utils import autopost
from utils.cards import send_card
from utils.helpers import extract_video
from utils.tasks import spawn

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

ORDER = ["title", "code", "genre", "language", "quality", "year", "description", "poster", "video"]
PROMPTS = {
    "code": "🔑 Kino kodini yuboring (masalan: 101):",
    "genre": "🎭 Janr (masalan: Jangari, Drama) yoki «-» :",
    "language": "🌐 Til (masalan: O'zbek tilida) yoki «-» :",
    "quality": "📺 Sifat (masalan: 1080p) yoki «-» :",
    "year": "📅 Yil (masalan: 2024) yoki «-» :",
    "description": "📝 Tavsif yoki «-» :",
    "poster": "🖼 Poster rasmini yuboring (yoki «-»):",
    "video": "🎥 Endi kino videosini yuboring:",
}


async def _next(msg: Message, state: FSMContext, current: str):
    nxt = ORDER[ORDER.index(current) + 1]
    await state.set_state(getattr(AddMovie, nxt))
    await msg.answer(PROMPTS[nxt])


# ================= QO'SHISH =================
@router.callback_query(F.data == "a:addmovie")
async def add_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AddMovie.title)
    await cb.message.answer("🎬 Kino nomini yuboring:\n(/cancel — bekor qilish)")
    await cb.answer()


@router.message(AddMovie.title, F.text)
async def f_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    await _next(msg, state, "title")


@router.message(AddMovie.code, F.text)
async def f_code(msg: Message, state: FSMContext, bot_id: int):
    code = msg.text.strip()
    if " " in code or await q.code_exists(bot_id, code):
        return await msg.answer("⚠️ Kod band yoki bo'sh joy bor. Boshqa kod yuboring:")
    await state.update_data(code=code)
    await _next(msg, state, "code")


@router.message(StateFilter(AddMovie.genre, AddMovie.language, AddMovie.quality,
                            AddMovie.year, AddMovie.description), F.text)
async def f_text(msg: Message, state: FSMContext):
    cur = (await state.get_state()).split(":")[1]
    val = msg.text.strip()
    await state.update_data(**{cur: None if val == "-" else val})
    await _next(msg, state, cur)


@router.message(AddMovie.poster, F.photo | (F.text == "-"))
async def f_poster(msg: Message, state: FSMContext):
    await state.update_data(poster_file_id=msg.photo[-1].file_id if msg.photo else None)
    await _next(msg, state, "poster")


@router.message(AddMovie.video, F.video | F.document)
async def f_video(msg: Message, state: FSMContext, bot: Bot, bot_id: int):
    fid, kind = extract_video(msg)
    if not fid:
        return await msg.answer("❌ Bu video emas. Video yuboring.")
    d = await state.get_data()
    await state.clear()
    mid = await q.add_movie(
        bot_id, title=d["title"], code=d["code"], genre=d.get("genre"), language=d.get("language"),
        quality=d.get("quality"), year=d.get("year"), description=d.get("description"),
        poster_file_id=d.get("poster_file_id"), video_file_id=fid, video_kind=kind)
    await msg.answer("✅ Kino saqlandi!")
    await send_card(bot, msg.chat.id, msg.from_user.id, await q.get_movie(mid))
    # kanalga avto-post (teaser) — fonda ishlaydi, admin kutib o'tirmaydi
    spawn(autopost.post_movie(bot, bot_id, mid, notify_chat=msg.chat.id))


# ================= TAHRIRLASH =================
@router.callback_query(F.data == "a:editmovie")
async def edit_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(EditMovie.code)
    await cb.message.answer("✏️ Tahrirlanadigan kino kodini yuboring:")
    await cb.answer()


@router.message(EditMovie.code, F.text)
async def edit_code(msg: Message, state: FSMContext, bot_id: int):
    m = await q.get_movie_by_code(bot_id, msg.text.strip())
    if not m:
        return await msg.answer("❌ Bunday kod topilmadi. Qayta yuboring yoki /cancel.")
    await state.update_data(mid=m["id"])
    await state.set_state(EditMovie.field)
    await msg.answer(f"🎬 <b>{m['title']}</b>\nQaysi maydonni o'zgartiramiz?", reply_markup=edit_fields_kb())


@router.callback_query(EditMovie.field, F.data.startswith("ef:"))
async def edit_field(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":")[1]
    if field == "done":
        await state.clear()
        await cb.message.answer("✅ Tahrirlash yakunlandi.")
        return await cb.answer()
    await state.update_data(field=field)
    await state.set_state(EditMovie.value)
    hint = {"poster_file_id": "rasm", "video_file_id": "video"}.get(field, "yangi qiymat (matn)")
    await cb.message.answer(f"Yangi {hint} yuboring:")
    await cb.answer()


@router.message(EditMovie.value)
async def edit_value(msg: Message, state: FSMContext, bot: Bot, bot_id: int):
    d = await state.get_data()
    field, mid = d["field"], d["mid"]
    upd = {}
    if field == "poster_file_id":
        if not msg.photo:
            return await msg.answer("❌ Rasm yuboring.")
        upd[field] = msg.photo[-1].file_id
    elif field == "video_file_id":
        fid, kind = extract_video(msg)
        if not fid:
            return await msg.answer("❌ Video yuboring.")
        upd.update(video_file_id=fid, video_kind=kind)
    else:
        if not msg.text:
            return await msg.answer("❌ Matn yuboring.")
        val = msg.text.strip()
        if field == "code" and await q.code_exists(bot_id, val):
            return await msg.answer("⚠️ Bu kod band. Boshqa kod yuboring:")
        upd[field] = val
    await q.update_movie(mid, **upd)
    await state.set_state(EditMovie.field)
    await msg.answer("✅ Yangilandi.")
    await send_card(bot, msg.chat.id, msg.from_user.id, await q.get_movie(mid))
    await msg.answer("Yana nimani o'zgartiramiz?", reply_markup=edit_fields_kb())


# ================= O'CHIRISH =================
@router.callback_query(F.data == "a:delmovie")
async def del_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(DelMovie.code)
    await cb.message.answer("🗑 O'chiriladigan kino kodini yuboring:")
    await cb.answer()


@router.message(DelMovie.code, F.text)
async def del_code(msg: Message, state: FSMContext, bot_id: int):
    m = await q.get_movie_by_code(bot_id, msg.text.strip())
    if not m:
        return await msg.answer("❌ Topilmadi. Qayta yuboring yoki /cancel.")
    await state.clear()
    kb = M(inline_keyboard=[[B(text="✅ Ha, o'chirish", callback_data=f"dm:{m['id']}"), HOME]])
    await msg.answer(f"❓ <b>{m['title']}</b> ({m['code']}) o'chirilsinmi?", reply_markup=kb)


@router.callback_query(F.data.startswith("dm:"))
async def del_confirm(cb: CallbackQuery):
    await q.delete_movie(int(cb.data.split(":")[1]))
    await cb.message.answer("🗑 O'chirildi.")
    await cb.answer()
