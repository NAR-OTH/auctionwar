import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db

# استيراد الملفات كـ modules
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

    # 1. الأوامر العامة
    app.add_handler(CommandHandler("start", general.start_handler))
    if hasattr(general, 'help_handler'):
        app.add_handler(CommandHandler("help", general.help_handler))

    # 2. أوامر التيمات (حل مشكلة join و join_team)
    if hasattr(team_handler, 'join'):
        app.add_handler(CommandHandler("join", team_handler.join))
    elif hasattr(team_handler, 'join_team'):
        app.add_handler(CommandHandler("join", team_handler.join_team))

    if hasattr(team_handler, 'create'):
        app.add_handler(CommandHandler("create", team_handler.create))
    elif hasattr(team_handler, 'create_team'):
        app.add_handler(CommandHandler("create", team_handler.create_team))

    # 3. أوامر اللاعبين (العمل والهجوم)
    if hasattr(player, 'work'):
        app.add_handler(CommandHandler("work", player.work))
    elif hasattr(player, 'work_handler'):
        app.add_handler(CommandHandler("work", player.work_handler))

    if hasattr(player, 'attack'):
        app.add_handler(CommandHandler("attack", player.attack))
    elif hasattr(player, 'attack_handler'):
        app.add_handler(CommandHandler("attack", player.attack_handler))

    # 4. الأزرار والمزاد
    app.add_handler(CallbackQueryHandler(callbacks.button_callback_handler))

    if app.job_queue:
        app.job_queue.run_repeating(auction_manager.schedule_auction, interval=600, first=10)

    print("🚀 تم تشغيل النظام بالنمط الذكي - البوت جاهز!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
