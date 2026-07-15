from telegram import Update
from telegram.ext import ContextTypes

import db
import keyboards as kb
from utils import user_passes_gate, is_admin

WELCOME = (
    "👋 *Welcome to XPLM Ai STORE*\n\n"
    "Software licenses • Subscriptions • Design assets • Courses • Gaming items • Social media services\n\n"
    "Use the menu below to browse products, place an order, or check your profile."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_code = None
    if context.args:
        ref_code = context.args[0]

    referred_by = None
    if ref_code:
        ref_user = db.get_user_by_ref_code(ref_code)
        if ref_user and ref_user["user_id"] != user.id:
            referred_by = ref_user["user_id"]

    existing = db.get_user(user.id)
    db.get_or_create_user(user.id, user.username or "", user.first_name or "", referred_by)

    if not existing and referred_by:
        try:
            await context.bot.send_message(
                referred_by,
                f"🎉 *{user.first_name}* just joined using your referral link!",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    await show_home(update, context)


async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    passed = await user_passes_gate(context.bot, user.id)

    if not passed:
        text = (
            "🔒 *One quick step first*\n\n"
            "To use XPLM Ai STORE you need to join our main channel and our proofs channel "
            "(this keeps the store trustworthy for everyone).\n\n"
            "Tap both buttons below, then hit *Continue*."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.join_gate_kb())
        else:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb.join_gate_kb())
        return

    markup = kb.main_menu_kb(is_admin(user.id))
    if update.callback_query:
        await update.callback_query.edit_message_text(WELCOME, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=markup)


async def home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await show_home(update, context)
