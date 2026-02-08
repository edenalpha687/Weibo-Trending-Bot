import os
import requests
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

DEX_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/"

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


# ========= PRICE CONVERSION =========
def get_coin_price(network):
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
            f"https://api.coingecko.com/api/v3/simple/price?ids={ids[network]}&vs_currencies=usd",
            timeout=10,
        ).json()

        return list(r.values())[0]["usd"]
    except:
        return None


# ========= DEX FETCH =========
def fetch_dex_data(ca):
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
        "pair_url": pair.get("url"),
        "logo": (pair.get("info") or {}).get("imageUrl"),
    }


# ========= START =========
def start(update: Update, context: CallbackContext):
    kb = [[InlineKeyboardButton("🐰Activate Weibo Trending 🇨🇳", callback_data="START")]]

    update.message.reply_text(
        "🔥 WEIBO TRENDING 🇨🇳 🐇\n\n"
        "🐰Boost Visibility for your Token in the Chinese market\n"
        "Fast Activation • Manual Control • Chinese visibility 🇨🇳",
        reply_markup=InlineKeyboardMarkup(kb),
    )


# ========= BUTTONS =========
def buttons(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    uid = q.from_user.id
    state = USER_STATE.get(uid)

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

    elif q.data == "PACKAGES":
        kb = [[InlineKeyboardButton(f"{k} — ${v}", callback_data=f"PKG_{k}")]
              for k, v in PACKAGES.items()]

        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="START")])

        context.bot.send_message(uid, "Select trending duration:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("PKG_"):
        pkg = q.data.replace("PKG_", "")
        state["package"] = pkg
        usd_price = PACKAGES[pkg]

        coin_price = get_coin_price(state["network"])
        amount = round((usd_price / coin_price) * 1.02, 4) if coin_price else usd_price

        state["amount"] = amount

        caption = (
            "🟢 Token Detected\n\n"
            f"Name: {state['name']}\n"
            f"Symbol: {state['symbol']}\n"
            f"Price: ${state['price']}\n"
            f"Liquidity: ${state['liquidity']}\n"
            f"Market Cap: ${state['mcap']}\n\n"
            f"⏱ Package: {pkg}\n"
            f"💰 Pay: {amount} {state['network']}"
        )

        q.message.delete()

        context.bot.send_photo(
            uid,
            state["logo"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm", callback_data="PAY")],
                [InlineKeyboardButton("⬅️ Back", callback_data="PACKAGES")],
            ]),
        )

    elif q.data == "PAY":
        wallet = NETWORK_WALLETS[state["network"]]
        state["step"] = "TXID"

        context.bot.send_message(
            uid,
            f"Activation Address ({state['network']}):\n\n"
            f"`{wallet}`\n\n"
            "🛎️ Send TXID to confirm",
            parse_mode="Markdown",
        )


# ========= TEXT =========
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
                f"Liquidity: ${data['liquidity']}\n"
                f"Market Cap: ${data['mcap']}"
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

        context.bot.send_message(
            ADMIN_ID,
            f"Payment Received\n\n"
            f"{state['name']} ({state['symbol']})\n"
            f"Network: {state['network']}\n"
            f"Package: {state['package']}\n"
            f"TXID: {txt}",
        )

        update.message.reply_text("Payment pending admin approval.")
        USER_STATE.pop(uid, None)


# ========= MAIN =========
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
