from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import db


def main_menu_kb(is_admin: bool = False):
    rows = [
        [InlineKeyboardButton("🛒 Order", callback_data="menu:order"),
         InlineKeyboardButton("📊 Dashboard", callback_data="menu:dashboard")],
        [InlineKeyboardButton("📜 Order History", callback_data="menu:history"),
         InlineKeyboardButton("👤 My Profile", callback_data="menu:profile")],
        [InlineKeyboardButton("🎁 Referral Program", callback_data="menu:referral"),
         InlineKeyboardButton("🎧 Support", callback_data="menu:support")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
         InlineKeyboardButton("🤖 Bot Status", callback_data="menu:status")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def back_kb(target="menu:home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def join_gate_kb():
    main_link = db.get_setting("MAIN_CHANNEL_LINK")
    proofs_link = db.get_setting("PROOFS_CHANNEL_LINK") or db.get_setting("ORDERS_CHANNEL_LINK")
    rows = []
    if main_link:
        rows.append([InlineKeyboardButton("📢 Join Main Channel", url=main_link)])
    if proofs_link:
        rows.append([InlineKeyboardButton("✅ Join Proofs Channel", url=proofs_link)])
    rows.append([InlineKeyboardButton("🔄 I've Joined — Continue", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def categories_kb(categories):
    rows = [[InlineKeyboardButton(c, callback_data=f"cat:{c}")] for c in categories]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def products_kb(products, category):
    rows = [
        [InlineKeyboardButton(f"{p['name']} — ${p['price_usd']:.2f}", callback_data=f"prod:{p['id']}")]
        for p in products
    ]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu:order")])
    return InlineKeyboardMarkup(rows)


def product_detail_kb(product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy:{product_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:order")],
    ])


def payment_methods_kb(methods, product_id):
    rows = [
        [InlineKeyboardButton(f"🪙 {m['network']}", callback_data=f"pay:{m['id']}")] for m in methods
    ]
    rows.append([InlineKeyboardButton("💠 Binance Pay (UID)", callback_data="pay:binance")])
    rows.append([InlineKeyboardButton("💬 Telegram Wallet (contact seller)", callback_data="pay:wallet")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"buy:{product_id}"),
                 InlineKeyboardButton("❌ Cancel", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def payment_instructions_kb(product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Change Payment Method", callback_data=f"qtyback:{product_id}")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="menu:home")],
    ])


def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu:home")]])


def admin_home_kb():
    rows = [
        [InlineKeyboardButton("➕ Add Product", callback_data="admin:add_product")],
        [InlineKeyboardButton("📥 Bulk Add Products", callback_data="admin:bulk_add")],
        [InlineKeyboardButton("📦 Manage Products", callback_data="admin:products")],
        [InlineKeyboardButton("💳 Payment Methods", callback_data="admin:payments")],
        [InlineKeyboardButton("🧾 Pending Orders", callback_data="admin:pending")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin:stats")],
        [InlineKeyboardButton("🔗 Channel Settings", callback_data="admin:channels")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:home")],
    ]
    return InlineKeyboardMarkup(rows)


def order_admin_kb(order_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Payment", callback_data=f"admconf:{order_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"admrej:{order_id}")],
    ])
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import db


def main_menu_kb(is_admin: bool = False):
    rows = [
        [InlineKeyboardButton("🛒 Order", callback_data="menu:order"),
         InlineKeyboardButton("📊 Dashboard", callback_data="menu:dashboard")],
        [InlineKeyboardButton("📜 Order History", callback_data="menu:history"),
         InlineKeyboardButton("👤 My Profile", callback_data="menu:profile")],
        [InlineKeyboardButton("🎁 Referral Program", callback_data="menu:referral"),
         InlineKeyboardButton("🎧 Support", callback_data="menu:support")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
         InlineKeyboardButton("🤖 Bot Status", callback_data="menu:status")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def back_kb(target="menu:home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def join_gate_kb():
    main_link = db.get_setting("MAIN_CHANNEL_LINK")
    proofs_link = db.get_setting("PROOFS_CHANNEL_LINK") or db.get_setting("ORDERS_CHANNEL_LINK")
    rows = []
    if main_link:
        rows.append([InlineKeyboardButton("📢 Join Main Channel", url=main_link)])
    if proofs_link:
        rows.append([InlineKeyboardButton("✅ Join Proofs Channel", url=proofs_link)])
    rows.append([InlineKeyboardButton("🔄 I've Joined — Continue", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def categories_kb(categories):
    rows = [[InlineKeyboardButton(c, callback_data=f"cat:{c}")] for c in categories]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def products_kb(products, category):
    rows = [
        [InlineKeyboardButton(f"{p['name']} — ${p['price_usd']:.2f}", callback_data=f"prod:{p['id']}")]
        for p in products
    ]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu:order")])
    return InlineKeyboardMarkup(rows)


def product_detail_kb(product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy:{product_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:order")],
    ])


def payment_methods_kb(methods, product_id):
    rows = [
        [InlineKeyboardButton(f"🪙 {m['network']}", callback_data=f"pay:{m['id']}")] for m in methods
    ]
    rows.append([InlineKeyboardButton("💠 Binance Pay (UID)", callback_data="pay:binance")])
    rows.append([InlineKeyboardButton("💬 Telegram Wallet (contact seller)", callback_data="pay:wallet")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"buy:{product_id}"),
                 InlineKeyboardButton("❌ Cancel", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def payment_instructions_kb(product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Change Payment Method", callback_data=f"qtyback:{product_id}")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="menu:home")],
    ])


def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu:home")]])


def admin_home_kb():
    rows = [
        [InlineKeyboardButton("➕ Add Product", callback_data="admin:add_product")],
        [InlineKeyboardButton("📥 Bulk Add Products", callback_data="admin:bulk_add")],
        [InlineKeyboardButton("📦 Manage Products", callback_data="admin:products")],
        [InlineKeyboardButton("💳 Payment Methods", callback_data="admin:payments")],
        [InlineKeyboardButton("🧾 Pending Orders", callback_data="admin:pending")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin:stats")],
        [InlineKeyboardButton("🔗 Channel Settings", callback_data="admin:channels")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:home")],
    ]
    return InlineKeyboardMarkup(rows)


def order_admin_kb(order_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Payment", callback_data=f"admconf:{order_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"admrej:{order_id}")],
    ])
