import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -----------------------
# 数据存储
# -----------------------
user_data = {}
DEFAULT_LANG = "zh"
langs = ["zh", "en", "km"]

# 三语言字典
texts = {
    "menu": {
        "zh": [["上班", "下班"], ["吃饭", "上厕所", "抽烟"], ["回座"], ["📊 今日统计"]],
        "en": [["Work", "Off Work"], ["Eat", "Toilet", "Smoke"], ["Back"], ["📊 Daily Summary"]],
        "km": [["ចូលការងារ", "ចេញការងារ"], ["បាយ", "បន្ទប់ទឹក", "ជក់បារី"], ["ត្រឡប់តុ"], ["📊 សរុបប្រចាំថ្ងៃ"]]
    },
    "start": {
        "zh": "✅ 打卡机器人已启动！请选择操作:",
        "en": "✅ Check-in bot started! Please choose an action:",
        "km": "✅ បូតបានចាប់ផ្តើម! សូមជ្រើសរើសសកម្មភាព:"
    },
    "back_hint": {
        "zh": "提示：本次活动时间已结算",
        "en": "Hint: This activity's time has been settled.",
        "km": "សេចក្តីជូនដំណឹង៖ ពេលវេលានៃសកម្មភាពនេះត្រូវបានបញ្ចប់"
    }
}

# -----------------------
# 工具函数
# -----------------------
def get_lang(uid):
    return user_data.get(uid, {}).get("lang", DEFAULT_LANG)

def init_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "counts": {"eat": 0, "toilet": 0, "smoke": 0, "work": 0},
            "time": {"eat": timedelta(0), "toilet": timedelta(0), "smoke": timedelta(0), "work": timedelta(0)},
            "start": {},
            "lang": DEFAULT_LANG
        }

def format_time(td: timedelta):
    total_seconds = int(td.total_seconds())
    h, m, s = total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

# -----------------------
# 菜单
# -----------------------
def get_menu(lang):
    return ReplyKeyboardMarkup(texts["menu"][lang], resize_keyboard=True)

# -----------------------
# 命令
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    init_user(uid)
    lang = get_lang(uid)
    await update.message.reply_text(texts["start"][lang], reply_markup=get_menu(lang))

async def lang_zh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    init_user(uid)
    user_data[uid]["lang"] = "zh"
    await update.message.reply_text("✅ 已切换到中文", reply_markup=get_menu("zh"))

async def lang_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    init_user(uid)
    user_data[uid]["lang"] = "en"
    await update.message.reply_text("✅ Switched to English", reply_markup=get_menu("en"))

async def lang_km(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    init_user(uid)
    user_data[uid]["lang"] = "km"
    await update.message.reply_text("✅ បានប្ដូរទៅជាភាសាខ្មែរ", reply_markup=get_menu("km"))

# -----------------------
# 消息处理
# -----------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    init_user(uid)
    lang = get_lang(uid)
    text = update.message.text

    now = datetime.now().strftime("%m/%d %H:%M:%S")

    if text in ["上班", "Work", "ចូលការងារ"]:
        user_data[uid]["start"]["work"] = datetime.now()
        user_data[uid]["counts"]["work"] += 1
        await update.message.reply_text(f"用户：{name}\n用户标识：{uid}\n✅ 打卡成功：上班 - {now}\n提示：请记得下班时打卡下班")

    elif text in ["下班", "Off Work", "ចេញការងារ"]:
        if "work" in user_data[uid]["start"]:
            start_time = user_data[uid]["start"].pop("work")
            duration = datetime.now() - start_time
            user_data[uid]["time"]["work"] += duration
            total_acts = user_data[uid]["time"]["eat"] + user_data[uid]["time"]["toilet"] + user_data[uid]["time"]["smoke"]
            reply = (
                f"用户：{name}\n用户标识：{uid}\n"
                f"✅ 打卡成功：下班 - {now}\n"
                f"提示：今日工作时长已结算。\n"
                f"总工作时长：{format_time(user_data[uid]['time']['work'])}\n"
                f"总活动时长（吃饭+上厕所+抽烟）：{format_time(total_acts)}"
            )
            await update.message.reply_text(reply)

    elif text in ["吃饭", "Eat", "បាយ"]:
        user_data[uid]["start"]["eat"] = datetime.now()
        user_data[uid]["counts"]["eat"] += 1
        await update.message.reply_text(f"用户：{name}\n用户标识：{uid}\n✅ 打卡成功：吃饭 - {now}\n注意：这是您第 {user_data[uid]['counts']['eat']} 次吃饭\n提示：活动完成后请及时打卡回座")

    elif text in ["上厕所", "Toilet", "បន្ទប់ទឹក"]:
        user_data[uid]["start"]["toilet"] = datetime.now()
        user_data[uid]["counts"]["toilet"] += 1
        await update.message.reply_text(f"用户：{name}\n用户标识：{uid}\n✅ 打卡成功：上厕所 - {now}\n提示：活动完成后请及时打卡回座")

    elif text in ["抽烟", "Smoke", "ជក់បារី"]:
        user_data[uid]["start"]["smoke"] = datetime.now()
        user_data[uid]["counts"]["smoke"] += 1
        await update.message.reply_text(f"用户：{name}\n用户标识：{uid}\n✅ 打卡成功：抽烟 - {now}\n提示：活动完成后请及时打卡回座")

    elif text in ["回座", "Back", "ត្រឡប់តុ"]:
        # 计算最后一次活动
        if user_data[uid]["start"]:
            act, stime = user_data[uid]["start"].popitem()
            duration = datetime.now() - stime
            user_data[uid]["time"][act] += duration
            total_time = sum(user_data[uid]["time"].values(), timedelta())
            reply = (
                f"用户：{name}\n用户标识：{uid}\n✅ {now} 回座打卡成功：{act}\n"
                f"{texts['back_hint'][lang]}\n本次活动耗时：{format_time(duration)}\n"
                f"今日累计{act}时间：{format_time(user_data[uid]['time'][act])}\n"
                f"今日累计活动总时间：{format_time(total_time)}\n"
                f"------------------------\n本日吃饭：{user_data[uid]['counts']['eat']} 次\n本日上厕所：{user_data[uid]['counts']['toilet']} 次\n本日抽烟：{user_data[uid]['counts']['smoke']} 次"
            )
            await update.message.reply_text(reply)

    elif text in ["📊 今日统计", "📊 Daily Summary", "📊 សរុបប្រចាំថ្ងៃ"]:
        total_time = sum(user_data[uid]["time"].values(), timedelta())
        reply = (
            f"用户：{name}\n用户标识：{uid}\n"
            f"🍽 吃饭 {user_data[uid]['counts']['eat']} 次 ({format_time(user_data[uid]['time']['eat'])})\n"
            f"🚽 上厕所 {user_data[uid]['counts']['toilet']} 次 ({format_time(user_data[uid]['time']['toilet'])})\n"
            f"🚬 抽烟 {user_data[uid]['counts']['smoke']} 次 ({format_time(user_data[uid]['time']['smoke'])})\n"
            f"💼 工作 {user_data[uid]['counts']['work']} 次 ({format_time(user_data[uid]['time']['work'])})\n"
            f"📊 总活动时间：{format_time(total_time)}"
        )
        await update.message.reply_text(reply)

# -----------------------
# 自动清零
# -----------------------
def reset_daily():
    for uid in user_data:
        user_data[uid]["counts"] = {"eat": 0, "toilet": 0, "smoke": 0, "work": 0}
        user_data[uid]["time"] = {"eat": timedelta(0), "toilet": timedelta(0), "smoke": timedelta(0), "work": timedelta(0)}
        user_data[uid]["start"] = {}
    logging.info("✅ 每日数据已清零 (15:00)")

# -----------------------
# 主函数
# -----------------------
def main():
    app = Application.builder().token("8466271055:AAFJHcvJ3WR2oAI7g1Xky2760qLgM68WXMM").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("zh", lang_zh))
    app.add_handler(CommandHandler("en", lang_en))
    app.add_handler(CommandHandler("km", lang_km))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # APScheduler 定时任务
    scheduler = AsyncIOScheduler()
    scheduler.add_job(reset_daily, CronTrigger(hour=15, minute=0))
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()
