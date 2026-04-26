"""
معالجات أوامر التيمات
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from utils import mention_user, group_only

logger = logging.getLogger(__name__)


@group_only
async def create_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /createteam - إنشاء تيم جديد"""
    chat = update.effective_chat
    user = update.effective_user

    db.ensure_group(chat.id, chat.title or "")
    player = db.get_or_create_player(
        user.id, chat.id,
        user.username or "",
        user.full_name or user.first_name
    )

    group = db.get_group(chat.id)
    if group and group["join_locked"]:
        await update.message.reply_text("🔒 إنشاء التيمات مقفل حالياً!")
        return

    if player["team_id"]:
        team = db.get_team(player["team_id"])
        await update.message.reply_text(
            f"❌ أنت بالفعل في تيم *{team['team_name']}*!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❓ اكتب اسم التيم: `/createteam اسم_التيم`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    team_name = " ".join(context.args).strip()[:30]

    if len(team_name) < 2:
        await update.message.reply_text("❌ اسم التيم قصير جداً!")
        return

    success = db.create_team(
        chat.id, team_name, user.id,
        user.full_name or user.first_name
    )

    if not success:
        await update.message.reply_text(
            f"❌ يوجد تيم باسم *{team_name}* بالفعل!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await update.message.reply_text(
        f"🏰 *تم إنشاء التيم بنجاح!*\n\n"
        f"👑 القائد: {mention_user(user)}\n"
        f"🏰 اسم التيم: *{team_name}*\n\n"
        f"📣 شارك `/join` مع أصدقائك ليتمكنوا من الانضمام!",
        parse_mode=ParseMode.MARKDOWN
    )


@group_only
async def my_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /myteam - عرض معلومات التيم"""
    chat = update.effective_chat
    user = update.effective_user

    player = db.get_player(user.id, chat.id)
    if not player or not player["team_id"]:
        await update.message.reply_text(
            f"⚠️ {mention_user(user)} أنت لست في أي تيم!\nاستخدم /join للانضمام.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    team = db.get_team(player["team_id"])
    members = db.get_team_members(team["id"])
    effects = db.get_team_effects(team["id"])

    # بناء قائمة الأعضاء
    members_text = ""
    for i, m in enumerate(members, 1):
        crown = " 👑" if m["user_id"] == team["leader_id"] else ""
        members_text += f"  {i}. {m['full_name']}{crown} — 💰{m['coins']}\n"

    # التأثيرات النشطة
    effects_text = ""
    if effects:
        effects_text = "\n✨ *التأثيرات النشطة:*\n"
        for e in effects:
            effects_text += f"  • {e['item_name']}\n"

    text = (
        f"🏰 *تيم {team['team_name']}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👑 القائد: {team['leader_name']}\n"
        f"💰 الخزينة: {team['treasury']} ذهب\n"
        f"🏆 نقاط الشرف: {team['honor_points']}\n"
        f"👥 الأعضاء ({len(members)}):\n"
        f"{members_text}"
        f"{effects_text}"
    )

    keyboard = [
        [InlineKeyboardButton("🗳️ انتخاب قائد", callback_data=f"vote_leader:{team['id']}:{chat.id}")]
    ]

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@group_only
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /leaderboard - ترتيب التيمات"""
    chat = update.effective_chat
    teams = db.get_group_teams(chat.id)

    if not teams:
        await update.message.reply_text("📊 لا توجد تيمات بعد في هذا الكروب!")
        return

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    text = "🏆 *لوحة الصدارة*\n━━━━━━━━━━━━━━━━\n"

    for i, team in enumerate(teams):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        members = db.get_team_members(team["id"])
        text += (
            f"{medal} *{team['team_name']}*\n"
            f"   🏆 {team['honor_points']} نقطة | 💰 {team['treasury']} | 👥 {len(members)}\n\n"
        )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
