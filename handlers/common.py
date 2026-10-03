from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.user_kb import main_menu

router = Router()


@router.message(Command("cancel"))
async def cancel(msg: Message, state: FSMContext, is_admin: bool = False):
    await state.clear()
    await msg.answer("❌ Bekor qilindi.", reply_markup=main_menu(is_admin))
