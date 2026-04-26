"""
🏆 حرب المزادات - Auction War Bot
بوت تليجرام للعب الجماعي داخل الكروبات
"""

import logging
import asyncio
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, JobQueue
)
from config import BOT_TOKEN
from database import init_db
from general import start_handler, help_handler
from team_handler import join_handler, team_handler
from player import work_handler, attack_handler
from auction_handler import auction_handler
from leader_handler import leader_handler
# أي ملف ثاني ناقص استدعيه بنفس الطريقة

from callbacks import button_callback_handler
from auction_manager import schedule_auction

# إعداد نظام السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """نقطة البداية الرئيسية للبوت"""
    # تهيئة قاعدة البيانات
    init_db()
    logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")

    # إنشاء تطبيق البوت
    app = Application.builder().token(BOT_TOKEN).build()

    # ── أوامر عامة ──
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("join", join_handler))
    app.add_handler(CommandHandler("status", status_handler))

    # ── أوامر اللاعبين ──
    app.add_handler(CommandHandler("work", work_handler))
    app.add_handler(CommandHandler("attack", attack_handler))

    # ── أوامر التيمات ──
    app.add_handler(CommandHandler("createteam", team_handler.create_team))
    app.add_handler(CommandHandler("myteam", team_handler.my_team))
    app.add_handler(CommandHandler("leaderboard", team_handler.leaderboard))

    # ── أوامر المزاد ──
    app.add_handler(CommandHandler("auction", auction_handler.show_auction))

    # ── أوامر القائد ──
    app.add_handler(CommandHandler("lockattack", leader_handler.lock_attack))
    app.add_handler(CommandHandler("unlockattack", leader_handler.unlock_attack))
    app.add_handler(CommandHandler("lockjoin", leader_handler.lock_join))
    app.add_handler(CommandHandler("unlockjoin", leader_handler.unlock_join))
    app.add_handler(CommandHandler("stopgame", leader_handler.stop_game))
    app.add_handler(CommandHandler("distribute", leader_handler.distribute_coins))
    app.add_handler(CommandHandler("kick", leader_handler.kick_member))

    # ── معالج الأزرار التفاعلية ──
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    # ── جدولة المزادات التلقائية كل 10 دقائق ──
    job_queue = app.job_queue
    job_queue.run_repeating(
        schedule_auction,
        interval=600,  # 10 دقائق
        first=60        # أول مزاد بعد دقيقة من التشغيل
    )

    logger.info("🚀 البوت يعمل الآن...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
