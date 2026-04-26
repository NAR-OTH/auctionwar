"""
معالج الأزرار التفاعلية (Inline Buttons)
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from utils import mention_user, build_auction_keyboard

logger = logging.getLogger(__name__)


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج مركزي لجميع الأزرار"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user
    chat = query.message.chat

    # ── الانضمام للعبة ──
    if data.startswith("join_game:"):
        group_id = int(data.split(":")[1])
        await _handle_join_game(query, user, group_id)

    # ── الانضمام لتيم ──
    elif data.startswith("join_team:"):
        parts = data.split(":")
        team_id = int(parts[1])
        group_id = int(parts[2])
        await _handle_join_team(query, user, team_id, group_id)

    # ── المزايدة ──
    elif data.startswith("bid:"):
        parts = data.split(":")
        auction_id = int(parts[1])
        amount = int(parts[2])
        await _handle_bid(query, user, chat, auction_id, amount)

    # ── الهجوم ──
    elif data.startswith("attack:"):
        parts = data.split(":")
        target_team_id = int(parts[1])
        attacker_id = int(parts[2])
        group_id = int(parts[3])
        if user.id != attacker_id:
            await query.answer("❌ هذا الزر ليس لك!", show_alert=True)
            return
        await _handle_attack_button(query, user, target_team_id, group_id)

    # ── التصويت للقائد ──
    elif data.startswith("vote_leader:"):
        parts = data.split(":")
        team_id = int(parts[1])
        group_id = int(parts[2])
        await _handle_vote_leader(query, user, team_id, group_id)

    elif data.startswith("vote_for:"):
        parts = data.split(":")
        team_id = int(parts[1])
        candidate_id = int(parts[2])
        group_id = int(parts[3])
        await _handle_cast_vote(query, user, team_id, candidate_id, group_id)

    # ── إلغاء ──
    elif data == "cancel":
        await query.message.delete()

    # ── مساعدة ──
    elif data == "show_help":
        from handlers.general import help_handler
        await query.message.reply_text(
            "استخدم /help لعرض قائمة الأوامر الكاملة!"
        )


async def _handle_join_game(query, user, group_id: int):
    """معالجة الانضمام للعبة"""
    db.ensure_group(group_id)
    group = db.get_group(group_id)

    if group and group["join_locked"]:
        await query.answer("🔒 الانضمام مقفل حالياً!", show_alert=True)
        return

    player = db.get_or_create_player(
        user.id, group_id,
        user.username or "",
        user.full_name or user.first_name
    )

    if player["team_id"]:
        team = db.get_team(player["team_id"])
        await query.answer(f"✅ أنت بالفعل في تيم {team['team_name']}!", show_alert=True)
        return

    await query.answer("✅ تم تسجيلك! الآن انضم لتيم.", show_alert=True)


async def _handle_join_team(query, user, team_id: int, group_id: int):
    """معالجة الانضمام لتيم"""
    db.ensure_group(group_id)
    group = db.get_group(group_id)

    if group and group["join_locked"]:
        await query.answer("🔒 الانضمام مقفل!", show_alert=True)
        return

    player = db.get_or_create_player(
        user.id, group_id,
        user.username or "",
        user.full_name or user.first_name
    )

    if player["team_id"]:
        await query.answer("❌ أنت بالفعل في تيم!", show_alert=True)
        return

    team = db.get_team(team_id)
    if not team:
        await query.answer("❌ التيم غير موجود!", show_alert=True)
        return

    success = db.join_team(user.id, group_id, team_id)
    if not success:
        await query.answer("❌ التيم ممتلئ!", show_alert=True)
        return

    # تحديث الرسالة
    await query.answer(f"🎉 انضممت لتيم {team['team_name']}!", show_alert=True)

    try:
        await query.message.edit_text(
            f"✅ {mention_user(user)} انضم لتيم *{team['team_name']}*! 🎊",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass


async def _handle_bid(query, user, chat, auction_id: int, amount: int):
    """معالجة المزايدة"""
    player = db.get_player(user.id, chat.id)

    if not player:
        await query.answer("❌ سجّل أولاً عبر /join", show_alert=True)
        return

    if not player["team_id"]:
        await query.answer("❌ يجب أن تكون في تيم للمزايدة!", show_alert=True)
        return

    team = db.get_team(player["team_id"])
    if not team:
        await query.answer("❌ خطأ في بيانات التيم!", show_alert=True)
        return

    if team["treasury"] < amount:
        await query.answer(
            f"❌ خزينتك لا تكفي! لديك {team['treasury']} ذهب فقط.",
            show_alert=True
        )
        return

    success = db.place_bid(auction_id, team["id"], user.id, amount, team["team_name"])

    if not success:
        await query.answer(
            "❌ المزايدة فشلت! قد تكون المزايدة أقل من الحد الأدنى أو المزاد انتهى.",
            show_alert=True
        )
        return

    await query.answer(f"✅ مزايدتك بـ {amount} ذهب مقبولة!", show_alert=True)

    # تحديث رسالة المزاد
    auction = db.get_active_auction(chat.id)
    if auction:
        text = (
            f"🎰 *مزاد نشط!*\n\n"
            f"🏆 الجائزة: *{auction['item_name']}*\n"
            f"📖 {auction['item_desc']}\n\n"
            f"💰 السعر الحالي: *{auction['current_bid']} ذهب*\n"
            f"🥇 أعلى مزايد: *{auction['winner_name']}*\n\n"
            f"⚡ {mention_user(user)} زايد بـ *{amount} ذهب*!\n"
            f"⏰ _المزايدة تغلق قريباً!_"
        )
        keyboard = build_auction_keyboard(auction["id"], auction["current_bid"])
        try:
            await query.message.edit_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"خطأ في تحديث رسالة المزاد: {e}")


async def _handle_attack_button(query, user, target_team_id: int, group_id: int):
    """تنفيذ الهجوم عبر الزر"""
    from config import ATTACK_STEAL_PERCENT, HONOR_PER_WIN
    import random

    player = db.get_player(user.id, group_id)
    if not player or not player["team_id"]:
        await query.answer("❌ أنت لست في تيم!", show_alert=True)
        return

    target_team = db.get_team(target_team_id)
    attacker_team = db.get_team(player["team_id"])

    if db.has_effect(target_team["id"], "defense_shield"):
        await query.answer("🛡️ هذا التيم محمي! لا يمكن مهاجمته.", show_alert=True)
        return

    stolen = int(target_team["treasury"] * ATTACK_STEAL_PERCENT)
    db.update_treasury(target_team["id"], -stolen)
    db.update_treasury(attacker_team["id"], stolen)
    db.update_honor(attacker_team["id"], HONOR_PER_WIN)
    db.update_last_attack(user.id, group_id)

    text = (
        f"⚔️ *هجوم ناجح!*\n\n"
        f"🗡️ تيم *{attacker_team['team_name']}* هاجم تيم *{target_team['team_name']}*\n"
        f"💰 تمت سرقة *{stolen} ذهب*!"
    )

    try:
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await query.answer(f"⚔️ هجوم ناجح! سُرق {stolen} ذهب!", show_alert=True)


async def _handle_vote_leader(query, user, team_id: int, group_id: int):
    """عرض قائمة الأعضاء للتصويت"""
    player = db.get_player(user.id, group_id)
    if not player or player["team_id"] != team_id:
        await query.answer("❌ أنت لست في هذا التيم!", show_alert=True)
        return

    members = db.get_team_members(team_id)
    team = db.get_team(team_id)

    keyboard = []
    for m in members:
        if m["user_id"] != user.id:
            keyboard.append([
                InlineKeyboardButton(
                    f"🗳️ {m['full_name']}",
                    callback_data=f"vote_for:{team_id}:{m['user_id']}:{group_id}"
                )
            ])

    if not keyboard:
        await query.answer("❌ لا يوجد أعضاء آخرون للتصويت!", show_alert=True)
        return

    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel")])

    await query.message.reply_text(
        f"🗳️ *انتخاب قائد تيم {team['team_name']}*\n\nاختر من تريد تصويته قائداً:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _handle_cast_vote(query, user, team_id: int, candidate_id: int, group_id: int):
    """تسجيل صوت انتخابي"""
    player = db.get_player(user.id, group_id)
    if not player or player["team_id"] != team_id:
        await query.answer("❌ أنت لست في هذا التيم!", show_alert=True)
        return

    try:
        with db.get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO leader_votes (group_id, team_id, voter_id, candidate_id)
                VALUES (?, ?, ?, ?)
            """, (group_id, team_id, user.id, candidate_id))
    except Exception:
        await query.answer("❌ خطأ في تسجيل الصوت!", show_alert=True)
        return

    # تحقق من نتائج التصويت
    members = db.get_team_members(team_id)
    total_members = len(members)

    with db.get_db() as conn:
        votes = conn.execute("""
            SELECT candidate_id, COUNT(*) as cnt
            FROM leader_votes
            WHERE team_id = ? AND group_id = ?
            GROUP BY candidate_id
            ORDER BY cnt DESC
        """, (team_id, group_id)).fetchall()

    from config import MIN_VOTE_PERCENT
    winner = None
    for v in votes:
        if v["cnt"] / total_members >= MIN_VOTE_PERCENT:
            winner = v["candidate_id"]
            break

    if winner:
        with db.get_db() as conn:
            winner_player = conn.execute(
                "SELECT * FROM players WHERE user_id = ? AND group_id = ?",
                (winner, group_id)
            ).fetchone()
            conn.execute("""
                UPDATE teams SET leader_id = ?, leader_name = ? WHERE id = ?
            """, (winner, winner_player["full_name"] if winner_player else "قائد", team_id))
            conn.execute("""
                DELETE FROM leader_votes WHERE team_id = ? AND group_id = ?
            """, (team_id, group_id))

        team = db.get_team(team_id)
        await query.message.reply_text(
            f"👑 *انتخاب ناجح!*\n\n"
            f"تهانينا للقائد الجديد لتيم *{team['team_name']}*: "
            f"*{winner_player['full_name'] if winner_player else 'القائد الجديد'}*!",
            parse_mode=ParseMode.MARKDOWN
        )
        await query.answer("✅ تم تسجيل صوتك!", show_alert=True)
    else:
        await query.answer(
            f"✅ تم تسجيل صوتك! ({votes[0]['cnt'] if votes else 1}/{total_members} صوت)",
            show_alert=True
        )
