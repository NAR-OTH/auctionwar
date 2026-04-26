import functools
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.constants import ChatType
import database as db

logger = logging.getLogger(__name__)


def mention_user(user: User) -> str:
    name = user.full_name or user.first_name or "مجهول"
    return f"[{name}](tg://user?id={user.id})"


def seconds_to_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} ثانية"
    minutes = seconds // 60
    secs = seconds % 60
    if secs:
        return f"{minutes} دقيقة و{secs} ثانية"
    return f"{minutes} دقيقة"


def build_auction_keyboard(auction_id: int, current_bid: int) -> InlineKeyboardMarkup:
    from config import AUCTION_MIN_INCREMENT
    inc = AUCTION_MIN_INCREMENT
    bids = [current_bid + inc, current_bid + inc * 5, current_bid + inc * 10, current_bid + inc * 25]
    buttons = [
        [
            InlineKeyboardButton(f"💰 {bids[0]}", callback_data=f"bid:{auction_id}:{bids[0]}"),
            InlineKeyboardButton(f"💰 {bids[1]}", callback_data=f"bid:{auction_id}:{bids[1]}"),
        ],
        [
            InlineKeyboardButton(f"💰 {bids[2]}", callback_data=f"bid:{auction_id}:{bids[2]}"),
            InlineKeyboardButton(f"💰 {bids[3]}", callback_data=f"bid:{auction_id}:{bids[3]}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def group_only(func):
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        chat = update.effective_chat
        if chat.type == ChatType.PRIVATE:
            await update.message.reply_text("⚠️ هذا البوت مخصص للكروبات فقط!\nأضفه لكروبك واستمتع باللعب.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def leader_only(func):
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        is_leader, team = db.is_team_leader(user.id, chat.id)
        if not is_leader:
            await update.message.reply_text("❌ هذا الأمر للقادة فقط!\nيجب أن تكون قائد تيم لاستخدامه.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
