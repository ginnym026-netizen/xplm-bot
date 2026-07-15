from telegram import Update
from telegram.ext import ContextTypes

import db
import keyboards as kb
from utils import uptime_str, is_admin


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    categories = db.list_categories()
    if not categories:
        await q.edit_message_text(
            "📊 *Product Dashboard*\n\nNo products listed yet — check back soon!",
            parse_mode="Markdown", reply_markup=kb.back_kb(),
        )
        return
    lines = ["📊 *Product Dashboard*\n"]
    for c in categories:
        prods = db.list_products(c)
        lines.append(f"\n*{c}*")
        for p in prods:
            stock_note = ""
            if p["delivery_type"] == "auto":
                sc = db.stock_count(p["id"])
                stock_note = f"  ({sc} in stock)" if sc else "  (out of stock)"
            lines.append(f"• {p['name']} — ${p['price_usd']:.2f}{stock_note}")
    lines.append("\nTap *Order* from the main menu to buy.")
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb.back_kb())


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = db.get_user(update.effective_user.id)
    ref_count = db.count_referrals(user["user_id"])
    text = (
        "👤 *My Profile*\n\n"
        f"ID: `{user['user_id']}`\n"
        f"Username: @{user['username'] or 'N/A'}\n"
        f"Referral code: `{user['referral_code']}`\n"
        f"Referrals made: {ref_count}\n"
        f"Orders placed: {len(db.list_user_orders(user['user_id']))}"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = db.get_user(update.effective_user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    ref_count = db.count_referrals(user["user_id"])
    text = (
        "🎁 *Referral Program*\n\n"
        "Share your link below — everyone who joins through it counts toward your referrals.\n\n"
        f"🔗 `{link}`\n\n"
        f"👥 Referrals so far: *{ref_count}*"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    support_user = db.get_setting("SUPPORT_USERNAME")
    text = (
        "🎧 *Support*\n\n"
        f"Need help with an order or have a question? Message @{support_user} directly.\n\n"
        "Please include your Order ID (see Order History) if your question is about a specific purchase."
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        "⚙️ *Settings*\n\n"
        "• Notifications: on by default for order updates\n"
        "• To change your linked username, update it in Telegram settings\n"
        "• Contact support to request account changes"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        "🤖 *Bot Status*\n\n"
        "Status: 🟢 Online\n"
        f"Uptime: {uptime_str()}\n"
        f"Total users: {db.total_users()}\n"
        f"Total orders: {db.total_orders()}"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    orders = db.list_user_orders(update.effective_user.id)
    if not orders:
        await q.edit_message_text("📜 *Order History*\n\nNo orders yet.", parse_mode="Markdown", reply_markup=kb.back_kb())
        return
    status_emoji = {
        "pending_payment": "⏳", "awaiting_confirmation": "🕵️",
        "paid": "💰", "delivered": "✅", "cancelled": "❌", "rejected": "❌",
    }
    lines = ["📜 *Order History*\n"]
    for o in orders[:20]:
        prod = db.get_product(o["product_id"])
        name = prod["name"] if prod else "Unknown product"
        emoji = status_emoji.get(o["status"], "•")
        lines.append(f"{emoji} #{o['id']} — {name} — ${o['amount_usd']:.2f} — _{o['status']}_")
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb.back_kb())
