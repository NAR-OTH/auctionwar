import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db
from utils import mention_user, group_only

logger = logging.getLogger(__name__)


@group_only
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    db.ensure_group(chat.id, chat.title or "")
    db.get_or_create_player(user.id, chat.id, user.username or "", user.full_name or user.first_name)
    text = (
        "🏆 *مرحباً بك في حرب المزادات!*\n\n"
        "⚔️ اشكّل تيمك، اجمع الذهب، وانتصر في المزادات!\n\n"
        "📖 *أوامر البداية:*\n"
        "• /join — انضم للعبة وشكّل أو انضم لتيم\n"
        "• /createteam اسم_التيم — أنشئ تيمك\n"
        "• /work — اعمل لجمع الذهب\n"
        "• /status — اعرض حالتك\n"
        "• /help — قائمة كل الأوامر\n\n"
        "🎯 *المزادات تبدأ كل 10 دقائق تلقائياً!*"
    )
    keyboard = [[InlineKeyboardButton("⚔️ انضم للعبة", callback_data=f"join_game:{chat.id}"), InlineKeyboardButton("📋 المساعدة", callback_data="show_help")]]
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


@group_only
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📜 *قائمة أوامر حرب المزادات*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 *أوامر اللاعب*\n"
        "• `/join` — انضم للعبة\n"
        "• `/work` — اعمل لجمع الذهب (كل 5 دقائق)\n"
        "• `/status` — حالتك الحالية\n"
        "• `/myteam` — معلومات تيمك\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🏰 *أوامر التيمات*\n"
        "• `/createteam اسم` — أنشئ تيم جديد\n"
        "• `/myteam` — اعرض تيمك وأعضاءه\n"
        "• `/leaderboard` — ترتيب التيمات\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ *أوامر الهجوم*\n"
        "• `/attack` — هاجم تيماً آخر\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🏆 *أوامر القائد فقط*\n"
        "• `/lockattack` — قفل/فتح الهجوم\n"
        "• `/lockjoin` — قفل/فتح الانضمام\n"
        "• `/distribute مبلغ` — توزيع ذهب على الأعضاء\n"
        "• `/kick` — ردّ على عضو لطرده\n"
        "• `/stopgame` — إيقاف اللعبة\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎰 *المزادات تلقائية كل 10 دقائق!*"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@group_only
async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    db.ensure_group(chat.id, chat.title or "")
    group = db.get_group(chat.id)
    if group and group["join_locked"]:
        await update.message.reply_text("🔒 الانضمام للعبة مقفل حالياً!")
        return
    player = db.get_or_create_player(user.id, chat.id, user.username or "", user.full_name or user.first_name)
    if player["team_id"]:
        team = db.get_team(player["team_id"])
        await update.message.reply_text(f"✅ أنت بالفعل عضو في تيم *{team['team_name']}*!\n💰 رصيدك: {player['coins']} ذهب", parse_mode=ParseMode.MARKDOWN)
        return
    teams = db.get_group_teams(chat.id)
    if not teams:
        await update.message.reply_text(f"👋 أهلاً {mention_user(user)}!\n\nلا توجد تيمات بعد.\nكن أول من يُنشئ تيماً:\n`/createteam اسم_التيم`", parse_mode=ParseMode.MARKDOWN)
        return
    from config import MAX_TEAM_MEMBERS
    keyboard = []
    for team in teams:
        mc = len(db.get_team_members(team["id"]))
        keyboard.append([InlineKeyboardButton(f"🏰 {team['team_name']} ({mc}/{MAX_TEAM_MEMBERS}) | 💰{team['treasury']}", callback_data=f"join_team:{team['id']}:{chat.id}")])
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel")])
    await update.message.reply_text(f"👋 أهلاً {mention_user(user)}!\n\n🏰 *اختر التيم الذي تريد الانضمام إليه:*\n_(أو أنشئ تيمك: /createteam اسم)_", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


@group_only
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    player = db.get_player(user.id, chat.id)
    if not player:
        await update.message.reply_text(f"⚠️ {mention_user(user)} أنت غير مسجل! استخدم /join للانضمام.", parse_mode=ParseMode.MARKDOWN)
        return
    team_text = "❌ بدون تيم"
    effects_text = ""
    if player["team_id"]:
        team = db.get_team(player["team_id"])
        if team:
            team_text = f"🏰 {team['team_name']} {'👑' if team['leader_id'] == user.id else ''}"
            effects = db.get_team_effects(player["team_id"])
            if effects:
                effects_text = "\n\n✨ *تأثيرات نشطة:*\n" + "\n".join([f"  • {e['item_name']}" for e in effects])
    await update.message.reply_text(f"📊 *حالة اللاعب*\n\n👤 {mention_user(user)}\n🏰 التيم: {team_text}\n💰 الذهب: {player['coins']}\n⚒️ عدد مرات العمل: {player['total_work']}{effects_text}", parse_mode=ParseMode.MARKDOWN)
