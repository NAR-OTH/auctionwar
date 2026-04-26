import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db
from utils import group_only, build_auction_keyboard

logger = logging.getLogger(__name__)


@group_only
async def show_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    auction = db.get_active_auction(chat.id)
    if not auction:
        await update.message.reply_text("🎰 لا يوجد مزاد نشط حالياً.\nالمزادات تبدأ تلقائياً كل *10 دقائق*! ⏰", parse_mode=ParseMode.MARKDOWN)
        return
    winner_text = f"🥇 أعلى مزايد: *{auction['winner_name']}*" if auction["winner_name"] else "🎯 لا توجد مزايدات بعد!"
    text = (
        f"🎰 *مزاد نشط!*\n\n"
        f"🏆 الجائزة: *{auction['item_name']}*\n"
        f"📖 {auction['item_desc']}\n\n"
        f"💰 السعر الحالي: *{auction['current_bid']} ذهب*\n"
        f"{winner_text}\n\n"
        f"⏰ _المزايدة تغلق قريباً!_"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_auction_keyboard(auction["id"], auction["current_bid"]))
