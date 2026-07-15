import os

# ── Core ──────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]                     # set in Railway variables, NOT in code
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Xplmaibot")

# Comma-separated Telegram user IDs who get admin access
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

DB_PATH = os.environ.get("DB_PATH", "xplm.db")

# ── Default channel setup (can be overridden later from the admin panel,
#    stored in the `settings` table — these are just the initial seed) ──
DEFAULT_SETTINGS = {
    "MAIN_CHANNEL_ID": os.environ.get("MAIN_CHANNEL_ID", ""),          # e.g. -1004303545553 (XPLM Ai STORE)
    "MAIN_CHANNEL_LINK": os.environ.get("MAIN_CHANNEL_LINK", "https://telegram.me/xplmstore"),
    "ORDERS_CHANNEL_ID": os.environ.get("ORDERS_CHANNEL_ID", ""),      # e.g. -1004345254651 (Xplm ORDERS PANEL)
    "ORDERS_CHANNEL_LINK": os.environ.get("ORDERS_CHANNEL_LINK", "https://telegram.me/xplmorders"),
    "PROOFS_CHANNEL_ID": os.environ.get("PROOFS_CHANNEL_ID", ""),      # set once you create/decide a proofs channel
    "PROOFS_CHANNEL_LINK": os.environ.get("PROOFS_CHANNEL_LINK", ""),
    "TESTIMONIALS_CHANNEL_ID": os.environ.get("TESTIMONIALS_CHANNEL_ID", ""),
    "TESTIMONIALS_CHANNEL_LINK": os.environ.get("TESTIMONIALS_CHANNEL_LINK", ""),
    "SUPPORT_USERNAME": os.environ.get("SUPPORT_USERNAME", "Peruv1an"),
    "BINANCE_PAY_UID": os.environ.get("BINANCE_PAY_UID", ""),
    "WALLET_CONTACT": os.environ.get("WALLET_CONTACT", ""),
}
