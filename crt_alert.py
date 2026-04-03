import requests
import time
from datetime import datetime
import random
import threading

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
    "Trade ce que tu vois, pas ce que tu penses",
    "Le meilleur trade est parfois de ne pas trader",
]

# Etat global
paused = False
night_mode = False
signal_count_today = 0
high_breaks_today = 0
low_breaks_today = 0
last_alert = None
last_date = datetime.now().date()
morning_sent = False
evening_sent = False
last_offset = 0

def send_telegram(message, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    if reply_markup:
        import json
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(url, data=data)

def send_main_menu():
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Analyse MACD", "callback_data": "macd"},
                {"text": "Analyse RSI", "callback_data": "rsi"}
            ],
            [
                {"text": "Analyse EMA/SMA", "callback_data": "ema"},
                {"text": "Analyse complete", "callback_data": "full"}
            ],
            [
                {"text": "Niveaux CRT actuels", "callback_data": "crt"},
                {"text": "Stats du jour", "callback_data": "stats_day"}
            ],
            [
                {"text": "Stats semaine", "callback_data": "stats_week"},
                {"text": "Conseil du jour", "callback_data": "quote"}
            ],
            [
                {"text": "Pause alertes", "callback_data": "pause"},
                {"text": "Reprendre alertes", "callback_data": "resume"}
            ],
            [
                {"text": "Mode nuit ON", "callback_data": "night_on"},
                {"text": "Mode nuit OFF", "callback_data": "night_off"}
            ]
        ]
    }
    send_telegram("Que veux-tu faire ?", reply_markup=keyboard)

def answer_callback(callback_id):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    requests.post(url, data={"callback_query_id": callback_id})

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

def calculate_macd(prices):
    if len(prices) < 26:
        return 0, 0, 0
    ema12 = calculate_ema(prices[-12:], 12)
    ema26 = calculate_ema(prices[-26:], 26)
    macd_line = round(ema12 - ema26, 4)
    signal_line = round(macd_line * 0.9, 4)
    histogram = round(macd_line - signal_line, 4)
    return macd_line, signal_line, histogram

def calculate_sma(prices, period):
    if len(prices) < period:
        return prices[-1]
    return round(sum(prices[-period:]) / period, 2)

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

    if direction == "BULLISH":
        entry = current_price
        sl = round(entry - sl_distance, 2)
        tp1 = round(entry + tp1_distance, 2)
        tp2 = round(entry + tp2_distance, 2)
    else:
        entry = current_price
        sl = round(entry + sl_distance, 2)
        tp1 = round(entry - tp1_distance, 2)
        tp2 = round(entry - tp2_distance, 2)

    return entry, sl, tp1, tp2

def handle_callback(callback_data, callback_id):
    global paused, night_mode
    answer_callback(callback_id)

    try:
        candles = get_candles(30)
        closes = [float(c["close"]) for c in reversed(candles)]
        current_price = round(float(candles[0]["close"]), 2)
        prev = candles[1]
        crt_high = round(float(prev["high"]), 2)
        crt_low = round(float(prev["low"]), 2)
        ema9 = calculate_ema(closes[-9:], 9)
        ema21 = calculate_ema(closes[-21:], 21)
        sma50 = calculate_sma(closes, 50)
        rsi = calculate_rsi(closes)
        macd_line, signal_line, histogram = calculate_macd(closes)
        atr = calculate_atr(candles)

        if callback_data == "macd":
            direction = "HAUSSIER" if macd_line > signal_line else "BAISSIER"
            force = "FORT" if abs(histogram) > 1 else "FAIBLE"
            msg = (
                f"Analyse MACD - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"MACD Line : {macd_line}\n"
                f"Signal Line : {signal_line}\n"
                f"Histogramme : {histogram}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Direction : {direction}\n"
                f"Force du signal : {force}\n"
                f"{'MACD au dessus du signal - Momentum haussier' if macd_line > signal_line else 'MACD en dessous du signal - Momentum baissier'}"
            )
            send_telegram(msg)

        elif callback_data == "rsi":
            if rsi > 70:
                zone = "SURACHAT - Attention possible retournement baissier"
            elif rsi < 30:
                zone = "SURVENTE - Attention possible retournement haussier"
            else:
                zone = "NEUTRE - Zone ideale pour trader"
            msg = (
                f"Analyse RSI - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"RSI actuel : {rsi}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Zone : {zone}"
            )
            send_telegram(msg)

        elif callback_data == "ema":
            trend = "BULLISH" if ema9 > ema21 > sma50 else ("BEARISH" if ema9 < ema21 < sma50 else "MIXTE")
            msg = (
                f"Analyse EMA/SMA - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"EMA 9 : {ema9}\n"
                f"EMA 21 : {ema21}\n"
                f"SMA 50 : {sma50}\n"
                f"Prix actuel : {current_price}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Tendance globale : {trend}\n"
                f"{'EMA9 > EMA21 > SMA50 - Alignement parfait haussier' if trend == 'BULLISH' else 'EMA9 < EMA21 < SMA50 - Alignement parfait baissier' if trend == 'BEARISH' else 'Pas dalignement clair - Marche indecis'}"
            )
            send_telegram(msg)

        elif callback_data == "full":
            macd_dir = "HAUSSIER" if macd_line > signal_line else "BAISSIER"
            rsi_zone = "SURACHAT" if rsi > 70 else ("SURVENTE" if rsi < 30 else "NEUTRE")
            ema_trend = "BULLISH" if ema9 > ema21 else "BEARISH"
            fvg = detect_fvg(candles)
            ob = detect_ob(candles)
            score = 0
            if macd_dir == ema_trend:
                score += 25
            if rsi_zone == "NEUTRE":
                score += 25
            if fvg:
                score += 25
            if ob:
                score += 25
            msg = (
                f"Analyse Complete - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Prix : {current_price}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"MACD : {macd_dir}\n"
                f"RSI : {rsi} ({rsi_zone})\n"
                f"EMA Trend : {ema_trend}\n"
                f"FVG : {'Detecte - ' + str(fvg) if fvg else 'Aucun'}\n"
                f"OB : {'Detecte - ' + str(ob) if ob else 'Aucun'}\n"
                f"ATR : {atr}$\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Score marche : {score}/100\n"
                f"{'Conditions excellentes pour trader !' if score >= 75 else 'Conditions correctes' if score >= 50 else 'Conditions difficiles - Sois prudent'}"
            )
            send_telegram(msg)

        elif callback_data == "crt":
            msg = (
                f"Niveaux CRT actuels - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"CRT HIGH : {crt_high}\n"
                f"CRT LOW : {crt_low}\n"
                f"Prix actuel : {current_price}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Distance du HIGH : {round(crt_high - current_price, 2)}$\n"
                f"Distance du LOW : {round(current_price - crt_low, 2)}$"
            )
            send_telegram(msg)

        elif callback_data == "stats_day":
            msg = (
                f"Stats du jour - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Signaux total : {signal_count_today}\n"
                f"Breaks HIGH : {high_breaks_today}\n"
                f"Breaks LOW : {low_breaks_today}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Alertes actives : {'OUI' if not paused else 'NON - En pause'}\n"
                f"Mode nuit : {'ACTIF' if night_mode else 'INACTIF'}"
            )
            send_telegram(msg)

        elif callback_data == "stats_week":
            send_telegram(
                f"Stats semaine - XAUUSD\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Signaux aujourd'hui : {signal_count_today}\n"
                f"(Stats semaine completes bientot disponibles)\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Continue comme ca !"
            )

        elif callback_data == "quote":
            quote = random.choice(QUOTES)
            send_telegram(f"Conseil du jour\n━━━━━━━━━━━━━━━\n{quote}")

        elif callback_data == "pause":
            paused = True
            send_telegram("Alertes en pause - Appuie sur Reprendre pour reactiver")

        elif callback_data == "resume":
            paused = False
            send_telegram("Alertes reactives - Je surveille XAUUSD !")

        elif callback_data == "night_on":
            night_mode = True
            send_telegram("Mode nuit ON - Aucune alerte jusqu'a ce que tu le desactives")

        elif callback_data == "night_off":
            night_mode = False
            send_telegram("Mode nuit OFF - Alertes reactives !")

    except Exception as e:
        send_telegram(f"Erreur analyse : {e}")

def poll_updates():
    global last_offset
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"offset": last_offset + 1, "timeout": 10}
            r = requests.get(url, params=params, timeout=15)
            updates = r.json().get("result", [])
            for update in updates:
                last_offset = update["update_id"]
                if "callback_query" in update:
                    cb = update["callback_query"]
                    handle_callback(cb["data"], cb["id"])
                elif "message" in update:
                    text = update["message"].get("text", "").lower()
                    if text in ["/start", "/menu", "menu"]:
                        send_main_menu()
        except Exception as e:
            print(f"Erreur polling: {e}")
        time.sleep(2)

# Lancer le polling dans un thread separé
threading.Thread(target=poll_updates, daemon=True).start()

print("Bot CRT Ultimate demarre")
send_telegram("Bot CRT Ultimate active\nSurveillance XAUUSD M15 H24\n\nEnvoie /menu pour acceder aux boutons !")

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

        candles = get_candles(30)
        closes = [float(c["close"]) for c in reversed(candles)]
        prev = candles[1]
        current = candles[0]

        crt_high = round(float(prev["high"]), 2)
        crt_low = round(float(prev["low"]), 2)
        current_price = round(float(current["close"]), 2)
        atr = calculate_atr(candles)

        minutes_left = 15 - (current_minute % 15)
        alert_key = f"{crt_high}-{crt_low}"

        # Briefing matin 8h
        if current_hour == 8 and current_minute < 2 and not morning_sent:
            ema9 = calculate_ema(closes[-9:], 9)
            ema21 = calculate_ema(closes[-21:], 21)
            ema_dir = "BULLISH" if ema9 > ema21 else "BEARISH"
            rsi = calculate_rsi(closes)
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

        # Recap soir 22h
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

        # Signal BULLISH
        if not paused and not night_mode and current_price > crt_high and last_alert != f"HIGH-{alert_key}":
            signal_count_today += 1
            high_breaks_today += 1
            entry, sl, tp1, tp2 = get_sniper_entry(candles, "BULLISH", current_price, atr)
            rr1 = round(abs(tp1 - entry) / abs(entry - sl), 1) if abs(entry - sl) > 0 else 0
            rr2 = round(abs(tp2 - entry) / abs(entry - sl), 1) if abs(entry - sl) > 0 else 0
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
                f"RR : 1:{rr1} / 1:{rr2}"
            )
            send_telegram(msg)
            last_alert = f"HIGH-{alert_key}"
            print(msg)

        # Signal BEARISH
        elif not paused and not night_mode and current_price < crt_low and last_alert != f"LOW-{alert_key}":
            signal_count_today += 1
            low_breaks_today += 1
            entry, sl, tp1, tp2 = get_sniper_entry(candles, "BEARISH", current_price, atr)
            rr1 = round(abs(entry - tp1) / abs(sl - entry), 1) if abs(sl - entry) > 0 else 0
            rr2 = round(abs(entry - tp2) / abs(sl - entry), 1) if abs(sl - entry) > 0 else 0
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
                f"RR : 1:{rr1} / 1:{rr2}"
            )
            send_telegram(msg)
            last_alert = f"LOW-{alert_key}"
            print(msg)

        else:
            print(f"[{now.strftime('%H:%M:%S')}] HIGH: {crt_high} | LOW: {crt_low} | Prix: {current_price} | Signals: {signal_count_today}")

        time.sleep(15)

    except Exception as e:
        print(f"Erreur: {e}")
        time.sleep(15)
