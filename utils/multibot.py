"""
Multibot (Parent/Child) menejeri.

Bitta Dispatcher (bir xil handlerlar) bir nechta Bot obyektiga xizmat qiladi.
Har bir bot uchun alohida long-polling vazifasi (asyncio.Task) ishlaydi va
kelgan update `dp.feed_update(bot, update)` orqali umumiy handlerlarga uzatiladi.
Yangi bot ish vaqtida (restartsiz) qo'shilishi mumkin.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramRetryAfter, TelegramUnauthorizedError
from aiogram.types import Update

from database import queries as q
from utils.botfactory import make_bot

log = logging.getLogger(__name__)


class BotManager:
    def __init__(self, dp: Dispatcher):
        self.dp = dp
        self.bots: dict[int, Bot] = {}
        self.tasks: dict[int, asyncio.Task] = {}
        self._feeds: set[asyncio.Task] = set()

    async def validate(self, token: str):
        bot = make_bot(token)
        try:
            return await bot.get_me()
        finally:
            await bot.session.close()

    async def launch(self, token: str) -> Bot:
        bot = make_bot(token)
        try:
            me = await bot.get_me()
        except Exception:
            await bot.session.close()
            raise
        if me.id in self.tasks:
            await bot.session.close()
            return self.bots[me.id]
        self.bots[me.id] = bot
        self.tasks[me.id] = asyncio.create_task(self._poll(bot), name=f"poll-{me.id}")
        log.info("Bot ishga tushdi: @%s (%s)", me.username, me.id)
        return bot

    async def stop(self, bot_id: int):
        task = self.tasks.pop(bot_id, None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        bot = self.bots.pop(bot_id, None)
        if bot:
            await bot.session.close()

    async def launch_all(self):
        for row in await q.get_bots(active_only=True):
            try:
                await self.launch(row["token"])
            except TelegramUnauthorizedError:
                await q.set_bot_active(row["bot_id"], False)
                log.warning("Token yaroqsiz, bot o'chirildi: %s", row["username"])
            except Exception:
                log.exception("Botni ishga tushirib bo'lmadi: %s", row["username"])

    async def shutdown(self):
        for bid in list(self.tasks):
            await self.stop(bid)

    async def _feed(self, bot: Bot, update: Update):
        try:
            await self.dp.feed_update(bot, update)
        except Exception:
            log.exception("Update qayta ishlashda xato")

    async def _poll(self, bot: Bot):
        offset = None
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            pass
        types = self.dp.resolve_used_update_types()
        while True:
            try:
                updates = await bot.get_updates(offset=offset, timeout=30, allowed_updates=types)
                for u in updates:
                    offset = u.update_id + 1
                    t = asyncio.create_task(self._feed(bot, u))
                    self._feeds.add(t)
                    t.add_done_callback(self._feeds.discard)
            except asyncio.CancelledError:
                raise
            except TelegramUnauthorizedError:
                log.warning("Bot %s tokeni bekor qilingan", bot.id)
                await q.set_bot_active(bot.id, False)
                return
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Exception:
                log.exception("Polling xatosi (bot %s)", bot.id)
                await asyncio.sleep(3)
