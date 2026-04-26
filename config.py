"""
إعدادات البوت
"""
import os

# ══════════════════════════════════════════
#  🔑 توكن البوت - ضعه في متغيرات البيئة
# ══════════════════════════════════════════
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ══════════════════════════════════════════
#  ⚙️ إعدادات اللعبة
# ══════════════════════════════════════════

# الحد الأقصى لأعضاء كل تيم
MAX_TEAM_MEMBERS = 10

# مكافأة العمل (ذهب)
WORK_REWARD_MIN = 50
WORK_REWARD_MAX = 200

# وقت الكولداون للعمل (ثانية) - 5 دقائق
WORK_COOLDOWN = 300

# وقت الكولداون للهجوم (ثانية) - 10 دقائق
ATTACK_COOLDOWN = 600

# الحد الأدنى للخزينة للهجوم
ATTACK_MIN_TREASURY = 100

# سرقة نسبة من خزينة الضحية
ATTACK_STEAL_PERCENT = 0.15  # 15%

# عدد الأصوات المطلوبة لانتخاب القائد
MIN_VOTES_FOR_LEADER = 2

# الحد الأدنى للتصويت بالنسبة المئوية
MIN_VOTE_PERCENT = 0.51  # 51%

# ══════════════════════════════════════════
#  🏆 إعدادات المزاد
# ══════════════════════════════════════════

# مدة المزاد (ثانية) - 3 دقائق
AUCTION_DURATION = 180

# الحد الأدنى لزيادة المزايدة
AUCTION_MIN_INCREMENT = 10

# قائمة أنواع الجوائز في المزاد
AUCTION_ITEMS = [
    {"name": "⚔️ سيف الأبطال", "description": "يضاعف أرباح الهجوم لـ 24 ساعة", "base_price": 500, "type": "attack_boost"},
    {"name": "🛡️ درع الحصن", "description": "يمنع الهجوم على تيمك لـ 12 ساعة", "base_price": 400, "type": "defense_shield"},
    {"name": "💰 صندوق الكنز", "description": "يضاعف أرباح العمل لـ 6 ساعات", "base_price": 300, "type": "work_boost"},
    {"name": "🗡️ خنجر الظل", "description": "يزيد نسبة السرقة إلى 30%", "base_price": 600, "type": "steal_boost"},
    {"name": "🧪 إكسير القوة", "description": "يمنح 500 ذهب فوري للتيم", "base_price": 200, "type": "gold_pack"},
    {"name": "👑 تاج الملك", "description": "يمنح نقاط شرف مضاعفة لـ 24 ساعة", "base_price": 800, "type": "honor_boost"},
    {"name": "🔮 كريستال السحر", "description": "يعطي القائد حق نقل 50% من خزينة التيم", "base_price": 700, "type": "transfer_power"},
    {"name": "🏹 قوس النسر", "description": "يسمح بمهاجمة 3 تيمات في نفس الوقت", "base_price": 550, "type": "multi_attack"},
]

# ══════════════════════════════════════════
#  📊 نقاط الشرف
# ══════════════════════════════════════════
HONOR_PER_WORK = 1
HONOR_PER_WIN = 10
HONOR_PER_AUCTION_WIN = 5
