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

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

WEBHOOK_BASE = "https://worker-production-56e9.up.railway.app"

ENTER_CA_IMAGE_URL = (
    "https://raw.githubusercontent.com/edenalpha687/weibo-trending-bot/main/"
    "9223EC4F-93FA-4639-A491-01D8BDB0DB4B.png"
)

DEX_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/"
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# ========= MULTICHAIN WALLETS =========
NETWORK_WALLETS = {
    "SOL": os.getenv("SOL_WALLET"),
    "ETH": os.getenv("ETH_WALLET"),
    "BSC": os.getenv("BSC_WALLET"),
    "BASE": os.getenv("BASE_WALLET"),
    "SUI": os.getenv("SUI_WALLET"),
    "XRP": os.getenv("XRP_WALLET"),
}

# ========= UPDATED PACKAGES =========
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


# ================= HELPERS =================
def is_solana_address(addr):
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", addr))


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

    telegram_link = None
    for l in (pair.get("info") or {}).get("links", []):
        if l.get("type") == "telegram":
            telegram_link = l.get("url")

    return {
        "name": pair["baseToken"]["name"],
        "symbol": pair["baseToken"]["symbol"],
        "price": pair.get("priceUsd"),
        "liquidity": (pair.get("liquidity") or {}).get("usd"),
        "mcap": pair.get("fdv"),
        "pair_url": pair.get("url"),
        "logo": (pair.get("info") or {}).get("imageUrl"),
        "telegram": telegram_link,
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


# ================= START =================
def start(update: Update, context: CallbackContext):
    kb = [[InlineKeyboardButton("Start Trending", callback_data="START")]]

    update.message.reply_text(
        "WEIBO TRENDING\n\n"
        "Boost Visibility for your Token in the Chinese market\n"
        "Fast Activation • Manual Control • Chinese visibility",
        reply_markup=InlineKeyboardMarkup(kb),
    )


# ================= BUTTONS =================
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    uid = q.from_user.id

    # Choose network first
    if q.data == "START":
        kb = [
            [
                InlineKeyboardButton("SOL", callback_data="NET_SOL"),
                InlineKeyboardButton("ETH", callback_data="NET_ETH"),
                InlineKeyboardButton("BSC", callback_data="NET_BSC"),
            ],
            [
                InlineKeyboardButton("SUI", callback_data="NET_SUI"),
                InlineKeyboardButton("BASE", callback_data="NET_BASE"),
                InlineKeyboardButton("XRP", callback_data="NET_XRP"),
            ],
        ]

        q.message.delete()
        context.bot.send_message(uid, "Choose Network:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("NET_"):
        network = q.data.replace("NET_", "")
        USER_STATE[uid] = {"step": "CA", "network": network}

        q.message.delete()
        context.bot.send_photo(
            uid,
            ENTER_CA_IMAGE_URL,
            caption="WEIBO TRENDING\n\nEnter Your Token CA",
        )

    elif q.data == "PACKAGES":
        kb = [[InlineKeyboardButton(k, callback_data=f"PKG_{k}")]
              for k in PACKAGES.keys()]
        context.bot.send_message(uid, "Select trending duration:",
                                 reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("PKG_"):
        pkg = q.data.replace("PKG_", "")
        state = USER_STATE[uid]
        state["package"] = pkg
        state["amount"] = PACKAGES[pkg]

        wallet = NETWORK_WALLETS[state["network"]]

        context.bot.send_message(
            uid,
            f"Send {state['amount']} USD equivalent to:\n\n{wallet}\n\nSend TXID after payment.",
        )

        state["step"] = "TXID"

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


# ================= TEXT =================
def messages(update: Update, context: CallbackContext):
    uid = update.message.from_user.id
    txt = update.message.text.strip()
    state = USER_STATE.get(uid)

    if not state:
        return

    if state["step"] == "CA":
        data = fetch_dex_data(txt)
        if not data:
            update.message.reply_text("Token not found.")
            return

        state.update(data)
        state["ca"] = txt
        state["step"] = "PREVIEW"

        context.bot.send_photo(
            uid,
            data["logo"],
            caption=(
                f"Token Detected\n\n"
                f"Name: {data['name']}\n"
                f"Symbol: {data['symbol']}\n"
                f"Price: ${data['price']}\n"
                f"Liquidity: {fmt_usd(data['liquidity'])}\n"
                f"Market Cap: {fmt_usd(data['mcap'])}"
            ),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Continue", callback_data="PACKAGES")]]
            ),
        )

    elif state["step"] == "TXID":
        if txt in USED_TXIDS:
            update.message.reply_text("TXID already used.")
            return

        res = verify_txid(txt)

        USED_TXIDS.add(txt)
        ref = f"{uid}_{txt[-6:]}"
        context.bot_data[ref] = state.copy()

        context.bot.send_message(
            ADMIN_ID,
            "Payment received\n\n"
            f"{state['name']} ({state['symbol']})\n"
            f"Network: {state['network']}\n"
            f"Package: {state['package']}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("START TRENDING", callback_data=f"ADMIN_START_{ref}")]]
            ),
        )

        update.message.reply_text("Payment pending admin approval.")
        USER_STATE.pop(uid, None)


# ================= MAIN =================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(buttons))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, messages))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
