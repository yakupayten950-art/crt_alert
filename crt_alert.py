import requests
import time
from datetime import datetime

TOKEN = "8671433198:AAEftUbbKOcuStOiH5FozZR_5zTPTPhP02E"
CHAT_ID = "7329783593"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

def get_xauusd_m15():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 3,
        "apikey": "5a9a64f5f7ba46c79d17c50b1a3a485d"
    }
    r = requests.get(url, params=params)
    data = r.json()
    candles = data["values"]
    return candles

last_alert = None

print("✅ Script CRT démarré - Surveillance XAUUSD M15")
send_telegram("✅ Script CRT démarré - Surveillance XAUUSD M15 active !")

while True:
    try:
        candles = get_xauusd_m15()
        prev = candles[1]
        current = candles[0]

        crt_high = round(float(prev["high"]), 2)
        crt_low = round(float(prev["low"]), 2)
        current_price = round(float(current["close"]), 2)

        alert_key = f"{crt_high}-{crt_low}"

        if current_price > crt_high and last_alert != f"HIGH-{alert_key}":
            msg = f"🚨 XAUUSD M15\nPrix a cassé le CRT HIGH à {crt_high}\nPrix actuel : {current_price}\n→ Check ton M1 pour l'entrée sniper !"
            send_telegram(msg)
            last_alert = f"HIGH-{alert_key}"
            print(msg)

        elif current_price < crt_low and last_alert != f"LOW-{alert_key}":
            msg = f"🚨 XAUUSD M15\nPrix a cassé le CRT LOW à {crt_low}\nPrix actuel : {current_price}\n→ Check ton M1 pour l'entrée sniper !"
            send_telegram(msg)
            last_alert = f"LOW-{alert_key}"
            print(msg)

        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CRT HIGH: {crt_high} | CRT LOW: {crt_low} | Prix: {current_price}")

        time.sleep(60)

    except Exception as e:
        print(f"Erreur: {e}")
        time.sleep(60)
