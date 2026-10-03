import asyncio
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DEFAULT_ROOTER_CMD, DEFAULT_ROOTER_PIN
from database import queries as q
from handlers.filters import IsAdmin, IsParent
from keyboards.admin_kb import HOME, autopost_kb, fsub_kb, panel_kb, settings_kb
from keyboards.user_kb import BTN_ADMIN
from states.states import AutoChannel, Broadcast, FSub, SettingsState
from utils.helpers import chat_link, esc, resolve_chat
from utils.multibot import BotManager
from utils.tasks import spawn

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

RESERVED = {"start", "admin", "cancel", "done", "help"}


# ---------- panel ----------
@router.message(Command("admin"))
@router.message(F.text == BTN_ADMIN)
async def panel(msg: Message, state: FSMContext, is_parent: bool):
    await state.clear()
    await msg.answer("🛠 <b>Admin panel</b>", reply_markup=panel_kb(is_parent))


@router.callback_query(F.data == "a:home")
async def home(cb: CallbackQuery, state: FSMContext, is_parent: bool):
    await state.clear()
    await cb.message.answer("🛠 <b>Admin panel</b>", reply_markup=panel_kb(is_parent))
    await cb.answer()


# ---------- statistika ----------
@router.callback_query(F.data == "a:stats")
async def stats(cb: CallbackQuery, bot_id: int, is_parent: bool):
    s = await q.stats(bot_id)
    text = (f"📊 <b>Statistika</b>\n\n👥 Foydalanuvchilar: {s['users']}\n🆕 24 soatda: {s['today']}\n"
            f"🚫 Bloklaganlar: {s['blocked']}\n🎬 Kinolar: {s['movies']}\n📺 Seriallar: {s['series']}\n"
            f"🎞 Seriyalar: {s['eps']}\n👁 Jami ko'rishlar: {s['views']}")
    if is_parent:
        text += f"\n🤖 Sub-botlar: {len(await q.get_bots(children_only=True))}"
    await cb.message.answer(text)
    await cb.answer()


# ---------- rassilka ----------
@router.callback_query(F.data == "a:bcast")
async def bcast_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.content)
    await cb.message.answer("📨 Barcha foydalanuvchilarga yuboriladigan xabarni yuboring "
                            "(matn/rasm/video — istalgan).\n/cancel — bekor qilish")
    await cb.answer()


@router.message(Broadcast.content)
async def bcast_go(msg: Message, state: FSMContext, bot, bot_id: int):
    await state.clear()
    await msg.answer("📨 Yuborish boshlandi, tugagach xabar beraman.")
    spawn(_broadcast(bot, bot_id, msg.chat.id, msg.message_id))


async def _broadcast(bot, bot_id, from_chat, mid):
    ok = fail = 0
    for uid in await q.user_ids(bot_id):
        try:
            try:
                await bot.copy_message(uid, from_chat, mid)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                await bot.copy_message(uid, from_chat, mid)
            ok += 1
        except TelegramForbiddenError:
            await q.mark_blocked(bot_id, uid)
            fail += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.04)
    await bot.send_message(from_chat, f"✅ Rassilka tugadi.\nYetkazildi: {ok}\nYetkazilmadi: {fail}")


# ---------- majburiy obuna ----------
async def _fsub_text(bot_id):
    chs = await q.get_channels(bot_id)
    body = "\n".join(f"• {esc(c['title'])}" for c in chs) or "Kanallar yo'q."
    return f"🔒 <b>Majburiy obuna kanallari</b>\n\n{body}\n\n⚠️ Bot har bir kanalda ADMIN bo'lishi kerak.", chs


@router.callback_query(F.data == "a:fsub")
async def fsub_menu(cb: CallbackQuery, bot_id: int):
    text, chs = await _fsub_text(bot_id)
    await cb.message.answer(text, reply_markup=fsub_kb(chs))
    await cb.answer()


@router.callback_query(F.data == "fs:add")
async def fsub_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(FSub.channel)
    await cb.message.answer("Kanaldan biror xabarni forward qiling yoki @username / -100... ID yuboring.\n/cancel")
    await cb.answer()


@router.message(FSub.channel)
async def fsub_save(msg: Message, state: FSMContext, bot, bot_id: int):
    try:
        chat = await resolve_chat(bot, msg)
        if chat is None:
            raise ValueError
    except Exception:
        return await msg.answer("❌ Kanal topilmadi. Bot kanalga qo'shilganini tekshiring va qayta yuboring.")
    await q.add_channel(bot_id, chat.id, chat.title or str(chat.id), await chat_link(bot, chat))
    await state.clear()
    text, chs = await _fsub_text(bot_id)
    await msg.answer("✅ Qo'shildi.\n\n" + text, reply_markup=fsub_kb(chs))


@router.callback_query(F.data.startswith("fs:del:"))
async def fsub_del(cb: CallbackQuery, bot_id: int):
    await q.del_channel(bot_id, int(cb.data.split(":")[2]))
    text, chs = await _fsub_text(bot_id)
    await cb.message.answer("🗑 O'chirildi.\n\n" + text, reply_markup=fsub_kb(chs))
    await cb.answer()


# ---------- avto-post kanal ----------
async def _ap_show(target: Message, bot_id: int):
    ch = await q.get_setting(bot_id, "autopost_channel", "")
    on = await q.get_setting(bot_id, "autopost_on", "0") == "1"
    teaser = await q.get_setting(bot_id, "teaser_on", "1") == "1"
    title = ch or "belgilanmagan"
    await target.answer(
        f"📢 <b>Avto-post</b>\n\nKanal: <code>{esc(title)}</code>\n"
        f"Yangi kino yuklanganda kanalga 30 soniyalik teaser + kod + nom + bot havolasi bilan post tashlanadi.\n"
        f"⚠️ Bot kanalda admin bo'lishi shart.", reply_markup=autopost_kb(on, teaser, bool(ch)))


@router.callback_query(F.data == "a:autopost")
async def ap_menu(cb: CallbackQuery, bot_id: int):
    await _ap_show(cb.message, bot_id)
    await cb.answer()


@router.callback_query(F.data == "ap:set")
async def ap_set(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AutoChannel.channel)
    await cb.message.answer("Kanaldan xabar forward qiling yoki @username / -100... ID yuboring.\n/cancel")
    await cb.answer()


@router.message(AutoChannel.channel)
async def ap_save(msg: Message, state: FSMContext, bot, bot_id: int):
    try:
        chat = await resolve_chat(bot, msg)
        if chat is None:
            raise ValueError
        me = await bot.get_chat_member(chat.id, bot.id)
        if me.status not in ("administrator", "creator"):
            return await msg.answer("❌ Bot bu kanalda admin emas. Avval admin qiling, so'ng qayta yuboring.")
    except Exception:
        return await msg.answer("❌ Kanal topilmadi yoki bot unda yo'q. Qayta yuboring.")
    await q.set_setting(bot_id, "autopost_channel", chat.id)
    await q.set_setting(bot_id, "autopost_on", "1")
    await state.clear()
    await msg.answer(f"✅ Kanal belgilandi: {esc(chat.title)}")
    await _ap_show(msg, bot_id)


@router.callback_query(F.data.in_({"ap:toggle", "ap:teaser", "ap:clear"}))
async def ap_toggle(cb: CallbackQuery, bot_id: int):
    key = {"ap:toggle": "autopost_on", "ap:teaser": "teaser_on"}.get(cb.data)
    if cb.data == "ap:clear":
        await q.set_setting(bot_id, "autopost_channel", "")
        await q.set_setting(bot_id, "autopost_on", "0")
    else:
        default = "1" if key == "teaser_on" else "0"
        cur = await q.get_setting(bot_id, key, default)
        await q.set_setting(bot_id, key, "0" if cur == "1" else "1")
    await _ap_show(cb.message, bot_id)
    await cb.answer("Saqlandi")


# ---------- sozlamalar (faqat Parent) ----------
sp = Router()
sp.message.filter(IsAdmin(), IsParent())
sp.callback_query.filter(IsAdmin(), IsParent())


@sp.callback_query(F.data == "a:settings")
async def settings(cb: CallbackQuery, bot_id: int):
    cmd = await q.get_setting(bot_id, "rooter_cmd", DEFAULT_ROOTER_CMD)
    pin = await q.get_setting(bot_id, "rooter_pin", DEFAULT_ROOTER_PIN)
    await cb.message.answer(f"⚙️ <b>Sozlamalar</b>\n\nYashirin buyruq: <code>/{esc(cmd)}</code>\n"
                            f"PIN-kod: <code>{esc(pin)}</code>", reply_markup=settings_kb())
    await cb.answer()


@sp.callback_query(F.data == "st:cmd")
async def st_cmd(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.cmd)
    await cb.message.answer("Yangi buyruq nomini yuboring (slashsiz, lotin harf/raqam/_, 3-32 belgi). Masalan: <code>newbot</code>")
    await cb.answer()


@sp.message(SettingsState.cmd, F.text)
async def st_cmd_save(msg: Message, state: FSMContext, bot_id: int):
    cmd = msg.text.strip().lstrip("/").lower()
    if not re.fullmatch(r"[a-z0-9_]{3,32}", cmd) or cmd in RESERVED:
        return await msg.answer("❌ Noto'g'ri yoki band nom. Qayta yuboring.")
    await q.set_setting(bot_id, "rooter_cmd", cmd)
    await state.clear()
    await msg.answer(f"✅ Yashirin buyruq endi: <code>/{cmd}</code>")


@sp.callback_query(F.data == "st:pin")
async def st_pin(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.pin)
    await cb.message.answer("Yangi PIN-kodni yuboring (faqat raqam, 4-12 ta):")
    await cb.answer()


@sp.message(SettingsState.pin, F.text)
async def st_pin_save(msg: Message, state: FSMContext, bot_id: int):
    pin = msg.text.strip()
    try:
        await msg.delete()
    except Exception:
        pass
    if not (pin.isdigit() and 4 <= len(pin) <= 12):
        return await msg.answer("❌ PIN 4-12 ta raqamdan iborat bo'lsin.")
    await q.set_setting(bot_id, "rooter_pin", pin)
    await state.clear()
    await msg.answer("✅ PIN-kod yangilandi.")


@sp.callback_query(F.data == "st:bots")
async def st_bots(cb: CallbackQuery):
    bots = await q.get_bots(children_only=True)
    if not bots:
        await cb.message.answer("🤖 Sub-botlar yo'q.")
        return await cb.answer()
    b = InlineKeyboardBuilder()
    lines = []
    for r in bots:
        st = "🟢" if r["active"] else "🔴"
        lines.append(f"{st} @{r['username']} — egasi: <code>{r['owner_id']}</code>")
        b.button(text=f"🗑 @{r['username']}", callback_data=f"sb:del:{r['bot_id']}")
    b.adjust(1)
    b.row(HOME)
    await cb.message.answer("🤖 <b>Sub-botlar</b>\n\n" + "\n".join(lines), reply_markup=b.as_markup())
    await cb.answer()


@sp.callback_query(F.data.startswith("sb:del:"))
async def sb_del(cb: CallbackQuery, manager: BotManager):
    bid = int(cb.data.split(":")[2])
    row = await q.get_bot(bid)
    if not row or row["is_parent"]:
        return await cb.answer("Topilmadi", show_alert=True)
    await manager.stop(bid)
    await q.purge_bot(bid)
    await cb.message.answer(f"🗑 @{row['username']} va uning barcha ma'lumotlari o'chirildi.")
    await cb.answer()


router.include_router(sp)
