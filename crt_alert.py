candle_range = round(crt_high - crt_low, 2)

        # Calcul indicateurs
        ema9 = calculate_ema(closes[-9:], 9)
        ema21 = calculate_ema(closes[-21:], 21)
        ema50 = calculate_ema(closes[-50:] if len(closes) >= 50 else closes, 50)
        rsi = calculate_rsi(closes)
        atr = calculate_atr(candles)

        minutes_left = 15 - (current_minute % 15)
        alert_key = f"{crt_high}-{crt_low}"

        # Briefing matin 8h00
        if current_hour == 8 and current_minute < 2 and not morning_sent:
            ema_dir = "📈 BULLISH" if ema9 > ema21 else "📉 BEARISH"
            msg = f"🌅 <b>GOOD MORNING TRADER</b>\n━━━━━━━━━━━━━━━\n💎 XAUUSD — Setup du jour\n🔺 CRT HIGH : {crt_high}\n🔻 CRT LOW : {crt_low}\n📊 Bias EMA : {ema_dir}\n📈 RSI : {rsi}\n🕐 Session London dans 1h\n━━━━━━━━━━━━━━━\n🧠 Reste patient, attends le setup !\n💪 <b>Today we eat !</b>"
            send_telegram(msg)
            morning_sent = True

        # Lundi motivation
        if weekday == 0 and current_hour == 8 and current_minute < 2 and not monday_sent:
            send_telegram("💥 <b>MONDAY — ON EST BACK</b>\n━━━━━━━━━━━━━━━\n🔥 Nouvelle semaine\n💎 Nouveaux setups\n🎯 Cette semaine on performe !\n━━━━━━━━━━━━━━━\n🚀 Let's get it !")
            monday_sent = True

        # Vendredi soir
        if weekday == 4 and current_hour == 20 and current_minute < 2 and not friday_sent:
            send_telegram("🎉 <b>WEEKEND MODE</b>\n━━━━━━━━━━━━━━━\n📊 Semaine terminée\n🧠 Analyse tes trades\n🔥 Recharge les batteries !\n━━━━━━━━━━━━━━━\n💤 Bonne fin de semaine !")
            friday_sent = True

        # Recap soir 22h00
        if current_hour == 22 and current_minute < 2 and not evening_sent:
            msg = f"🌙 <b>DAILY RECAP — XAUUSD</b>\n━━━━━━━━━━━━━━━\n📊 Signaux aujourd'hui : {signal_count_today}\n🔺 Breaks HIGH : {high_breaks_today}\n🔻 Breaks LOW : {low_breaks_today}\n━━━━━━━━━━━━━━━\n💤 Repose toi bien\n🔥 Demain on est back !"
            send_telegram(msg)
            evening_sent = True

        # Gros move détecté
        if last_price and abs(current_price - last_price) > 30:
            move = round(abs(current_price - last_price), 2)
            direction = "📈" if current_price > last_price else "📉"
            send_telegram(f"💥 <b>GROS MOVE XAUUSD !</b>\n━━━━━━━━━━━━━━━\n{direction} Move de +{move}$ détecté !\n💰 Prix actuel : {current_price}\n━━━━━━━━━━━━━━━\n🔥 Marché très actif !")

        # Marché trop calme
        if candle_range < 3 and last_calm_alert != alert_key:
            send_telegram(f"😴 <b>MARCHÉ TROP CALME</b>\n━━━━━━━━━━━━━━━\n📏 Range M15 : seulement {candle_range}$\n⚠️ Pas idéal pour trader\n━━━━━━━━━━━━━━━\n🧘 Attends un meilleur setup !")
            last_calm_alert = alert_key

        # Alerte préventive HIGH
        dist_high = round(crt_high - current_price, 2)
        dist_low = round(current_price - crt_low, 2)

        if 0 < dist_high <= 3 and last_warning != f"WARN-HIGH-{alert_key}":
            send_telegram(f"⚠️ <b>ATTENTION TRADER !</b>\n━━━━━━━━━━━━━━━\n👀 Prix s'approche du CRT HIGH\n🔺 CRT HIGH : {crt_high}\n📍 Prix actuel : {current_price}\n📏 Distance : {dist_high}$\n━━━━━━━━━━━━━━━\n🎯 PRÉPARE TOI — Sa va casser !\n👁️ Garde l'œil sur M1 !")
            last_warning = f"WARN-HIGH-{alert_key}"

        # Alerte préventive LOW
        if 0 < dist_low <= 3 and last_warning != f"WARN-LOW-{alert_key}":
            send_telegram(f"⚠️ <b>ATTENTION TRADER !</b>\n━━━━━━━━━━━━━━━\n👀 Prix s'approche du CRT LOW\n🔻 CRT LOW : {crt_low}\n📍 Prix actuel : {current_price}\n📏 Distance : {dist_low}$\n━━━━━━━━━━━━━━━\n🎯 PRÉPARE TOI — Sa va casser !\n👁️ Garde l'œil sur M1 !")
            last_warning = f"WARN-LOW-{alert_key}"

        # Retest HIGH
        if last_alert == f"HIGH-{alert_key}" and current_price <= crt_high and current_price > crt_high - 2:
            send_telegram(f"🔄 <b>RETEST EN COURS !</b>\n━━━━━━━━━━━━━━━\n💰 Prix reteste le CRT HIGH\n📍 Niveau : {crt_high}\n💰 Prix actuel : {current_price}\n━━━━━━━━━━━━━━━\n🎯 Deuxième chance d'entrée !")

        # Retest LOW
        if last_alert == f"LOW-{alert_key}" and current_price >= crt_low and current_price < crt_low + 2:
            send_telegram(f"🔄 <b>RETEST EN COURS !</b>\n━━━━━━━━━━━━━━━\n💰 Prix reteste le CRT LOW\n📍 Niveau : {crt_low}\n💰 Prix actuel : {current_price}\n━━━━━━━━━━━━━━━\n🎯 Deuxième chance d'entrée !")

        # SIGNAL BULLISH
        if current_price > crt_high and last_alert != f"HIGH-{alert_key}":
            signal_count_today += 1
            high_breaks_today += 1
            entry, sl, tp1, tp2, confirmations = get_sniper_entry(candles, "BULLISH", current_price, atr)
            rr1 = round(abs(tp1 - entry) / abs(entry - sl), 1)
            rr2 = round(abs(tp2 - entry) / abs(entry - sl), 1)
            ema_conf = "✅ EMAs alignées haussier" if ema9 > ema21 else "⚠️ EMAs pas alignées"
            rsi_conf = "✅ RSI neutre" if 30 < rsi < 70 else f"⚠️ RSI {rsi} — Zone extrême"
            conf_list = "\n".join(confirmations) if confirmations else ""
            risk_warning = f"\n⚠️ <b>Attention</b> : {signal_count_today} signaux aujourd'hui !" if signal_count_today >= 3 else ""
            quote = random.choice(QUOTES)
            msg = f"🚨 <b>SIGNAL CRT — XAUUSD</b>\n━━━━━━━━━━━━━━━\n💥 BREAK CRT HIGH — {crt_high}\n⏰ {now.strftime('%H:%M')} — M15\n📈 Direction : BULLISH\n⏳ Prochaine bougie : {minutes_left} min\n━━━━━━━━━━━━━━━\n🦅 <b>SNIPER ENTRY</b>\n📍 BUY : {entry}\n🎯 TP1 : {tp1} (+{round(tp1-entry,2)}$)\n🎯 TP2 : {tp2} (+{round(tp2-entry,2)}$)\n🛑 SL : {sl} (-{round(entry-sl,2)}$)\n📊 RR : 1:{rr1} / 1:{rr2}\n━━━━━━━━━━━━━━━\n{ema_conf}\n{rsi_conf}\n{conf_list}{risk_warning}\n━━━━━━━━━━━━━━━\n🎯 <b>FILE SUR M1 !</b>\n{quote}"
            send_telegram(msg)
            send_telegram("🎯 As-tu pris ce trade ?\nRéponds <b>OUI</b> ou <b>NON</b>")
            last_alert = f"HIGH-{alert_key}"
            print(msg)

        # SIGNAL BEARISH
        elif current_price < crt_low and last_alert != f"LOW-{alert_key}":
            signal_count_today += 1
            low_breaks_today += 1
            entry, sl, tp1, tp2, confirmations = get_sniper_entry(candles, "BEARISH", current_price, atr)
            rr1 = round(abs(entry - tp1) / abs(sl - entry), 1)
            rr2 = round(abs(entry - tp2) / abs(sl - entry), 1)
            ema_conf = "✅ EMAs alignées baissier" if ema9 < ema21 else "⚠️ EMAs pas alignées"
            rsi_conf = "✅ RSI neutre" if 30 < rsi < 70 else f"⚠️ RSI {rsi} — Zone extrême"
            conf_list = "\n".join(confirmations) if confirmations else ""
            risk_warning = f"\n⚠️ <b>Attention</b> : {signal_count_today} signaux aujourd'hui !" if signal_count_today >= 3 else ""
            quote = random.choice(QUOTES)
            msg = f"🚨 <b>SIGNAL CRT — XAUUSD</b>\n━━━━━━━━━━━━━━━\n💥 BREAK CRT LOW — {crt_low}\n⏰ {now.strftime('%H:%M')} — M15\n📉 Direction : BEARISH\n⏳ Prochaine bougie : {minutes_left} min\n━━━━━━━━━━━━━━━\n🦅 <b>SNIPER ENTRY</b>\n📍 SELL : {entry}\n🎯 TP1 : {tp1} (-{round(entry-tp1,2)}$)\n🎯 TP2 : {tp2} (-{round(entry-tp2,2)}$)\n🛑 SL : {sl} (+{round(sl-entry,2)}$)\n📊 RR : 1:{rr1} / 1:{rr2}\n━━━━━━━━━━━━━━━\n{ema_conf}\n{rsi_conf}\n{conf_list}{risk_warning}\n━━━━━━━━━━━━━━━\n🎯 <b>FILE SUR M1 !</b>\n{quote}"
            send_telegram(msg)
            send_telegram("🎯 As-tu pris ce trade ?\nRéponds <b>OUI</b> ou <b>NON</b>")
            last_alert = f"LOW-{alert_key}"
            print(msg)

        else:
            print(f"[{now.strftime('%H:%M:%S')}] HIGH: {crt_high} | LOW: {crt_low} | Prix: {current_price} | EMA9: {ema9} | RSI: {rsi} | Signals: {signal_count_today}")

        last_price = current_price
        time.sleep(60)

    except Exception as e:
        print(f"Erreur: {e}")
        time.sleep(60)
