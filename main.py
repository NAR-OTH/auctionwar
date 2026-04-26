import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db

# استيراد الملفات كأدوات كاملة (Modules) لتجنب أخطاء الأسماء
import general
import team_handler
import player
import auction_handler
import leader_handler
import callbacks
import auction_manager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # ربط الأوامر (استخدمنا اسم الملف . اسم الوظيفة)
    # ملاحظة: إذا طلع خطأ بكلمة بعد النقطة، راح نعرف وين النقص بالضبط
    app.add_handler(CommandHandler("start", general.start_handler))
    app.add_handler(CommandHandler("help", general.help_handler))
    
    # إذا كان join_handler داخل ملف team_handler
    try:
        app.add_handler(CommandHandler("join", team_handler.join_handler))
    except AttributeError:
        logger.warning("لم يتم العثور على join_handler في team_handler")

    app.add_handler(CallbackQueryHandler(callbacks.button_callback_handler))

    if app.job_queue:
        app.job_queue.run_repeating(auction_manager.schedule_auction, interval=600, first=10)

    print("🚀 البوت يحاول الإقلاع...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
