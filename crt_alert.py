import requests
import time
from datetime import datetime
import random

TOKEN = "8671433198:AAEftUbbKOcuStOiH5FozZR_5zTPTPhP02E"
CHAT_ID = "7329783593"

QUOTES = [
    "Les meilleurs trades viennent a ceux qui attendent",
    "Discipline > Emotion. Toujours.",
    "Un bon trade c'est un trade prepare",
    "Patience et discipline font les grands traders",
    "Le marche recompense ceux qui restent calmes",
    "Coupe tes pertes, laisse courir tes gains",
    "Les pros attendent, les amateurs forcent",
    "Chaque pip gagne est une victoire de discipline",
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

def get_candles(outputsize=20):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": outputsize,
        "apikey": "5a9a64f5f7ba46c79d17c50b1a3a485d",
        "type": "Physical Currency"
    }
    r = requests.get(url, params=params)
    return r.json()["values"]

def calculate_ema(prices, period):
    if len(prices) < period:
        return prices[-1]
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calculate_atr(candles, period=14):
    trs = []
    for i in range(1, min(len(candles)-1, period+1)):
        high = float(candles[i]["high"])
        low = float(candles[i]["low"])
        prev_close = float(candles[i+1]["close"])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    if not trs:
        return 5
    return round(sum(trs) / len(trs), 2)

def detect_fvg(candles):
    for i in range(1, len(candles)-1):
        high_prev = float(candles[i+1]["high"])
        low_next = float(candles[i-1]["low"])
        high_next = float(candles[i-1]["high"])
        low_prev = float(candles[i+1]["low"])
        if low_next > high_prev:
            return "BULLISH"
        if high_next < low_prev:
            return "BEARISH"
    return None

def detect_ob(candles):
    for i in range(2, len(candles)-1):
        curr_close = float(candles[i]["close"])
        curr_open = float(candles[i]["open"])
        next_close = float(candles[i-1]["close"])
        if curr_close < curr_open and next_close > curr_open:
            return "BULLISH"
        if curr_close > curr_open and next_close < curr_open:
            return "BEARISH"
    return None

def get_sniper_entry(candles, direction, current_price, atr):
    fvg_dir = detect_fvg(candles)
    ob_dir = detect_ob(candles)
    sl_distance = round(atr * 1.5, 2)
    tp1_distance = round(atr * 2, 2)
    tp2_distance = round(atr * 4, 2)
    confirmations = []

    if direction == "BULLISH":
        entry = current_price
        sl = round(entry - sl_distance, 2)
        tp1 = round(entry + tp1_distance, 2)
        tp2 = round(entry + tp2_distance, 2)
        if fvg_dir == "BULLISH":
            confirmations.append("FVG Bullish detecte")
        if ob_dir == "BULLISH":
            confirmations.append("Order Block Bullish")
    else:
        entry = current_price
        sl = round(entry + sl_distance, 2)
        tp1 = round(entry - tp1_distance, 2)
        tp2 = round(entry - tp2_distance, 2)
        if fvg_dir == "BEARISH":
            confirmations.append("FVG Bearish detecte")
        if ob_dir == "BEARISH":
            confirmations.append("Order Block Bearish")

    return entry, sl, tp1, tp2, confirmations

last_alert = None
signal_count_today = 0
high_breaks_today = 0
low_breaks_today = 0
last_date = datetime.now().date()
morning_sent = False
evening_sent = False

print("Bot CRT Sniper demarre")
send_telegram("Bot CRT Sniper active - Surveillance XAUUSD M15 H24")

while True:
    try:
        now = datetime.now()
        current_date = now.date()
        current_hour = now.hour
        current_minute = now.minute

        if current_date != last_date:
            signal_count_today = 0
            high_breaks_today = 0
            low_breaks_today = 0
            last_date = current_date
            morning_sent = False
            evening_sent = False

        candles = get_candles(20)
        closes = [float(c["close"]) for c in reversed(candles)]
        prev = candles[1]
        current = candles[0]

        crt_high = round(float(prev["high"]), 2)
        crt_low = round(float(prev["low"]), 2)
        current_price = round(float(current["close"]), 2)

        ema9 = calculate_ema(closes[-9:], 9)
        ema21 = calculate_ema(closes[-21:], 21)
        rsi = calculate_rsi(closes)
        atr = calculate_atr(candles)

        minutes_left = 15 - (current_minute % 15)
        alert_key = f"{crt_high}-{crt_low}"

        if current_hour == 8 and current_minute < 2 and not morning_sent:
            ema_dir = "BULLISH" if ema9 > ema21 else "BEARISH"
            msg = (
                f"GOOD MORNING TRADER\n"
                f"━━━━━━━━━━━━━━━\n"
                f"XAUUSD Setup du jour\n"
                f"CRT HIGH : {crt_high}\n"
                f"CRT LOW : {crt_low}\n"
                f"Bias EMA : {ema_dir}\n"
                f"RSI : {rsi}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Reste patient, attends le setup !\n"
                f"Today we eat !"
            )
            send_telegram(msg)
            morning_sent = True

        if current_hour == 22 and current_minute < 2 and not evening_sent:
            msg = (
                f"DAILY RECAP XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Signaux aujourd'hui : {signal_count_today}\n"
                f"Breaks HIGH : {high_breaks_today}\n"
                f"Breaks LOW : {low_breaks_today}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Repose toi bien, demain on est back !"
            )
            send_telegram(msg)
            evening_sent = True

        if current_price > crt_high and last_alert != f"HIGH-{alert_key}":
            signal_count_today += 1
            high_breaks_today += 1
            entry, sl, tp1, tp2, confirmations = get_sniper_entry(candles, "BULLISH", current_price, atr)
            rr1 = round(abs(tp1 - entry) / abs(entry - sl), 1) if abs(entry - sl) > 0 else 0
            rr2 = round(abs(tp2 - entry) / abs(entry - sl), 1) if abs(entry - sl) > 0 else 0
            ema_conf = "EMAs alignees haussier" if ema9 > ema21 else "EMAs pas alignees"
            rsi_conf = "RSI neutre" if 30 < rsi < 70 else f"RSI {rsi} - Zone extreme"
            conf_text = " | ".join(confirmations) if confirmations else "Pas de FVG/OB detecte"
            quote = random.choice(QUOTES)
            msg = (
                f"SIGNAL CRT - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"BREAK CRT HIGH {crt_high}\n"
                f"Heure : {now.strftime('%H:%M')} M15\n"
                f"Direction : BULLISH\n"
                f"Prochaine bougie : {minutes_left} min\n"
                f"━━━━━━━━━━━━━━━\n"
                f"SNIPER ENTRY\n"
                f"BUY : {entry}\n"
                f"TP1 : {tp1} (+{round(tp1-entry,2)}$)\n"
                f"TP2 : {tp2} (+{round(tp2-entry,2)}$)\n"
                f"SL : {sl} (-{round(entry-sl,2)}$)\n"
                f"RR : 1:{rr1} / 1:{rr2}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{ema_conf}\n"
                f"{rsi_conf}\n"
                f"{conf_text}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"FILE SUR M1 !\n"
                f"{quote}"
            )
            send_telegram(msg)
            last_alert = f"HIGH-{alert_key}"
            print(msg)

        elif current_price < crt_low and last_alert != f"LOW-{alert_key}":
            signal_count_today += 1
            low_breaks_today += 1
            entry, sl, tp1, tp2, confirmations = get_sniper_entry(candles, "BEARISH", current_price, atr)
            rr1 = round(abs(entry - tp1) / abs(sl - entry), 1) if abs(sl - entry) > 0 else 0
            rr2 = round(abs(entry - tp2) / abs(sl - entry), 1) if abs(sl - entry) > 0 else 0
            ema_conf = "EMAs alignees baissier" if ema9 < ema21 else "EMAs pas alignees"
            rsi_conf = "RSI neutre" if 30 < rsi < 70 else f"RSI {rsi} - Zone extreme"
            conf_text = " | ".join(confirmations) if confirmations else "Pas de FVG/OB detecte"
            quote = random.choice(QUOTES)
            msg = (
                f"SIGNAL CRT - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"BREAK CRT LOW {crt_low}\n"
                f"Heure : {now.strftime('%H:%M')} M15\n"
                f"Direction : BEARISH\n"
                f"Prochaine bougie : {minutes_left} min\n"
                f"━━━━━━━━━━━━━━━\n"
                f"SNIPER ENTRY\n"
                f"SELL : {entry}\n"
                f"TP1 : {tp1} (-{round(entry-tp1,2)}$)\n"
                f"TP2 : {tp2} (-{round(entry-tp2,2)}$)\n"
                f"SL : {sl} (+{round(sl-entry,2)}$)\n"
                f"RR : 1:{rr1} / 1:{rr2}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{ema_conf}\n"
                f"{rsi_conf}\n"
                f"{conf_text}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"FILE SUR M1 !\n"
                f"{quote}"
            )
            send_telegram(msg)
            last_alert = f"LOW-{alert_key}"
            print(msg)

        else:
            print(f"[{now.strftime('%H:%M:%S')}] HIGH: {crt_high} | LOW: {crt_low} | Prix: {current_price} | RSI: {rsi} | Signals: {signal_count_today}")

        time.sleep(60)

    except Exception as e:
        print(f"Erreur: {e}")
        time.sleep(60)
