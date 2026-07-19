import time
from telegram import Update
from telegram.ext import ContextTypes

import db
from config import ADMIN_IDS

START_TIME = time.time()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def is_member(bot, chat_id: str, user_id: int) -> bool:
    if not chat_id:
        return True  # channel not configured yet — don't block users
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        # If the bot isn't admin in the channel yet, or the check fails, don't hard-lock users out
        return True


async def user_passes_gate(bot, user_id: int) -> bool:
    main_id = db.get_setting("MAIN_CHANNEL_ID")
    proofs_id = db.get_setting("PROOFS_CHANNEL_ID") or db.get_setting("ORDERS_CHANNEL_ID")
    ok_main = await is_member(bot, main_id, user_id)
    ok_proofs = await is_member(bot, proofs_id, user_id)
    return ok_main and ok_proofs


def uptime_str() -> str:
    secs = int(time.time() - START_TIME)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"


async def post_to_channel(bot, chat_id: str, text: str, **kwargs):
    if not chat_id:
        return
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML", **kwargs)
    except Exception as e:
        print(f"[warn] failed to post to channel {chat_id}: {e}")
