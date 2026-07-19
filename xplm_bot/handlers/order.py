import asyncio
import html

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import db
import keyboards as kb
from utils import post_to_channel

QTY_OPTIONS = [1, 2, 3, 5, 10]


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


async def order_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    categories = db.list_categories()
    if not categories:
        await q.edit_message_text(
            "🛒 <b>Order</b>\n\nNo products available right now — check back soon!",
            parse_mode="HTML", reply_markup=kb.back_kb(),
        )
        return
    await q.edit_message_text("🛒 <b>Order</b>\n\nChoose a category:", parse_mode="HTML",
                               reply_markup=kb.categories_kb(categories))


async def order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = db.list_categories()
    if not categories:
        await update.message.reply_text(
            "🛒 <b>Order</b>\n\nNo products available right now — check back soon!",
            parse_mode="HTML", reply_markup=kb.back_kb(),
        )
        return
    await update.message.reply_text("🛒 <b>Order</b>\n\nChoose a category:", parse_mode="HTML",
                                     reply_markup=kb.categories_kb(categories))


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    category = q.data.split(":", 1)[1]
    products = db.list_products(category)
    if not products:
        await q.edit_message_text("No products in this category right now.", reply_markup=kb.back_kb("menu:order"))
        return
    await q.edit_message_text(f"🛒 <b>{esc(category)}</b>\n\nSelect a product:", parse_mode="HTML",
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
        f"<b>{esc(p['name'])}</b>\n\n"
        f"{esc(p['description'] or '')}\n\n"
        f"💵 Price: ${p['price_usd']:.2f}{stock_note}"
    )
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb.product_detail_kb(pid))


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
    await q.edit_message_text(f"How many <b>{esc(p['name'])}</b> would you like?", parse_mode="HTML",
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
    if not methods:
        note = "\n\n⚠️ No crypto addresses are configured yet — use Binance Pay or Telegram Wallet below, or contact support."
    else:
        note = ""
    text = f"<b>{esc(p['name'])}</b> x{qty} = <b>${amount:.2f}</b>{note}\n\nChoose a payment method:"
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb.payment_methods_kb(methods, pid))


async def qty_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return from the payment-instructions screen back to the payment-method list."""
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split(":", 1)[1])
    p = db.get_product(pid)
    if not p:
        await q.edit_message_text("Product not found.", reply_markup=kb.back_kb("menu:order"))
        return
    qty = context.user_data.get("order_qty", 1)
    amount = p["price_usd"] * qty
    methods = db.list_payment_methods()
    text = f"<b>{esc(p['name'])}</b> x{qty} = <b>${amount:.2f}</b>\n\nChoose a payment method:"
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb.payment_methods_kb(methods, pid))


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
        ref = db.get_setting("BINANCE_PAY_UID")
        if not ref:
            await q.edit_message_text("Binance Pay isn't configured yet — please choose another method or contact support.",
                                       reply_markup=kb.payment_methods_kb(db.list_payment_methods(), pid), parse_mode="HTML")
            return
        instructions = f"Send <b>${amount:.2f}</b> via <b>Binance Pay</b> to UID:\n<code>{esc(ref)}</code>"
    elif choice == "wallet":
        method_name = "Telegram Wallet"
        contact = db.get_setting("WALLET_CONTACT") or db.get_setting("SUPPORT_USERNAME")
        if not contact:
            await q.edit_message_text("Wallet contact isn't configured yet — please choose another method or contact support.",
                                       reply_markup=kb.payment_methods_kb(db.list_payment_methods(), pid), parse_mode="HTML")
            return
        ref = f"@{contact}"
        instructions = f"Contact <b>@{esc(contact)}</b> directly via Telegram Wallet to pay <b>${amount:.2f}</b>."
    else:
        pm_id = int(choice)
        methods = {m["id"]: m for m in db.list_payment_methods()}
        m = methods.get(pm_id)
        if not m:
            await q.edit_message_text("That payment method is no longer available.", reply_markup=kb.back_kb("menu:order"))
            return
        method_name = m["network"]
        ref = m["address"]
        instructions = f"Send <b>${amount:.2f}</b> worth via <b>{esc(method_name)}</b> to:\n<code>{esc(ref)}</code>"

    order = db.create_order(update.effective_user.id, pid, qty, amount, method_name, ref)
    order_id, code = order["id"], order["order_code"]
    context.user_data["awaiting_proof_order"] = order_id

    text = (
        f"🧾 <b>Order {esc(code)} created</b>\n\n"
        f"{instructions}\n\n"
        "Once you've paid, reply here with a <b>screenshot</b> or the <b>transaction ID / hash</b> as proof. "
        "Our team will confirm and process your order."
    )
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb.payment_instructions_kb(pid))

    orders_channel = db.get_setting("ORDERS_CHANNEL_ID")
    await post_to_channel(
        context.bot, orders_channel,
        f"🆕 Order {esc(code)} created — awaiting payment via {esc(method_name)}.",
    )


async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("awaiting_proof_order")
    if not order_id:
        return  # not in a proof-submission flow, ignore
    order = db.get_order(order_id)
    if not order or order["status"] != "pending_payment":
        context.user_data.pop("awaiting_proof_order", None)
        return

    code = order["order_code"] or f"#{order_id}"
    file_id = None
    proof_desc = ""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        proof_desc = "📷 screenshot attached"
        db.attach_proof(order_id, file_id)
    elif update.message.text:
        proof_desc = f"🧾 ref: <code>{esc(update.message.text.strip())}</code>"
        db.attach_proof(order_id, f"TEXT:{update.message.text.strip()}")
    else:
        return

    db.set_order_status(order_id, "awaiting_confirmation")
    context.user_data.pop("awaiting_proof_order", None)

    # -- "processing" feedback for the buyer --
    processing = await update.message.reply_text("⏳ Processing your proof...")
    for frame in ("▰▰▱▱▱ 40%", "▰▰▰▰▱ 80%", "▰▰▰▰▰ 100%"):
        await asyncio.sleep(0.5)
        try:
            await processing.edit_text(f"⏳ Processing your proof...\n{frame}")
        except Exception:
            pass
    try:
        await processing.edit_text(
            f"✅ <b>Order {esc(code)} received — Awaiting confirmation.</b>\n\n"
            "Please be patient — our team will verify your payment and confirm shortly. "
            "You'll get a message here the moment it's done.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    user = update.effective_user
    product = db.get_product(order["product_id"])
    admin_text = (
        f"🕵️ <b>Order {esc(code)} — awaiting confirmation</b>\n\n"
        f"Buyer: {esc(user.first_name)} (@{esc(user.username or 'no username')}, <code>{user.id}</code>)\n"
        f"Product: {esc(product['name']) if product else '—'} x{order['quantity']}\n"
        f"Amount: ${order['amount_usd']:.2f}\n"
        f"Method: {esc(order['payment_method'])}\n"
        f"{proof_desc}"
    )

    # Public orders channel: plain status update only, NO admin action buttons.
    orders_channel = db.get_setting("ORDERS_CHANNEL_ID")
    channel_text = f"🕵️ Order {esc(code)} — payment proof submitted, awaiting confirmation."
    if update.message.photo and orders_channel:
        try:
            await context.bot.send_photo(orders_channel, file_id, caption=channel_text)
        except Exception as e:
            print(f"[warn] failed posting proof photo to orders channel: {e}")
    else:
        await post_to_channel(context.bot, orders_channel, channel_text)

    # Admins only: private DM with Confirm/Reject buttons.
    from config import ADMIN_IDS
    reply_markup = kb.order_admin_kb(order_id)
    for admin_id in ADMIN_IDS:
        try:
            if update.message.photo:
                await context.bot.send_photo(admin_id, file_id, caption=admin_text, parse_mode="HTML",
                                              reply_markup=reply_markup)
            else:
                await context.bot.send_message(admin_id, admin_text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            print(f"[warn] failed to DM admin {admin_id}: {e}")
