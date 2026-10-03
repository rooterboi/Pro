from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode

from config import LOCAL_API_URL


def make_bot(token: str) -> Bot:
    session = None
    if LOCAL_API_URL:
        session = AiohttpSession(api=TelegramAPIServer.from_base(LOCAL_API_URL, is_local=True))
    return Bot(token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
