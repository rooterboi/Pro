from aiogram import BaseMiddleware
from aiogram.types import Update

from config import ADMIN_IDS
from database import queries as q

_seen: set[tuple[int, int]] = set()


class ContextMiddleware(BaseMiddleware):
    """Har bir update uchun: qaysi bot, Parent/Child roli, admin ekanligi, foydalanuvchini ro'yxatga olish."""

    async def __call__(self, handler, event: Update, data: dict):
        bot = data["bot"]
        info = await q.get_bot(bot.id)
        if info is None:
            return
        user = data.get("event_from_user")
        data["bot_id"] = bot.id
        data["is_parent"] = bool(info["is_parent"])  # Is_Parent / Child roli
        data["is_admin"] = bool(user and (user.id in ADMIN_IDS or user.id == info["owner_id"]))
        if user and (bot.id, user.id) not in _seen:
            await q.add_user(bot.id, user)
            _seen.add((bot.id, user.id))
        return await handler(event, data)
      
