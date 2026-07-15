import sqlite3
import time
import secrets
import string
from contextlib import contextmanager

from config import DB_PATH, DEFAULT_SETTINGS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at INTEGER,
    referral_code TEXT UNIQUE,
    referred_by INTEGER,
    is_banned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    price_usd REAL NOT NULL,
    delivery_type TEXT NOT NULL DEFAULT 'manual',   -- 'auto' | 'manual'
    active INTEGER DEFAULT 1,
    created_at INTEGER
);

-- stock for auto-delivery products (license keys / codes / text)
CREATE TABLE IF NOT EXISTS stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_used INTEGER DEFAULT 0,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    amount_usd REAL NOT NULL,
    payment_method TEXT,          -- e.g. 'USDT-TRC20', 'BinancePay', 'Wallet'
    payment_ref TEXT,             -- address/uid shown to buyer
    status TEXT DEFAULT 'pending_payment',  -- pending_payment -> awaiting_confirmation -> paid -> delivered / cancelled
    proof_file_id TEXT,
    created_at INTEGER,
    updated_at INTEGER
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network TEXT NOT NULL,        -- e.g. 'USDT (TRC20)', 'BTC', 'Binance Pay', 'Telegram Wallet'
    address TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(_SCHEMA)
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )


# ── settings ──────────────────────────────────────────────────────────
def get_setting(key: str) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else ""


def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


# ── users ─────────────────────────────────────────────────────────────
def _gen_ref_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(7))


def get_or_create_user(user_id: int, username: str, first_name: str, referred_by: int | None = None):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET username=?, first_name=? WHERE user_id=?",
                (username, first_name, user_id),
            )
            return dict(row)
        code = _gen_ref_code()
        while conn.execute("SELECT 1 FROM users WHERE referral_code=?", (code,)).fetchone():
            code = _gen_ref_code()
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, joined_at, referral_code, referred_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, first_name, int(time.time()), code, referred_by),
        )
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row)


def get_user(user_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_ref_code(code: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE referral_code=?", (code,)).fetchone()
        return dict(row) if row else None


def count_referrals(user_id: int) -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) c FROM users WHERE referred_by=?", (user_id,)).fetchone()
        return row["c"]


def total_users() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]


# ── products ──────────────────────────────────────────────────────────
def add_product(name, category, description, price_usd, delivery_type):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO products (name, category, description, price_usd, delivery_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, category, description, price_usd, delivery_type, int(time.time())),
        )
        return cur.lastrowid


def list_categories():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM products WHERE active=1 ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


def list_products(category=None, active_only=True):
    with get_db() as conn:
        q = "SELECT * FROM products"
        cond = []
        args = []
        if category:
            cond.append("category=?")
            args.append(category)
        if active_only:
            cond.append("active=1")
        if cond:
            q += " WHERE " + " AND ".join(cond)
        q += " ORDER BY id DESC"
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def get_product(product_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        return dict(row) if row else None


def set_product_active(product_id: int, active: bool):
    with get_db() as conn:
        conn.execute("UPDATE products SET active=? WHERE id=?", (1 if active else 0, product_id))


def stock_count(product_id: int) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) c FROM stock_items WHERE product_id=? AND is_used=0", (product_id,)
        ).fetchone()
        return row["c"]


def add_stock(product_id: int, lines: list[str]):
    with get_db() as conn:
        conn.executemany(
            "INSERT INTO stock_items (product_id, content) VALUES (?, ?)",
            [(product_id, line) for line in lines],
        )


def pop_stock_item(product_id: int):
    """Claim one unused stock item atomically, return its content or None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, content FROM stock_items WHERE product_id=? AND is_used=0 LIMIT 1",
            (product_id,),
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE stock_items SET is_used=1 WHERE id=?", (row["id"],))
        return row["content"]


# ── payment methods ───────────────────────────────────────────────────
def add_payment_method(network: str, address: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO payment_methods (network, address) VALUES (?, ?)", (network, address)
        )


def list_payment_methods(active_only=True):
    with get_db() as conn:
        q = "SELECT * FROM payment_methods"
        if active_only:
            q += " WHERE active=1"
        return [dict(r) for r in conn.execute(q).fetchall()]


def remove_payment_method(pm_id: int):
    with get_db() as conn:
        conn.execute("UPDATE payment_methods SET active=0 WHERE id=?", (pm_id,))


# ── orders ────────────────────────────────────────────────────────────
def create_order(user_id, product_id, quantity, amount_usd, payment_method, payment_ref):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO orders (user_id, product_id, quantity, amount_usd, payment_method, "
            "payment_ref, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'awaiting_confirmation', ?, ?)",
            (user_id, product_id, quantity, amount_usd, payment_method, payment_ref, int(time.time()), int(time.time())),
        )
        return cur.lastrowid


def attach_proof(order_id: int, file_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE orders SET proof_file_id=?, updated_at=? WHERE id=?",
            (file_id, int(time.time()), order_id),
        )


def get_order(order_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None


def set_order_status(order_id: int, status: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE orders SET status=?, updated_at=? WHERE id=?", (status, int(time.time()), order_id)
        )


def list_user_orders(user_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_pending_orders():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status='awaiting_confirmation' ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def total_orders() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]


def total_revenue() -> float:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount_usd),0) s FROM orders WHERE status='delivered'"
        ).fetchone()
        return row["s"]
