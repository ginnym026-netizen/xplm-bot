import html

from telegram import Update
from telegram.ext import ContextTypes

import db
import keyboards as kb
from utils import uptime_str, is_admin


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


STATUS_LABELS = {
    "pending_payment": "⏳ Awaiting payment",
    "awaiting_confirmation": "🕵️ Awaiting confirmation",
    "paid": "💰 Paid",
    "delivered": "✅ Delivered",
    "cancelled": "❌ Cancelled",
    "rejected": "❌ Rejected",
}


def _dashboard_text():
    categories = db.list_categories()
    if not categories:
        return "📊 <b>Product Dashboard</b>\n\nNo products listed yet — check back soon!"
    lines = ["📊 <b>Product Dashboard</b>\n"]
    for c in categories:
        prods = db.list_products(c)
        lines.append(f"\n<b>{esc(c)}</b>")
        for p in prods:
            stock_note = ""
            if p["delivery_type"] == "auto":
                sc = db.stock_count(p["id"])
                stock_note = f"  ({sc} in stock)" if sc else "  (out of stock)"
            lines.append(f"• {esc(p['name'])} — ${p['price_usd']:.2f}{stock_note}")
    lines.append("\nTap <b>Order</b> from the main menu to buy.")
    return "\n".join(lines)


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(_dashboard_text(), parse_mode="HTML", reply_markup=kb.back_kb())


async def dashboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_dashboard_text(), parse_mode="HTML", reply_markup=kb.back_kb())


def _profile_text(user_id: int):
    user = db.get_user(user_id)
    ref_count = db.count_referrals(user["user_id"])
    return (
        "👤 <b>My Profile</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Username: @{esc(user['username'] or 'N/A')}\n"
        f"Referral code: <code>{esc(user['referral_code'])}</code>\n"
        f"Referrals made: {ref_count}\n"
        f"Orders placed: {len(db.list_user_orders(user['user_id']))}"
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(_profile_text(update.effective_user.id), parse_mode="HTML", reply_markup=kb.back_kb())


async def _referral_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_or_create_user(update.effective_user.id, update.effective_user.username or "",
                                  update.effective_user.first_name or "")
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    ref_count = db.count_referrals(user["user_id"])
    return (
        "🎁 <b>Referral Program</b>\n\n"
        "Share your link below — everyone who joins through it counts toward your referrals.\n\n"
        f"🔗 <code>{esc(link)}</code>\n\n"
        f"👥 Referrals so far: <b>{ref_count}</b>"
    )


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = await _referral_text(update, context)
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb.back_kb())


async def referral_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await _referral_text(update, context)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb.back_kb())


def _support_text():
    support_user = db.get_setting("SUPPORT_USERNAME")
    return (
        "🎧 <b>Support</b>\n\n"
        f"Need help with an order or have a question? Message @{esc(support_user)} directly.\n\n"
        "Please include your Order ID (see Order History) if your question is about a specific purchase."
    )


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(_support_text(), parse_mode="HTML", reply_markup=kb.back_kb())


async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_support_text(), parse_mode="HTML", reply_markup=kb.back_kb())


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        "⚙️ <b>Settings</b>\n\n"
        "• Notifications: on by default for order updates\n"
        "• To change your linked username, update it in Telegram settings\n"
        "• Contact support to request account changes"
    )
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb.back_kb())


def _status_text():
    return (
        "🤖 <b>Bot Status</b>\n\n"
        "Status: 🟢 Online\n"
        f"Uptime: {uptime_str()}\n"
        f"Total users: {db.total_users()}\n"
        f"Total orders: {db.total_orders()}"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(_status_text(), parse_mode="HTML", reply_markup=kb.back_kb())


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_status_text(), parse_mode="HTML", reply_markup=kb.back_kb())


def _history_text(user_id: int):
    orders = db.list_user_orders(user_id)
    if not orders:
        return "📜 <b>Order History</b>\n\nNo orders yet."
    lines = ["📜 <b>Order History</b>\n"]
    for o in orders[:20]:
        prod = db.get_product(o["product_id"])
        name = prod["name"] if prod else "Unknown product"
        label = STATUS_LABELS.get(o["status"], o["status"])
        code = o["order_code"] or f"#{o['id']}"
        lines.append(f"{esc(code)} — {esc(name)} — ${o['amount_usd']:.2f} — {label}")
    return "\n".join(lines)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(_history_text(update.effective_user.id), parse_mode="HTML", reply_markup=kb.back_kb())


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_history_text(update.effective_user.id), parse_mode="HTML", reply_markup=kb.back_kb())
