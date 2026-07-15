from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import db
import keyboards as kb
from utils import post_to_channel

QTY_OPTIONS = [1, 2, 3, 5, 10]


async def order_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    categories = db.list_categories()
    if not categories:
        await q.edit_message_text(
            "🛒 *Order*\n\nNo products available right now — check back soon!",
            parse_mode="Markdown", reply_markup=kb.back_kb(),
        )
        return
    await q.edit_message_text("🛒 *Order*\n\nChoose a category:", parse_mode="Markdown",
                               reply_markup=kb.categories_kb(categories))


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    category = q.data.split(":", 1)[1]
    products = db.list_products(category)
    if not products:
        await q.edit_message_text("No products in this category right now.", reply_markup=kb.back_kb("menu:order"))
        return
    await q.edit_message_text(f"🛒 *{category}*\n\nSelect a product:", parse_mode="Markdown",
                               reply_markup=kb.products_kb(products, category))


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split(":", 1)[1])
    p = db.get_product(pid)
    if not p:
        await q.edit_message_text("Product not found.", reply_markup=kb.back_kb("menu:order"))
        return
    stock_note = ""
    if p["delivery_type"] == "auto":
        sc = db.stock_count(pid)
        stock_note = f"\n📦 In stock: {sc}" if sc else "\n📦 Out of stock"
    text = (
        f"*{p['name']}*\n\n"
        f"{p['description'] or ''}\n\n"
        f"💵 Price: ${p['price_usd']:.2f}{stock_note}"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.product_detail_kb(pid))


async def buy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split(":", 1)[1])
    p = db.get_product(pid)
    if not p:
        await q.edit_message_text("Product not found.", reply_markup=kb.back_kb("menu:order"))
        return
    if p["delivery_type"] == "auto" and db.stock_count(pid) == 0:
        await q.edit_message_text("😔 This item is currently out of stock.", reply_markup=kb.back_kb("menu:order"))
        return
    rows = [[InlineKeyboardButton(str(n), callback_data=f"qty:{pid}:{n}") for n in QTY_OPTIONS]]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"prod:{pid}")])
    await q.edit_message_text(f"How many *{p['name']}* would you like?", parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(rows))


async def choose_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, pid, qty = q.data.split(":")
    pid, qty = int(pid), int(qty)
    p = db.get_product(pid)
    if not p:
        await q.edit_message_text("Product not found.", reply_markup=kb.back_kb("menu:order"))
        return
    context.user_data["order_pid"] = pid
    context.user_data["order_qty"] = qty
    amount = p["price_usd"] * qty
    methods = db.list_payment_methods()
    text = (
        f"*{p['name']}* x{qty} = *${amount:.2f}*\n\n"
        "Choose a payment method:"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.payment_methods_kb(methods))


async def choose_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid = context.user_data.get("order_pid")
    qty = context.user_data.get("order_qty", 1)
    p = db.get_product(pid) if pid else None
    if not p:
        await q.edit_message_text("Session expired — please start again from Order.", reply_markup=kb.back_kb("menu:order"))
        return
    amount = p["price_usd"] * qty

    choice = q.data.split(":", 1)[1]
    if choice == "binance":
        method_name = "Binance Pay"
        payment_ref = db.get_setting("BINANCE_PAY_UID") or "Ask support for our Binance Pay UID"
        instructions = f"Send *${amount:.2f}* via *Binance Pay* to UID:\n`{payment_ref}`"
    elif choice == "wallet":
        method_name = "Telegram Wallet"
        contact = db.get_setting("WALLET_CONTACT") or db.get_setting("SUPPORT_USERNAME")
        payment_ref = f"@{contact}"
        instructions = f"Contact *@{contact}* directly via Telegram Wallet to pay *${amount:.2f}*."
    else:
        pm_id = int(choice)
        methods = {m["id"]: m for m in db.list_payment_methods()}
        m = methods.get(pm_id)
        if not m:
            await q.edit_message_text("That payment method is no longer available.", reply_markup=kb.back_kb("menu:order"))
            return
        method_name = m["network"]
        payment_ref = m["address"]
        instructions = f"Send *${amount:.2f}* worth via *{method_name}* to:\n`{payment_ref}`"

    order_id = db.create_order(update.effective_user.id, pid, qty, amount, method_name, payment_ref)
    context.user_data["awaiting_proof_order"] = order_id

    text = (
        f"🧾 *Order #{order_id} created*\n\n"
        f"{instructions}\n\n"
        "Once you've paid, reply here with a *screenshot* or the *transaction ID / hash* as proof. "
        "Our team will confirm and process your order."
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.cancel_kb())


async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("awaiting_proof_order")
    if not order_id:
        return  # not in a proof-submission flow, ignore
    order = db.get_order(order_id)
    if not order or order["status"] != "awaiting_confirmation":
        context.user_data.pop("awaiting_proof_order", None)
        return

    file_id = None
    proof_desc = ""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        proof_desc = "📷 screenshot attached"
    elif update.message.text:
        file_id = None
        proof_desc = f"🧾 ref: `{update.message.text.strip()}`"
        db.attach_proof(order_id, f"TEXT:{update.message.text.strip()}")
    if update.message.photo:
        db.attach_proof(order_id, file_id)

    context.user_data.pop("awaiting_proof_order", None)
    await update.message.reply_text(
        f"✅ Proof received for order #{order_id}. We'll confirm shortly — you'll get a message here once it's verified.",
    )

    user = update.effective_user
    product = db.get_product(order["product_id"])
    admin_text = (
        f"🆕 *Order #{order_id} — awaiting confirmation*\n\n"
        f"Buyer: {user.first_name} (@{user.username or 'no username'}, `{user.id}`)\n"
        f"Product: {product['name'] if product else '—'} x{order['quantity']}\n"
        f"Amount: ${order['amount_usd']:.2f}\n"
        f"Method: {order['payment_method']}\n"
        f"{proof_desc}"
    )
    reply_markup = kb.order_admin_kb(order_id)

    orders_channel = db.get_setting("ORDERS_CHANNEL_ID")
    if update.message.photo and orders_channel:
        try:
            await context.bot.send_photo(orders_channel, file_id, caption=admin_text, parse_mode="Markdown",
                                          reply_markup=reply_markup)
        except Exception as e:
            print(f"[warn] failed posting proof photo to orders channel: {e}")
    else:
        await post_to_channel(context.bot, orders_channel, admin_text, reply_markup=reply_markup)

    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            if update.message.photo:
                await context.bot.send_photo(admin_id, file_id, caption=admin_text, parse_mode="Markdown",
                                              reply_markup=reply_markup)
            else:
                await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            print(f"[warn] failed to DM admin {admin_id}: {e}")
