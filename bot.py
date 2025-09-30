import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from apscheduler.schedulers.background import BackgroundScheduler

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read bot token from Railway env
TOKEN = os.getenv("BOT_TOKEN")

# Store user data in memory (for demo, you may replace with DB later)
user_data = {}

# Languages
LANGS = {
    "en": {
        "start": "You started work at {time}",
        "end": "You finished work at {time}\n\nWork duration: {duration}\nBreaks total: {breaks}",
        "menu": [["Start Work", "End Work"], ["🍽️ Eat", "🚬 Smoke", "🚻 Toilet"], ["Reset", "Language"]],
        "choose_lang": "Choose your language:",
        "reset": "Your data has been reset ✅",
        "break": "Added {activity} ({minutes} min)"
    },
    "zh": {
        "start": "你在 {time} 开始上班",
        "end": "你在 {time} 下班\n\n工作时长: {duration}\n休息总时长: {breaks}",
        "menu": [["上班", "下班"], ["🍽️ 吃饭", "🚬 抽烟", "🚻 上厕所"], ["重置", "语言"]],
        "choose_lang": "选择语言：",
        "reset": "你的数据已重置 ✅",
        "break": "已添加 {activity} ({minutes} 分钟)"
    }
}

DEFAULT_LANG = "en"

# Scheduler
scheduler = BackgroundScheduler()
scheduler.start()


def format_duration(seconds):
    """Convert seconds to HH:MM"""
    return str(timedelta(seconds=seconds))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        user_data[uid] = {"lang": DEFAULT_LANG, "work_start": None, "breaks": 0}

    lang = user_data[uid]["lang"]
    kb = ReplyKeyboardMarkup(LANGS[lang]["menu"], resize_keyboard=True)

    await update.message.reply_text("Welcome! 🚀", reply_markup=kb)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text
    lang = user_data.get(uid, {}).get("lang", DEFAULT_LANG)

    # Start work
    if msg in ["Start Work", "上班"]:
        user_data[uid]["work_start"] = datetime.now()
        await update.message.reply_text(LANGS[lang]["start"].format(time=datetime.now().strftime("%H:%M")))
        return

    # End work
    if msg in ["End Work", "下班"]:
        start_time = user_data[uid].get("work_start")
        if start_time:
            duration = (datetime.now() - start_time).seconds
            breaks = user_data[uid]["breaks"]
            await update.message.reply_text(
                LANGS[lang]["end"].format(
                    time=datetime.now().strftime("%H:%M"),
                    duration=format_duration(duration),
                    breaks=format_duration(breaks)
                )
            )
            user_data[uid]["work_start"] = None
            user_data[uid]["breaks"] = 0
        return

    # Breaks
    if msg in ["🍽️ Eat", "🍽️ 吃饭"]:
        user_data[uid]["breaks"] += 1800  # 30min
        await update.message.reply_text(LANGS[lang]["break"].format(activity="🍽️", minutes=30))
        return

    if msg in ["🚬 Smoke", "🚬 抽烟"]:
        user_data[uid]["breaks"] += 600  # 10min
        await update.message.reply_text(LANGS[lang]["break"].format(activity="🚬", minutes=10))
        return

    if msg in ["🚻 Toilet", "🚻 上厕所"]:
        user_data[uid]["breaks"] += 300  # 5min
        await update.message.reply_text(LANGS[lang]["break"].format(activity="🚻", minutes=5))
        return

    # Reset
    if msg in ["Reset", "重置"]:
        user_data[uid] = {"lang": lang, "work_start": None, "breaks": 0}
        await update.message.reply_text(LANGS[lang]["reset"])
        return

    # Language
    if msg in ["Language", "语言"]:
        kb = [["English", "中文"]]
        await update.message.reply_text(LANGS[lang]["choose_lang"], reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    if msg in ["English", "中文"]:
        user_data[uid]["lang"] = "en" if msg == "English" else "zh"
        kb = ReplyKeyboardMarkup(LANGS[user_data[uid]["lang"]]["menu"], resize_keyboard=True)
        await update.message.reply_text("Language updated ✅", reply_markup=kb)


def reset_all_users():
    """Daily reset at midnight"""
    for uid in user_data:
        user_data[uid]["work_start"] = None
        user_data[uid]["breaks"] = 0
    logger.info("Daily reset done ✅")


def main():
    # Schedule daily reset at 00:00
    scheduler.add_job(reset_all_users, "cron", hour=0, minute=0)

    app = Application.builder().token(8466271055:AAFJHcvJ3WR2oAI7g1Xky2760qLgM68WXMM).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
