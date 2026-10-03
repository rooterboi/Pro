from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import DEFAULT_ROOTER_CMD
from database import queries as q


class IsAdmin(BaseFilter):
    async def __call__(self, event, is_admin: bool = False) -> bool:
        return is_admin


class IsParent(BaseFilter):
    async def __call__(self, event, is_parent: bool = False) -> bool:
        return is_parent


class RooterCmd(BaseFilter):
    """Yashirin buyruq faqat Parent botda ishlaydi. Child botda hech qachon mos kelmaydi."""

    async def __call__(self, message: Message, bot_id: int, is_parent: bool = False) -> bool:
        if not is_parent or not message.text:
            return False
        cmd = await q.get_setting(bot_id, "rooter_cmd", DEFAULT_ROOTER_CMD)
        return message.text.split()[0].split("@")[0].lower() == f"/{cmd.lower()}"
