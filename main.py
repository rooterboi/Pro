import asyncio
import logging
import os

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import ADMIN_IDS, BOT_TOKEN, TMP_DIR
from database import db, queries as q
from handlers import admin_misc, admin_movies, admin_series, common, rooter, user
from middlewares.context import ContextMiddleware
from middlewares.forcesub import ForceSubMiddleware
from utils.botfactory import make_bot
from utils.ffmpeg_utils import ffmpeg_available
from utils.multibot import BotManager


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN .env faylda ko'rsatilmagan!")
    os.makedirs(TMP_DIR, exist_ok=True)
    if not ffmpeg_available():
        logging.warning("ffmpeg/ffprobe topilmadi — teaser o'rniga poster bilan post qilinadi.")

    await db.init()

    # Parent botni bazaga yozamiz
    tmp = make_bot(BOT_TOKEN)
    me = await tmp.get_me()
    await tmp.session.close()
    old = await q.get_bot(me.id)
    await q.add_bot(me.id, BOT_TOKEN, me.username, owner_id=0, is_parent=1)
    if old is None:
        logging.info("Parent bot: @%s | super-adminlar: %s", me.username, ADMIN_IDS)

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(ContextMiddleware())
    dp.message.outer_middleware(ForceSubMiddleware())
    dp.callback_query.outer_middleware(ForceSubMiddleware())

    # Tartib muhim: common(/cancel) -> rooter -> admin -> user (universal qidiruv oxirida)
    dp.include_routers(common.router, rooter.router, admin_misc.router,
                       admin_movies.router, admin_series.router, user.router)

    manager = BotManager(dp)
    dp.workflow_data["manager"] = manager
    await manager.launch_all()
    logging.info("Ishga tushgan botlar: %d", len(manager.bots))
    try:
        await asyncio.Event().wait()
    finally:
        await manager.shutdown()
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
