import logging
import asyncio
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, JobQueue
)
# استدعاء التوكن وقاعدة البيانات
from config import BOT_TOKEN
from database import init_db

# استدعاء الوظائف من الملفات مباشرة حسب الأسماء في GitHub مالتك
from general import start_handler, help_handler, status_handler
from team_handler import join_handler, team_handler_obj # تأكد من اسم الكائن بداخل ملفك
from player import work_handler, attack_handler
from auction_handler import auction_handler
from leader_handler import leader_handler
from callbacks import button_callback_handler
from auction_manager import schedule_auction

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    # تهيئة الداتابيس
    init_db()
    logger.info("✅ تم تهيئة قاعدة البيانات")

    # بناء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("join", join_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("work", work_handler))
    app.add_handler(CommandHandler("attack", attack_handler))
    
    # أوامر القائد والمزاد (تأكد أن الوظائف موجودة بهذه الأسماء داخل ملفاتها)
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    # تشغيل المزاد التلقائي كل 10 دقائق
    if app.job_queue:
        app.job_queue.run_repeating(schedule_auction, interval=600, first=10)

    logger.info("🚀 البوت انطلق...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
