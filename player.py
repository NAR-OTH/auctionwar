"""
معالجات أفعال اللاعب: العمل والهجوم
"""
import random
import logging
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from config import (
    WORK_REWARD_MIN, WORK_REWARD_MAX, WORK_COOLDOWN,
    ATTACK_COOLDOWN, ATTACK_STEAL_PERCENT, HONOR_PER_WORK, HONOR_PER_WIN
)
from utils import mention_user, group_only, seconds_to_time

logger = logging.getLogger(__name__)


@group_only
async def work_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /work - اعمل واكسب الذهب"""
    chat = update.effective_chat
    user = update.effective_user

    player = db.get_player(user.id, chat.id)
    if not player:
        await update.message.reply_text(
            f"⚠️ {mention_user(user)} سجّل أولاً عبر /join",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── فحص الكولداون ──
    if player["last_work"]:
        last = datetime.fromisoformat(str(player["last_work"]))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        elapsed = (now - last).total_seconds()

        if elapsed < WORK_COOLDOWN:
            remaining = int(WORK_COOLDOWN - elapsed)
            await update.message.reply_text(
                f"⏳ {mention_user(user)} يمكنك العمل مجدداً خلال *{seconds_to_time(remaining)}*",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # حساب المكافأة
    reward = random.randint(WORK_REWARD_MIN, WORK_REWARD_MAX)

    # تأثير مضاعفة الذهب
    if player["team_id"] and db.has_effect(player["team_id"], "work_boost"):
        reward *= 2
        boost_text = " _(x2 بسبب صندوق الكنز!)_"
    else:
        boost_text = ""

    # تحديث قاعدة البيانات
    db.update_player_coins(user.id, chat.id, reward)
    db.update_last_work(user.id, chat.id)

    # إضافة للخزينة وللشرف إن كان في تيم
    if player["team_id"]:
        team_share = int(reward * 0.3)  # 30% للخزينة
        db.update_treasury(player["team_id"], team_share)
        db.update_honor(player["team_id"], HONOR_PER_WORK)
        team_text = f"\n🏦 +{team_share} ذهب لخزينة تيمك"
    else:
        team_text = ""

    # رسائل عمل عشوائية ممتعة
    work_msgs = [
        "⚒️ عملت في المنجم وعثرت على كنز!",
        "🌾 حصدت المحاصيل ببراعة!",
        "🐟 صدت أسماكاً نادرة!",
        "🔨 صنعت أدوات وبعتها بسعر جيد!",
        "📦 أتممت صفقة تجارية رابحة!",
        "🏺 نبشت في الأطلال ووجدت ثروة!",
    ]

    text = (
        f"{random.choice(work_msgs)}\n\n"
        f"👤 {mention_user(user)}\n"
        f"💰 كسبت *+{reward} ذهب*{boost_text}"
        f"{team_text}"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@group_only
async def attack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /attack - هاجم تيماً آخر"""
    chat = update.effective_chat
    user = update.effective_user

    # التحقق من حالة الهجوم في الكروب
    group = db.get_group(chat.id)
    if group and group["attack_locked"]:
        await update.message.reply_text("🔒 الهجوم مقفل حالياً في هذا الكروب!")
        return

    player = db.get_player(user.id, chat.id)
    if not player:
        await update.message.reply_text(
            f"⚠️ {mention_user(user)} سجّل أولاً عبر /join",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not player["team_id"]:
        await update.message.reply_text(
            f"⚠️ {mention_user(user)} يجب أن تكون في تيم للهجوم!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # فحص الكولداون
    if player["last_attack"]:
        last = datetime.fromisoformat(str(player["last_attack"]))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        elapsed = (now - last).total_seconds()

        if elapsed < ATTACK_COOLDOWN:
            remaining = int(ATTACK_COOLDOWN - elapsed)
            await update.message.reply_text(
                f"⏳ {mention_user(user)} يمكنك الهجوم مجدداً خلال *{seconds_to_time(remaining)}*",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # التحقق من تحديد الهدف
    if not context.args:
        teams = db.get_group_teams(chat.id)
        my_team_id = player["team_id"]
        enemy_teams = [t for t in teams if t["id"] != my_team_id and t["active"]]

        if not enemy_teams:
            await update.message.reply_text("😔 لا توجد تيمات أخرى لمهاجمتها!")
            return

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        for team in enemy_teams:
            btn = InlineKeyboardButton(
                f"⚔️ {team['team_name']} | 🏦 {team['treasury']}",
                callback_data=f"attack:{team['id']}:{user.id}:{chat.id}"
            )
            keyboard.append([btn])

        await update.message.reply_text(
            f"⚔️ {mention_user(user)} *اختر التيم الذي تريد مهاجمته:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # هجوم مباشر باسم التيم
    target_name = " ".join(context.args)
    await _execute_attack(update, context, user, player, chat, target_name)


async def _execute_attack(update, context, user, player, chat, target_name):
    """تنفيذ الهجوم الفعلي"""
    target_team = db.get_team_by_name(chat.id, target_name)
    if not target_team:
        await update.message.reply_text(
            f"❌ لا يوجد تيم باسم *{target_name}*!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if target_team["id"] == player["team_id"]:
        await update.message.reply_text("🤦 لا يمكنك مهاجمة تيمك الخاص!")
        return

    attacker_team = db.get_team(player["team_id"])

    # التحقق من الدرع الواقي
    if db.has_effect(target_team["id"], "defense_shield"):
        await update.message.reply_text(
            f"🛡️ تيم *{target_team['team_name']}* محمي بـ **درع الحصن**! لا يمكن الهجوم عليه الآن.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # حساب السرقة
    steal_percent = ATTACK_STEAL_PERCENT
    if db.has_effect(player["team_id"], "steal_boost"):
        steal_percent = 0.30
    if db.has_effect(player["team_id"], "attack_boost"):
        steal_percent *= 2

    stolen = int(target_team["treasury"] * steal_percent)
    stolen = max(0, stolen)

    # تحديث الخزائن
    db.update_treasury(target_team["id"], -stolen)
    db.update_treasury(attacker_team["id"], stolen)
    db.update_honor(attacker_team["id"], HONOR_PER_WIN)
    db.update_last_attack(user.id, chat.id)

    # تسجيل الهجوم
    with db.get_db() as conn:
        conn.execute("""
            INSERT INTO attack_log (group_id, attacker_team, defender_team, stolen_amount, result)
            VALUES (?, ?, ?, ?, 'win')
        """, (chat.id, attacker_team["id"], target_team["id"], stolen))

    text = (
        f"⚔️ *هجوم ناجح!*\n\n"
        f"🗡️ المهاجم: تيم *{attacker_team['team_name']}*\n"
        f"🏰 المدافع: تيم *{target_team['team_name']}*\n"
        f"💰 تمت سرقة: *{stolen} ذهب*\n\n"
        f"🏆 +{HONOR_PER_WIN} نقطة شرف لتيم {attacker_team['team_name']}!"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
