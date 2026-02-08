import os
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

# Your banner image
ENTER_CA_IMAGE_URL = "https://raw.githubusercontent.com/edenalpha687/weibo-trending-bot/main/9223EC4F-93FA-4639-A491-01D8BDB0DB4B.png"

DEX_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/"

# ================= MULTICHAIN =================
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

# ================= HELPERS =================
def fmt_usd(v):
    if not v:
        return "—"
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.2f}K"
    return f"${v:.2f}"


def fetch_dex_data(ca):
    try:
        r = requests.get(f"{DEX_TOKEN_URL}{ca}", timeout=15)
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
            "logo": (pair.get("info") or {}).get("imageUrl"),
        }
    except:
        return None


def get_price(symbol):
    ids = {
        "SOL": "solana",
        "ETH": "ethereum",
        "BSC": "binancecoin",
        "BASE": "ethereum",
        "SUI": "sui",
        "XRP": "ripple",
    }

    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={ids[symbol]}&vs_currencies=usd"
        ).json()

        return list(r.values())[0]["usd"]
    except:
        return None


# ================= START =================
def start(update: Update, context: CallbackContext):

    kb = [[InlineKeyboardButton("Start Trending", callback_data="START")]]

    update.message.reply_photo(
        photo=ENTER_CA_IMAGE_URL,
        caption=(
            "WEIBO TRENDING\n\n"
            "Boost Visibility for your Token in the Chinese market\n"
            "Fast Activation • Manual Control • Chinese Visibility"
        ),
        reply_markup=InlineKeyboardMarkup(kb),
    )


# ================= BUTTONS =================
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    uid = q.from_user.id

    # Start trending button
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

        context.bot.send_message(
            chat_id=uid,
            text="Choose Network",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    # Network selected
    elif q.data.startswith("NET_"):
        network = q.data.replace("NET_", "")
        USER_STATE[uid] = {"step": "CA", "network": network}

        q.message.delete()

        context.bot.send_photo(
            chat_id=uid,
            photo=ENTER_CA_IMAGE_URL,
            caption="Enter your token contract address",
        )

    # Packages
    elif q.data == "PACKAGES":

        kb = [[InlineKeyboardButton(k, callback_data=f"PKG_{k}")]
              for k in PACKAGES.keys()]

        context.bot.send_message(
            chat_id=uid,
            text="Select trending duration:",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif q.data.startswith("PKG_"):
        pkg = q.data.replace("PKG_", "")
        state = USER_STATE.get(uid)

        state["package"] = pkg

        usd_price = PACKAGES[pkg]
        coin_price = get_price(state["network"])

        amount = round((usd_price / coin_price) * 1.02, 4)
        state["amount"] = amount

        wallet = NETWORK_WALLETS[state["network"]]

        context.bot.send_message(
            chat_id=uid,
            text=(
                f"Send {amount} {state['network']} to:\n\n"
                f"{wallet}\n\n"
                "Send TXID after payment."
            ),
        )

        state["step"] = "TXID"

    # Admin approval
    elif q.data.startswith("ADMIN_START_") and uid == ADMIN_ID:

        ref = q.data.replace("ADMIN_START_", "")
        payload = context.bot_data.pop(ref, None)

        context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=(
                "Weibo Trending Live\n\n"
                f"{payload['name']} ({payload['symbol']})\n"
                f"Network: {payload['network']}\n"
                f"Started: {datetime.utcnow().strftime('%H:%M UTC')}"
            ),
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
            chat_id=uid,
            photo=data["logo"],
            caption=(
                f"Token Detected\n\n"
                f"Name: {data['name']}\n"
                f"Symbol: {data['symbol']}\n"
                f"Price: ${data['price']}\n"
                f"Liquidity: {fmt_usd(data['liquidity'])}\n"
                f"Market Cap: {fmt_usd(data['mcap'])}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Continue", callback_data="PACKAGES")]
            ]),
        )

    elif state["step"] == "TXID":

        if txt in USED_TXIDS:
            update.message.reply_text("TXID already used.")
            return

        USED_TXIDS.add(txt)

        ref = f"{uid}_{txt[-6:]}"
        context.bot_data[ref] = state.copy()

        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "Payment received\n\n"
                f"{state['name']} ({state['symbol']})\n"
                f"Network: {state['network']}\n"
                f"Package: {state['package']}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("START TRENDING", callback_data=f"ADMIN_START_{ref}")]
            ]),
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
