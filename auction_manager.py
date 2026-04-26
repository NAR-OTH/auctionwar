import random
import logging
from datetime import datetime, timedelta, timezone
from telegram.constants import ParseMode
import database as db
from config import AUCTION_ITEMS, AUCTION_DURATION
from utils import build_auction_keyboard

logger = logging.getLogger(__name__)


async def schedule_auction(context):
    with db.get_db() as conn:
        active_groups = conn.execute("SELECT * FROM groups WHERE game_active = 1").fetchall()
    for group in active_groups:
        group_id = group["group_id"]
        if db.get_active_auction(group_id):
            continue
        if len(db.get_group_teams(group_id)) < 2:
            continue
        await _start_auction(context, group_id)


async def _start_auction(context, group_id: int):
    item = random.choice(AUCTION_ITEMS)
    ends_at = datetime.now(timezone.utc) + timedelta(seconds=AUCTION_DURATION)
    auction_id = db.create_auction(group_id, item, ends_at)
    text = (
        f"🚨 *مزاد جديد بدأ!* 🚨\n\n"
        f"🏆 الجائزة: *{item['name']}*\n"
        f"📖 {item['description']}\n\n"
        f"💰 سعر البداية: *{item['base_price']} ذهب*\n"
        f"⏰ المزاد يغلق خلال *3 دقائق*!\n\n"
        f"🎯 _زايد الآن بالأزرار أدناه!_"
    )
    try:
        msg = await context.bot.send_message(chat_id=group_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_auction_keyboard(auction_id, item["base_price"]))
        db.set_auction_message_id(auction_id, msg.message_id)
        context.job_queue.run_once(_close_auction_job, when=AUCTION_DURATION, data={"auction_id": auction_id, "group_id": group_id, "message_id": msg.message_id}, name=f"close_auction_{auction_id}")
        logger.info(f"✅ بدأ مزاد {auction_id} في كروب {group_id}")
    except Exception as e:
        logger.error(f"❌ خطأ في إطلاق المزاد في كروب {group_id}: {e}")


async def _close_auction_job(context):
    data = context.job.data
    auction = db.close_auction(data["auction_id"])
    if not auction:
        return
    if auction["winner_team"]:
        result_text = (
            f"🏁 *انتهى المزاد!*\n\n"
            f"🏆 الجائزة: *{auction['item_name']}*\n"
            f"👑 الفائز: تيم *{auction['winner_name']}*\n"
            f"💰 بمبلغ: *{auction['current_bid']} ذهب*\n\n"
            f"✨ تمت إضافة الجائزة لتيم الفائز تلقائياً!"
        )
    else:
        result_text = f"🏁 *انتهى المزاد بدون فائز!*\n\nلم يزايد أحد على *{auction['item_name']}*.\nمزاد جديد سيبدأ قريباً!"
    try:
        await context.bot.edit_message_text(chat_id=data["group_id"], message_id=data["message_id"], text=result_text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        try:
            await context.bot.send_message(chat_id=data["group_id"], text=result_text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"❌ خطأ في إغلاق المزاد: {e}")
