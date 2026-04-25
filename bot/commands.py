"""
bot/commands.py
Telegram command handlers: /start /setup /profile /status
"""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from db.profile import get_profile, save_profile
from coach.context_builder import build_quick_status
from coach.ai import get_coach_reply

# Conversation states for /setup
(
    SETUP_NAME,
    SETUP_AGE,
    SETUP_SPORTS,
    SETUP_PRIMARY,
    SETUP_DAYS,
    SETUP_HOURS,
    SETUP_GOAL_EVENT,
    SETUP_GOAL_DATE,
    SETUP_GOAL_TYPE,
    SETUP_GOAL_TIME,
    SETUP_EMAIL,
    SETUP_EXPERIENCE,
    SETUP_DONE,
) = range(13)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)
    if profile:
        await update.message.reply_text(
            f"Welcome back, {profile.name}! 👋\n\n"
            "Just talk to me — ask about your training, request plan changes, or check your status.\n\n"
            "Commands:\n/status — today's snapshot\n/profile — view/edit your profile\n/setup — redo onboarding"
        )
    else:
        await update.message.reply_text(
            "Hey! I'm your AI endurance coach. 🏃\n\n"
            "I connect to your Intervals.icu data and help you train smarter — "
            "planning sessions, adjusting for fatigue, and analysing your workouts.\n\n"
            "Let's get you set up. Type /setup to begin."
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)
    if not profile:
        await update.message.reply_text(
            "No profile found. Run /setup first."
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )
    status_text = await build_quick_status(user_id)
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    profile = get_profile(user_id)
    if not profile:
        await update.message.reply_text("No profile found. Run /setup first.")
        return

    text = (
        f"*Your Profile*\n\n"
        f"Name: {profile.name}\n"
        f"Age: {profile.age}\n"
        f"Sports: {', '.join(profile.sports or [])}\n"
        f"Primary sport: {profile.primary_sport}\n"
        f"Available days: {', '.join(profile.available_days or [])}\n"
        f"Hours/week: {profile.hours_per_week}\n"
        f"Goal: {profile.goal_event} on {profile.goal_date}\n"
        f"Goal type: {profile.goal_type}\n"
        f"Experience: {profile.experience_level}\n"
        f"Injuries: {', '.join(profile.current_injuries or []) or 'None'}\n"
        f"Limiters: {', '.join(profile.limiters or []) or 'None'}\n\n"
        "To update anything, just tell me — e.g. 'I hurt my left knee' or 'I can only train 4 days this week'."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── /setup conversational onboarding ──────────────────────────────────────────

async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Let's build your profile. I'll ask a few quick questions.\n\nWhat's your name?"
    )
    return SETUP_NAME


async def setup_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("How old are you?")
    return SETUP_AGE


async def setup_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["age"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a number.")
        return SETUP_AGE
    await update.message.reply_text(
        "What sports do you train? (e.g. running, cycling, swimming — separate with commas)"
    )
    return SETUP_SPORTS


async def setup_sports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sports = [s.strip().lower() for s in update.message.text.split(",")]
    context.user_data["sports"] = sports
    if len(sports) == 1:
        context.user_data["primary_sport"] = sports[0]
        await update.message.reply_text(
            "Which days are you typically available to train? (e.g. mon, tue, thu, sat)"
        )
        return SETUP_DAYS
    await update.message.reply_text(
        f"Which is your primary sport? ({', '.join(sports)})"
    )
    return SETUP_PRIMARY


async def setup_primary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["primary_sport"] = update.message.text.strip().lower()
    await update.message.reply_text(
        "Which days are you typically available to train? (e.g. mon, tue, thu, sat)"
    )
    return SETUP_DAYS


async def setup_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = [d.strip().lower()[:3] for d in update.message.text.split(",")]
    context.user_data["available_days"] = days
    await update.message.reply_text(
        "Max training hours per week? (just a number, e.g. 10)"
    )
    return SETUP_HOURS


async def setup_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["hours_per_week"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a number like 8 or 10.5.")
        return SETUP_HOURS
    await update.message.reply_text(
        "What's your main goal event? (e.g. Cape Town Marathon, or 'general fitness')"
    )
    return SETUP_GOAL_EVENT


async def setup_goal_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goal_event"] = update.message.text.strip()
    await update.message.reply_text(
        "When is it? (YYYY-MM-DD, or type 'none' if no date)"
    )
    return SETUP_GOAL_DATE


async def setup_goal_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["goal_date"] = None if val.lower() == "none" else val
    await update.message.reply_text(
        "What's your goal? (finish / time / podium)"
    )
    return SETUP_GOAL_TYPE


async def setup_goal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goal_type"] = update.message.text.strip().lower()
    await update.message.reply_text(
        "Target time? (e.g. 3:45:00 — or type 'none')"
    )
    return SETUP_GOAL_TIME


async def setup_goal_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["goal_time_target"] = None if val.lower() == "none" else val
    await update.message.reply_text(
        "Email address for post-workout analysis emails?"
    )
    return SETUP_EMAIL


async def setup_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text.strip()
    await update.message.reply_text(
        "Experience level? (beginner / intermediate / advanced)"
    )
    return SETUP_EXPERIENCE


async def setup_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    context.user_data["experience_level"] = update.message.text.strip().lower()
    context.user_data["telegram_id"] = user_id

    save_profile(user_id, context.user_data)

    name = context.user_data.get("name", "there")
    await update.message.reply_text(
        f"Profile saved, {name}! 🎉\n\n"
        "You're all set. Just talk to me naturally — ask anything about your training.\n\n"
        "Try: _'What should I do today?'_ or _'Plan my week'_",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Setup cancelled. Run /setup when you're ready.")
    return ConversationHandler.END

async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.session import clear_session
    clear_session(str(update.effective_user.id))
    await update.message.reply_text("Fresh start. What's up?")

def setup_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("setup", setup_start)],
        states={
            SETUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_name)],
            SETUP_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_age)],
            SETUP_SPORTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_sports)],
            SETUP_PRIMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_primary)],
            SETUP_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_days)],
            SETUP_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_hours)],
            SETUP_GOAL_EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_goal_event)],
            SETUP_GOAL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_goal_date)],
            SETUP_GOAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_goal_type)],
            SETUP_GOAL_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_goal_time)],
            SETUP_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_email)],
            SETUP_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_experience)],
        },
        fallbacks=[CommandHandler("cancel", setup_cancel)],
    )
