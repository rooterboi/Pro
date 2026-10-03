from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import DEFAULT_ROOTER_CMD
from database import queries as q
from keyboards.user_kb import main_menu, sub_kb

TEXT = "🔒 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, so'ng «✅ Tekshirish» tugmasini bosing:"


async def get_missing(bot, bot_id: int, user_id: int):
    missing = []
    for c in await q.get_channels(bot_id):
        try:
            m = await bot.get_chat_member(c["chat_id"], user_id)
            if m.status in ("left", "kicked"):
                missing.append(c)
        except Exception:
            continue  # bot kanalda admin emas — tekshirib bo'lmaydi, o'tkazib yuboramiz
    return missing


class ForceSubMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict):
        if data.get("is_admin"):
            return await handler(event, data)
        if isinstance(event, Message) and event.chat.type != "private":
            return await handler(event, data)
        bot, bot_id = data["bot"], data["bot_id"]
        user = data["event_from_user"]

        # Maxfiy /rooter jarayoni obunadan ozod
        if (data.get("raw_state") or "").startswith("RooterStates"):
            return await handler(event, data)
        if isinstance(event, Message) and data.get("is_parent") and event.text:
            cmd = await q.get_setting(bot_id, "rooter_cmd", DEFAULT_ROOTER_CMD)
            if event.text.split()[0].split("@")[0].lower() == f"/{cmd.lower()}":
                return await handler(event, data)

        missing = await get_missing(bot, bot_id, user.id)
        is_chk = isinstance(event, CallbackQuery) and event.data == "chk"
        if not missing:
            if is_chk:
                await event.answer("✅ Rahmat!")
                try:
                    await event.message.delete()
                except Exception:
                    pass
                await bot.send_message(user.id, "🎬 Xush kelibsiz! Kino nomi yoki kodini yuboring.",
                                       reply_markup=main_menu(False))
                return
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            if is_chk:
                return await event.answer("❗ Hali hamma kanalga obuna bo'lmadingiz.", show_alert=True)
            await event.answer()
            return await event.message.answer(TEXT, reply_markup=sub_kb(missing))
        return await event.answer(TEXT, reply_markup=sub_kb(missing))
