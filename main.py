import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db

# استدعاء الملفات
import general
import team_handler
import player
import auction_handler
import leader_handler
import callbacks
import auction_manager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # --- الأوامر العامة ---
    app.add_handler(CommandHandler("start", general.start_handler))
    
    # --- أوامر التيمات (حسب الصورة مالتك) ---
    app.add_handler(CommandHandler("join", team_handler.join_team))
    app.add_handler(CommandHandler("create", team_handler.create_team))
    app.add_handler(CommandHandler("leaderboard", team_handler.leaderboard))
    
    # --- أوامر اللاعبين ---
    app.add_handler(CommandHandler("work", player.work_handler))
    app.add_handler(CommandHandler("attack", player.attack_handler))

    # --- الأزرار والمزاد ---
    app.add_handler(CallbackQueryHandler(callbacks.button_callback_handler))

    if app.job_queue:
        app.job_queue.run_repeating(auction_manager.schedule_auction, interval=600, first=10)

    print("🚀 البوت انطلق بالأسماء الصحيحة!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
