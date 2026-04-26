import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db
from utils import mention_user, group_only, leader_only

logger = logging.getLogger(__name__)


@group_only
@leader_only
async def lock_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    group = db.get_group(chat.id)
    new_val = 0 if (group and group["attack_locked"]) else 1
    db.set_group_flag(chat.id, "attack_locked", new_val)
    await update.message.reply_text(f"⚔️ الهجوم الآن: *{'🔒 مقفل' if new_val else '🔓 مفتوح'}*", parse_mode=ParseMode.MARKDOWN)


@group_only
@leader_only
async def unlock_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_group_flag(update.effective_chat.id, "attack_locked", 0)
    await update.message.reply_text("🔓 تم *فتح الهجوم* في الكروب!", parse_mode=ParseMode.MARKDOWN)


@group_only
@leader_only
async def lock_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    group = db.get_group(chat.id)
    new_val = 0 if (group and group["join_locked"]) else 1
    db.set_group_flag(chat.id, "join_locked", new_val)
    await update.message.reply_text(f"🚪 الانضمام الآن: *{'🔒 مقفل' if new_val else '🔓 مفتوح'}*", parse_mode=ParseMode.MARKDOWN)


@group_only
@leader_only
async def unlock_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_group_flag(update.effective_chat.id, "join_locked", 0)
    await update.message.reply_text("🔓 تم *فتح الانضمام*!", parse_mode=ParseMode.MARKDOWN)


@group_only
@leader_only
async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    db.set_group_flag(chat.id, "game_active", 0)
    db.set_group_flag(chat.id, "attack_locked", 1)
    db.set_group_flag(chat.id, "join_locked", 1)
    await update.message.reply_text(f"🛑 *تم إيقاف اللعبة* بواسطة {mention_user(user)}\n\nاستخدم /start لإعادة تشغيل اللعبة.", parse_mode=ParseMode.MARKDOWN)


@group_only
@leader_only
async def distribute_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    _, team = db.is_team_leader(user.id, chat.id)
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❓ الاستخدام: `/distribute مبلغ`", parse_mode=ParseMode.MARKDOWN)
        return
    amount = int(context.args[0])
    members = db.get_team_members(team["id"])
    total = amount * len(members)
    if team["treasury"] < total:
        await update.message.reply_text(f"❌ خزينتك لا تكفي! تحتاج *{total}* ذهب ولديك *{team['treasury']}*.", parse_mode=ParseMode.MARKDOWN)
        return
    db.update_treasury(team["id"], -total)
    for member in members:
        db.update_player_coins(member["user_id"], chat.id, amount)
    await update.message.reply_text(f"💰 *تم التوزيع بنجاح!*\n\nحصل كل عضو على *{amount} ذهب*\nالمجموع المصروف: *{total} ذهب*", parse_mode=ParseMode.MARKDOWN)


@group_only
@leader_only
async def kick_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ *ردّ على رسالة العضو* الذي تريد طرده مع كتابة /kick", parse_mode=ParseMode.MARKDOWN)
        return
    target = update.message.reply_to_message.from_user
    _, my_team = db.is_team_leader(user.id, chat.id)
    target_player = db.get_player(target.id, chat.id)
    if not target_player or target_player["team_id"] != my_team["id"]:
        await update.message.reply_text("❌ هذا الشخص ليس في تيمك!")
        return
    if target.id == user.id:
        await update.message.reply_text("❌ لا يمكنك طرد نفسك!")
        return
    with db.get_db() as conn:
        conn.execute("UPDATE players SET team_id = NULL WHERE user_id = ? AND group_id = ?", (target.id, chat.id))
    await update.message.reply_text(f"🚪 تم طرد {mention_user(target)} من تيم *{my_team['team_name']}*!", parse_mode=ParseMode.MARKDOWN)
