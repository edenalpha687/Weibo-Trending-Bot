# ONLY UI TEXT + BANNERS UPDATED — LOGIC UNCHANGED

import os
import re
import requests
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

WEBHOOK_BASE = "https://worker-production-56e9.up.railway.app"

DEX_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/"
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

NETWORK_WALLETS = {
    "SOL": os.getenv("SOL_WALLET"),
    "ETH": os.getenv("ETH_WALLET"),
    "BSC": os.getenv("BSC_WALLET"),
    "BASE": os.getenv("BASE_WALLET"),
    "SUI": os.getenv("SUI_WALLET"),
    "XRP": os.getenv("XRP_WALLET"),
}

PACKAGES = {
    "24H": 2500,
    "48H": 5500,
    "72H": 8000,
    "96H": 10500,
    "120H": 13000,
    "144H": 15500,
    "168H": 18000,
}

USER_STATE = {}
USED_TXIDS = set()


def fmt_usd(v):
    if not v:
        return "—"
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.2f}K"
    return f"${v:.2f}"


def fetch_dex_data(ca):
    r = requests.get(f"{DEX_TOKEN_URL}{ca}", timeout=15)
    r.raise_for_status()
    pairs = r.json().get("pairs", [])
    if not pairs:
        return None

    pair = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd", 0))

    return {
        "name": pair["baseToken"]["name"],
        "symbol": pair["baseToken"]["symbol"],
        "price": pair.get("priceUsd"),
        "liquidity": (pair.get("liquidity") or {}).get("usd"),
        "mcap": pair.get("fdv"),
        "pair_url": pair.get("url"),
        "logo": (pair.get("info") or {}).get("imageUrl"),
    }


def verify_txid(txid):
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignatureStatuses",
            "params": [[txid], {"searchTransactionHistory": True}],
        }

        r = requests.post(HELIUS_RPC_URL, json=payload, timeout=15)
        status = r.json()["result"]["value"][0]

        if status and status.get("confirmationStatus") in ("confirmed", "finalized"):
            return "OK"

        return "PENDING"
    except:
        return "PENDING"


def activate_trending(payload):
    requests.post(
        f"{WEBHOOK_BASE}/activate",
        json={
            "mint": payload["ca"],
            "name": payload["name"],
            "price": payload["price"],
            "mcap": payload["mcap"],
            "logo": payload["logo"],
            "dex": payload["pair_url"],
        },
        timeout=10,
    )


# ===== START =====
def start(update: Update, context: CallbackContext):
    kb = [[InlineKeyboardButton("🐰Activate Weibo Trending 🇨🇳", callback_data="START")]]

    update.message.reply_text(
        "🔥 WEIBO TRENDING 🇨🇳 🐇\n\n"
        "🐰Boost Visibility for your Token in the Chinese market\n"
        "Fast Activation • Manual Control • Chinese visibility 🇨🇳",
        reply_markup=InlineKeyboardMarkup(kb),
    )


# ===== BUTTONS =====
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    uid = q.from_user.id

    if q.data == "START":
        kb = [
            [InlineKeyboardButton("SOL", callback_data="NET_SOL"),
             InlineKeyboardButton("ETH", callback_data="NET_ETH"),
             InlineKeyboardButton("BSC", callback_data="NET_BSC")],
            [InlineKeyboardButton("SUI", callback_data="NET_SUI"),
             InlineKeyboardButton("BASE", callback_data="NET_BASE"),
             InlineKeyboardButton("XRP", callback_data="NET_XRP")]
        ]

        q.message.delete()

        context.bot.send_photo(
            uid,
            "https://raw.githubusercontent.com/edenalpha687/weibo-trending-bot/main/1190BF8B-063E-4AFE-8B1D-88E9BF653834.png",
            caption="Choose Network",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif q.data.startswith("NET_"):
        network = q.data.replace("NET_", "")
        USER_STATE[uid] = {"step": "CA", "network": network}

        q.message.delete()

        context.bot.send_photo(
            uid,
            "https://raw.githubusercontent.com/edenalpha687/weibo-trending-bot/main/F33A4A2F-E8A9-440E-BA47-F7603692010A.png",
            caption="Enter Your Token CA",
        )

    elif q.data.startswith("ADMIN_START_") and uid == ADMIN_ID:
        ref = q.data.replace("ADMIN_START_", "")
        payload = context.bot_data.pop(ref, None)

        activate_trending(payload)

        context.bot.send_message(
            CHANNEL_USERNAME,
            "Weibo Trending Live\n\n"
            f"{payload['name']} ({payload['symbol']})\n"
            f"CA: {payload['ca']}\n"
            f"Started: {datetime.utcnow().strftime('%H:%M UTC')}",
        )

        q.edit_message_text("Trending activated.")


# ===== MAIN =====
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(buttons))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
