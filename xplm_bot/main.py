import logging

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters,
)

from config import BOT_TOKEN
import db
from handlers import start, menu, order, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_app():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # ── core ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CallbackQueryHandler(start.home_callback, pattern="^menu:home$"))

    # ── slash-command shortcuts (mirrors BotFather command list) ────
    app.add_handler(CommandHandler("order", order.order_cmd))
    app.add_handler(CommandHandler("dashboard", menu.dashboard_cmd))
    app.add_handler(CommandHandler("history", menu.history_cmd))
    app.add_handler(CommandHandler("referral", menu.referral_cmd))
    app.add_handler(CommandHandler("support", menu.support_cmd))
    app.add_handler(CommandHandler("status", menu.status_cmd))
    app.add_handler(CommandHandler("admin", admin.admin_cmd))

    # ── main menu sections ──────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(menu.dashboard, pattern="^menu:dashboard$"))
    app.add_handler(CallbackQueryHandler(menu.profile, pattern="^menu:profile$"))
    app.add_handler(CallbackQueryHandler(menu.referral, pattern="^menu:referral$"))
    app.add_handler(CallbackQueryHandler(menu.support, pattern="^menu:support$"))
    app.add_handler(CallbackQueryHandler(menu.settings_menu, pattern="^menu:settings$"))
    app.add_handler(CallbackQueryHandler(menu.status, pattern="^menu:status$"))
    app.add_handler(CallbackQueryHandler(menu.history, pattern="^menu:history$"))

    # ── ordering ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(order.order_home, pattern="^menu:order$"))
    app.add_handler(CallbackQueryHandler(order.show_category, pattern="^cat:"))
    app.add_handler(CallbackQueryHandler(order.show_product, pattern="^prod:"))
    app.add_handler(CallbackQueryHandler(order.buy_start, pattern="^buy:"))
    app.add_handler(CallbackQueryHandler(order.choose_qty, pattern="^qty:"))
    app.add_handler(CallbackQueryHandler(order.qty_back, pattern="^qtyback:"))
    app.add_handler(CallbackQueryHandler(order.choose_payment, pattern="^pay:"))

    # proof submission (photo or text) — only acts if user_data flag is set
    app.add_handler(MessageHandler((filters.PHOTO | (filters.TEXT & ~filters.COMMAND)), order.receive_proof), group=1)

    # ── admin: simple callbacks ──────────────────────────────────────
    app.add_handler(CallbackQueryHandler(admin.admin_home, pattern="^admin:home$"))
    app.add_handler(CallbackQueryHandler(admin.list_products_admin, pattern="^admin:products$"))
    app.add_handler(CallbackQueryHandler(admin.toggle_product, pattern="^admtoggle:"))
    app.add_handler(CallbackQueryHandler(admin.payments_home, pattern="^admin:payments$"))
    app.add_handler(CallbackQueryHandler(admin.remove_payment, pattern="^admrmpm:"))
    app.add_handler(CallbackQueryHandler(admin.pending_orders, pattern="^admin:pending$"))
    app.add_handler(CallbackQueryHandler(admin.confirm_order, pattern="^admconf:"))
    app.add_handler(CallbackQueryHandler(admin.reject_order, pattern="^admrej:"))
    app.add_handler(CallbackQueryHandler(admin.mark_delivered, pattern="^admdeliv:"))
    app.add_handler(CallbackQueryHandler(admin.stats, pattern="^admin:stats$"))
    app.add_handler(CallbackQueryHandler(admin.channels_home, pattern="^admin:channels$"))

    # ── admin: conversations ──────────────────────────────────────────
    add_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_product_start, pattern="^admin:add_product$")],
        states={
            admin.ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_name)],
            admin.ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_category)],
            admin.ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_desc)],
            admin.ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_price)],
            admin.ADD_DELIVERY: [CallbackQueryHandler(admin.add_delivery, pattern="^deliv:")],
            admin.ADD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_stock)],
        },
        fallbacks=[CallbackQueryHandler(admin.cancel_conv, pattern="^menu:home$")],
        per_message=False,
    )
    app.add_handler(add_product_conv)

    bulk_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.bulk_add_start, pattern="^admin:bulk_add$")],
        states={
            admin.BULK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.bulk_add_receive)],
        },
        fallbacks=[CallbackQueryHandler(admin.cancel_conv, pattern="^menu:home$")],
        per_message=False,
    )
    app.add_handler(bulk_add_conv)

    add_payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_payment_start, pattern="^admin:add_payment$")],
        states={
            admin.PM_NETWORK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.pm_network)],
            admin.PM_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.pm_address)],
        },
        fallbacks=[CallbackQueryHandler(admin.cancel_conv, pattern="^menu:home$")],
        per_message=False,
    )
    app.add_handler(add_payment_conv)

    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.broadcast_start, pattern="^admin:broadcast$")],
        states={
            admin.BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.broadcast_send)],
        },
        fallbacks=[CallbackQueryHandler(admin.cancel_conv, pattern="^menu:home$")],
        per_message=False,
    )
    app.add_handler(broadcast_conv)

    set_channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_channel_start, pattern="^admsetch:")],
        states={
            admin.CHANNEL_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.set_channel_value)],
        },
        fallbacks=[CallbackQueryHandler(admin.cancel_conv, pattern="^menu:home$")],
        per_message=False,
    )
    app.add_handler(set_channel_conv)

    return app


def main():
    app = build_app()
    logger.info("XPLM Ai STORE bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
