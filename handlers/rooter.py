"""Maxfiy /rooter: PIN -> Bot token -> yangi Child bot (faqat Parent botda)."""
import re
import time

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import DEFAULT_ROOTER_PIN
from database import queries as q
from handlers.filters import IsParent, RooterCmd
from states.states import RooterStates
from utils.multibot import BotManager

router = Router()
router.message.filter(IsParent())  # Child botlarda bu router umuman ishlamaydi

_blocked: dict[int, float] = {}
TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")


@router.message(RooterCmd())
async def rooter(msg: Message, state: FSMContext):
    if time.time() < _blocked.get(msg.from_user.id, 0):
        return await msg.answer("⛔ Ko'p xato urinish. Keyinroq urinib ko'ring.")
    await state.set_state(RooterStates.pin)
    await state.update_data(tries=0)
    await msg.answer("🔐 PIN-kodni kiriting:\n(/cancel — bekor qilish)")


@router.message(RooterStates.pin, F.text)
async def check_pin(msg: Message, state: FSMContext, bot_id: int):
    real = await q.get_setting(bot_id, "rooter_pin", DEFAULT_ROOTER_PIN)
    try:
        await msg.delete()
    except Exception:
        pass
    if msg.text.strip() == real:
        await state.set_state(RooterStates.token)
        return await msg.answer("✅ PIN to'g'ri.\n\n🤖 Yangi Kino Bot tokenini yuboring (@BotFather dan):")
    tries = (await state.get_data()).get("tries", 0) + 1
    if tries >= 3:
        _blocked[msg.from_user.id] = time.time() + 600
        await state.clear()
        return await msg.answer("⛔ 3 marta xato. 10 daqiqaga bloklandingiz.")
    await state.update_data(tries=tries)
    await msg.answer(f"❌ Noto'g'ri PIN. Qolgan urinish: {3 - tries}")


@router.message(RooterStates.token, F.text)
async def new_bot(msg: Message, state: FSMContext, manager: BotManager):
    token = msg.text.strip()
    try:
        await msg.delete()  # token chatda qolmasin
    except Exception:
        pass
    if not TOKEN_RE.match(token):
        return await msg.answer("❌ Token formati noto'g'ri. Qayta yuboring yoki /cancel.")
    try:
        me = await manager.validate(token)
    except Exception:
        return await msg.answer("❌ Token yaroqsiz (Telegram rad etdi). Qayta yuboring yoki /cancel.")
    if await q.get_bot(me.id):
        await state.clear()
        return await msg.answer("⚠️ Bu bot allaqachon tizimga ulangan.")

    await q.add_bot(me.id, token, me.username, owner_id=msg.from_user.id, is_parent=0)  # Child
    try:
        await manager.launch(token)
    except Exception as e:
        await q.purge_bot(me.id)
        await state.clear()
        return await msg.answer(f"❌ Botni ishga tushirib bo'lmadi: {e}")
    await state.clear()
    await msg.answer(
        f"🎉 <b>@{me.username}</b> ishga tushdi!\n\n"
        f"Endi shu botga kirib /start va /admin yuboring — siz uning egasisiz.\n"
        f"ℹ️ Sub-botda /rooter ishlamaydi."
    )
