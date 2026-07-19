import html

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

import db
import keyboards as kb
from utils import is_admin, post_to_channel

# Conversation states
(ADD_NAME, ADD_CATEGORY, ADD_DESC, ADD_PRICE, ADD_DELIVERY, ADD_STOCK,
 PM_NETWORK, PM_ADDRESS, BROADCAST_TEXT, CHANNEL_VALUE, BULK_TEXT) = range(11)


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def _guard(update: Update) -> bool:
    return is_admin(update.effective_user.id)


async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        await q.edit_message_text("🚫 Admins only.", reply_markup=kb.back_kb())
        return
    await q.edit_message_text("🛠 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=kb.admin_home_kb())


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Admins only.")
        return
    await update.message.reply_text("🛠 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=kb.admin_home_kb())


# -- Add product --
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return ConversationHandler.END
    context.user_data["new_product"] = {}
    await q.edit_message_text("📝 Product name?", reply_markup=kb.cancel_kb())
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["name"] = update.message.text.strip()
    await update.message.reply_text("📂 Category? (e.g. Software, Subscriptions, Design Assets, Courses, Gaming, Social Media)")
    return ADD_CATEGORY


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["category"] = update.message.text.strip()
    await update.message.reply_text("🖊 Description?")
    return ADD_DESC


async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["description"] = update.message.text.strip()
    await update.message.reply_text("💵 Price in USD? (number only, e.g. 9.99)")
    return ADD_PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send a valid number, e.g. 9.99")
        return ADD_PRICE
    context.user_data["new_product"]["price"] = price
    rows = [[InlineKeyboardButton("⚡ Auto-delivery (stock of keys/codes)", callback_data="deliv:auto")],
            [InlineKeyboardButton("✋ Manual (admin delivers)", callback_data="deliv:manual")]]
    await update.message.reply_text("📦 Delivery type?", reply_markup=InlineKeyboardMarkup(rows))
    return ADD_DELIVERY


async def add_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    delivery = q.data.split(":", 1)[1]
    np = context.user_data["new_product"]
    np["delivery"] = delivery
    if delivery == "auto":
        await q.edit_message_text(
            "📥 Send the stock now — one license key/code per line "
            "(you can add more later from Manage Products)."
        )
        return ADD_STOCK
    return await _finalize_product(update, context)


async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [l.strip() for l in update.message.text.split("\n") if l.strip()]
    context.user_data["new_product"]["stock_lines"] = lines
    return await _finalize_product(update, context)


async def _finalize_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    np = context.user_data.pop("new_product")
    pid = db.add_product(np["name"], np["category"], np["description"], np["price"], np["delivery"])
    if np["delivery"] == "auto" and np.get("stock_lines"):
        db.add_stock(pid, np["stock_lines"])

    confirm_text = f"✅ Product added: <b>{esc(np['name'])}</b> — ${np['price']:.2f} ({esc(np['delivery'])})"
    if update.callback_query:
        await update.callback_query.edit_message_text(confirm_text, parse_mode="HTML", reply_markup=kb.admin_home_kb())
    else:
        await update.message.reply_text(confirm_text, parse_mode="HTML", reply_markup=kb.admin_home_kb())

    main_channel = db.get_setting("MAIN_CHANNEL_ID")
    await post_to_channel(
        context.bot, main_channel,
        f"🆕 <b>New Product Available!</b>\n\n<b>{esc(np['name'])}</b>\n{esc(np['description'])}\n\n💵 ${np['price']:.2f}",
    )
    return ConversationHandler.END


# -- Bulk add products --
BULK_FORMAT_HELP = (
    "📥 <b>Bulk Add Products</b>\n\n"
    "Send one product per line, fields separated by <code>|</code>:\n\n"
    "<code>Name|Category|Description|Price|auto or manual|stock keys (optional, ; separated)</code>\n\n"
    "Examples:\n"
    "<code>Netflix Premium 1mo|Subscriptions|Full HD, 1 screen|4.99|auto|KEY1;KEY2;KEY3</code>\n"
    "<code>Logo Design|Design Assets|Custom logo, 2 revisions|25|manual</code>\n\n"
    "The stock-keys field is only used for <b>auto</b> products — leave it out for <b>manual</b> ones. "
    "Send your list now (one message, one product per line)."
)


async def bulk_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return ConversationHandler.END
    await q.edit_message_text(BULK_FORMAT_HELP, parse_mode="HTML", reply_markup=kb.cancel_kb())
    return BULK_TEXT


async def bulk_add_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [l for l in update.message.text.split("\n") if l.strip()]
    added, errors = [], []
    for i, line in enumerate(lines, start=1):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            errors.append(f"Line {i}: expected at least 5 fields, got {len(parts)} — skipped")
            continue
        name, category, description, price_raw, delivery = parts[:5]
        stock_raw = parts[5] if len(parts) > 5 else ""
        delivery = delivery.lower().strip()
        if delivery not in ("auto", "manual"):
            errors.append(f"Line {i} ({name}): delivery must be 'auto' or 'manual' — skipped")
            continue
        try:
            price = float(price_raw.replace("$", "").strip())
        except ValueError:
            errors.append(f"Line {i} ({name}): invalid price '{price_raw}' — skipped")
            continue
        pid = db.add_product(name, category, description, price, delivery)
        if delivery == "auto" and stock_raw:
            keys = [k.strip() for k in stock_raw.split(";") if k.strip()]
            if keys:
                db.add_stock(pid, keys)
        added.append(name)

        main_channel = db.get_setting("MAIN_CHANNEL_ID")
        await post_to_channel(
            context.bot, main_channel,
            f"🆕 <b>New Product Available!</b>\n\n<b>{esc(name)}</b>\n{esc(description)}\n\n💵 ${price:.2f}",
        )

    summary = f"✅ Added {len(added)} product(s)."
    if added:
        summary += "\n" + "\n".join(f"• {esc(n)}" for n in added)
    if errors:
        summary += "\n\n⚠️ Issues:\n" + "\n".join(esc(e) for e in errors)
    await update.message.reply_text(summary, parse_mode="HTML", reply_markup=kb.admin_home_kb())
    return ConversationHandler.END


# -- Manage products (list + toggle active) --
async def list_products_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return
    products = db.list_products(active_only=False)
    if not products:
        await q.edit_message_text("No products yet.", reply_markup=kb.back_kb("admin:home"))
        return
    rows = []
    for p in products:
        label = f"{'🟢' if p['active'] else '🔴'} {p['name']} (${p['price_usd']:.2f})"
        rows.append([InlineKeyboardButton(label, callback_data=f"admtoggle:{p['id']}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:home")])
    await q.edit_message_text("📦 <b>Manage Products</b> — tap to toggle active/inactive:",
                               parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def toggle_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return
    pid = int(q.data.split(":", 1)[1])
    p = db.get_product(pid)
    db.set_product_active(pid, not p["active"])
    await list_products_admin(update, context)


# -- Payment methods --
async def payments_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return
    methods = db.list_payment_methods()
    lines = ["💳 <b>Payment Methods</b>\n"]
    for m in methods:
        lines.append(f"• {esc(m['network'])}: <code>{esc(m['address'])}</code>")
    if not methods:
        lines.append("<i>None added yet — buyers will only see Binance Pay / Telegram Wallet until you add at least one crypto network here.</i>")
    rows = [[InlineKeyboardButton("➕ Add Network/Address", callback_data="admin:add_payment")]]
    for m in methods:
        rows.append([InlineKeyboardButton(f"🗑 Remove {m['network']}", callback_data=f"admrmpm:{m['id']}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:home")])
    await q.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def add_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return ConversationHandler.END
    await q.edit_message_text("Network name? (e.g. USDT (TRC20), BTC, ETH (ERC20))", reply_markup=kb.cancel_kb())
    return PM_NETWORK


async def pm_network(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pm_network"] = update.message.text.strip()
    await update.message.reply_text("Wallet address for this network?")
    return PM_ADDRESS


async def pm_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    network = context.user_data.pop("pm_network")
    address = update.message.text.strip()
    db.add_payment_method(network, address)
    await update.message.reply_text(f"✅ Added {esc(network)}: <code>{esc(address)}</code>", parse_mode="HTML",
                                     reply_markup=kb.admin_home_kb())
    return ConversationHandler.END


async def remove_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return
    pm_id = int(q.data.split(":", 1)[1])
    db.remove_payment_method(pm_id)
    await payments_home(update, context)


# -- Pending orders --
async def pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return
    orders = db.list_pending_orders()
    if not orders:
        await q.edit_message_text("🧾 No orders awaiting confirmation.", reply_markup=kb.back_kb("admin:home"))
        return
    lines = ["🧾 <b>Pending Orders</b>\n"]
    for o in orders[:15]:
        prod = db.get_product(o["product_id"])
        code = o["order_code"] or f"#{o['id']}"
        lines.append(f"{esc(code)} — {esc(prod['name']) if prod else '?'} x{o['quantity']} — ${o['amount_usd']:.2f} — {esc(o['payment_method'])}")
    lines.append("\nUse the Confirm/Reject buttons sent to your DM for each order.")
    await q.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=kb.back_kb("admin:home"))


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not _guard(update):
        await q.answer("Admins only.", show_alert=True)
        return
    order_id = int(q.data.split(":", 1)[1])
    order = db.get_order(order_id)
    if not order or order["status"] != "awaiting_confirmation":
        await q.answer("Already processed.", show_alert=True)
        return
    await q.answer("Confirming...")
    code = order["order_code"] or f"#{order_id}"
    db.set_order_status(order_id, "paid")
    product = db.get_product(order["product_id"])
    buyer_id = order["user_id"]

    if product and product["delivery_type"] == "auto":
        delivered_items = []
        for _ in range(order["quantity"]):
            item = db.pop_stock_item(product["id"])
            if item:
                delivered_items.append(item)
        if delivered_items:
            db.set_order_status(order_id, "delivered")
            try:
                await context.bot.send_message(
                    buyer_id,
                    f"✅ <b>Order {esc(code)} confirmed!</b>\n\n" + "\n".join(f"<code>{esc(i)}</code>" for i in delivered_items),
                    parse_mode="HTML",
                )
            except Exception:
                pass
            await _post_testimonial(context, code, order, product, success=True)
        else:
            try:
                await context.bot.send_message(
                    buyer_id,
                    f"✅ Payment for order {esc(code)} confirmed, but we're temporarily out of stock — "
                    "our team will deliver it manually shortly.",
                    parse_mode="HTML",
                )
            except Exception:
                pass
    else:
        try:
            await context.bot.send_message(
                buyer_id,
                f"✅ Payment for order {esc(code)} confirmed! Our team will deliver your item shortly.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    try:
        if product and product["delivery_type"] == "manual":
            await q.edit_message_reply_markup(
                InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirmed — Mark Delivered", callback_data=f"admdeliv:{order_id}")]])
            )
        else:
            await q.edit_message_reply_markup(None)
    except Exception:
        pass


async def mark_delivered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not _guard(update):
        await q.answer("Admins only.", show_alert=True)
        return
    order_id = int(q.data.split(":", 1)[1])
    order = db.get_order(order_id)
    if not order:
        await q.answer("Not found.", show_alert=True)
        return
    code = order["order_code"] or f"#{order_id}"
    db.set_order_status(order_id, "delivered")
    product = db.get_product(order["product_id"])
    await q.answer("Marked delivered.")
    try:
        await q.edit_message_reply_markup(None)
    except Exception:
        pass
    await _post_testimonial(context, code, order, product, success=True)


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not _guard(update):
        await q.answer("Admins only.", show_alert=True)
        return
    order_id = int(q.data.split(":", 1)[1])
    order = db.get_order(order_id)
    if not order or order["status"] != "awaiting_confirmation":
        await q.answer("Already processed.", show_alert=True)
        return
    code = order["order_code"] or f"#{order_id}"
    db.set_order_status(order_id, "rejected")
    await q.answer("Rejected.")
    try:
        await q.edit_message_reply_markup(None)
    except Exception:
        pass
    try:
        await context.bot.send_message(
            order["user_id"],
            f"❌ Order {esc(code)} could not be confirmed — payment not verified. "
            f"Contact support (@{esc(db.get_setting('SUPPORT_USERNAME'))}) if you believe this is a mistake.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    product = db.get_product(order["product_id"])
    await _post_testimonial(context, code, order, product, success=False)


async def _post_testimonial(context, code, order, product, success: bool):
    channel = db.get_setting("TESTIMONIALS_CHANNEL_ID") or db.get_setting("PROOFS_CHANNEL_ID") or db.get_setting("ORDERS_CHANNEL_ID")
    if success:
        text = (
            f"✅ <b>Order {esc(code)} — Successful</b>\n"
            f"Product: {esc(product['name']) if product else '—'}\n"
            f"Amount: ${order['amount_usd']:.2f}\n"
            "Delivered and confirmed. 🎉"
        )
    else:
        text = (
            f"❌ <b>Order {esc(code)} — Failed / Unverified Payment</b>\n"
            f"Product: {esc(product['name']) if product else '—'}"
        )
    await post_to_channel(context.bot, channel, text)


# -- Broadcast --
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return ConversationHandler.END
    await q.edit_message_text("📣 Send the broadcast message text now.", reply_markup=kb.cancel_kb())
    return BROADCAST_TEXT


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    with db.get_db() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    sent = 0
    for r in rows:
        try:
            await context.bot.send_message(r["user_id"], text)
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users.", reply_markup=kb.admin_home_kb())
    return ConversationHandler.END


# -- Stats --
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return
    text = (
        "📊 <b>Stats</b>\n\n"
        f"Users: {db.total_users()}\n"
        f"Orders: {db.total_orders()}\n"
        f"Pending: {len(db.list_pending_orders())}\n"
        f"Revenue (delivered): ${db.total_revenue():.2f}"
    )
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb.back_kb("admin:home"))


# -- Channel settings --
CHANNEL_KEYS = {
    "main_id": "MAIN_CHANNEL_ID", "main_link": "MAIN_CHANNEL_LINK",
    "orders_id": "ORDERS_CHANNEL_ID", "orders_link": "ORDERS_CHANNEL_LINK",
    "proofs_id": "PROOFS_CHANNEL_ID", "proofs_link": "PROOFS_CHANNEL_LINK",
    "testi_id": "TESTIMONIALS_CHANNEL_ID", "testi_link": "TESTIMONIALS_CHANNEL_LINK",
    "support": "SUPPORT_USERNAME", "binance": "BINANCE_PAY_UID", "wallet": "WALLET_CONTACT",
}


async def channels_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return
    lines = ["🔗 <b>Channel & Payment Contact Settings</b>\n"]
    rows = []
    for short, key in CHANNEL_KEYS.items():
        val = db.get_setting(key) or "—"
        lines.append(f"<code>{esc(key)}</code>: {esc(val)}")
        rows.append([InlineKeyboardButton(f"✏️ {key}", callback_data=f"admsetch:{short}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:home")])
    await q.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def set_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _guard(update):
        return ConversationHandler.END
    short = q.data.split(":", 1)[1]
    key = CHANNEL_KEYS[short]
    context.user_data["editing_setting"] = key
    await q.edit_message_text(f"Send the new value for <code>{esc(key)}</code>:", parse_mode="HTML", reply_markup=kb.cancel_kb())
    return CHANNEL_VALUE


async def set_channel_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.pop("editing_setting", None)
    if not key:
        return ConversationHandler.END
    db.set_setting(key, update.message.text.strip())
    await update.message.reply_text(f"✅ <code>{esc(key)}</code> updated.", parse_mode="HTML", reply_markup=kb.admin_home_kb())
    return ConversationHandler.END


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        from handlers.start import show_home
        await show_home(update, context)
    return ConversationHandler.END
