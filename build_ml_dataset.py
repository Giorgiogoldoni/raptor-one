#!/usr/bin/env python3
"""
build_ml_dataset.py — RAPTOR ONE
Costruisce il dataset di training per il modello ML a partire dagli eventi
storici BUY1/BUY2: per ognuno individua l'esito (fino a quando il segnale
si inverte in EXIT1/EXIT2), estrae le feature al momento dell'ingresso e
salva un CSV compatto.

Da lanciare MANUALMENTE (locale o Action ad hoc) — non fa parte del
workflow live raptor_chart_fetch.py. Output: ml_dataset.csv

Filtro anti-discontinuità: scarta un evento se, nella finestra tra entrata
e uscita, il prezzo fa un salto giorno-su-giorno >2.5x o <0.4x (tipico di
rebase/split ETP non allineati da Yahoo — stesso fix già applicato su
raptor-leva).
"""
import json, time, csv
import yfinance as yf

# Riusa la stessa identica lista ticker e le stesse funzioni indicatori
# di raptor_chart_fetch.py (copia-incolla diretta per restare autosufficiente)
from raptor_chart_fetch import (
    TICKERS, calc_kama, calc_sar_array, calc_ao_array, calc_rsi_array,
    calc_er_array, calc_baffetti_array, calc_mm_align_array,
    calc_cross_days_array, calc_ao_improving_array, calc_segnale_array,
    calc_atr,
)

JUMP_HIGH = 2.5   # rapporto giorno-su-giorno oltre il quale è "salto anomalo"
JUMP_LOW  = 0.4

def has_anomalous_jump(closes, i0, i1):
    """True se tra i0 e i1 (inclusi) c'è un salto di prezzo anomalo giorno-su-giorno."""
    for i in range(max(i0,1), i1+1):
        if closes[i-1] == 0: continue
        ratio = closes[i]/closes[i-1]
        if ratio > JUMP_HIGH or ratio < JUMP_LOW:
            return True
    return False

def process_ticker(info):
    symbol = info['y']
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period='1y', interval='1d', timeout=20)
        if hist.empty or len(hist) < 60:
            return []

        opens  = [round(float(x),4) for x in hist['Open'].values]
        highs  = [round(float(x),4) for x in hist['High'].values]
        lows   = [round(float(x),4) for x in hist['Low'].values]
        closes = [round(float(x),4) for x in hist['Close'].values]
        vols   = [int(x) for x in hist['Volume'].values]
        dates  = [ts.strftime('%Y-%m-%d') for ts in hist.index]

        kama_arr = calc_kama(closes)
        sar_arr, sarBull_arr = calc_sar_array(highs, lows)
        ao_arr = calc_ao_array(highs, lows)
        rsi_arr = calc_rsi_array(closes)
        er_arr = calc_er_array(closes)
        baff_arr = calc_baffetti_array(highs, lows)
        mm_arr = calc_mm_align_array(closes)
        cross_arr = calc_cross_days_array(closes, kama_arr)
        ao_imp_arr = calc_ao_improving_array(ao_arr)
        segnale_arr = calc_segnale_array(closes, kama_arr, er_arr, baff_arr, ao_imp_arr,
                                          sarBull_arr, cross_arr, mm_arr, rsi_arr)
        atr = calc_atr(highs, lows, closes, 14)

        events = []
        n = len(closes)
        i = 0
        prev_seg = None
        while i < n:
            seg = segnale_arr[i]
            # Nuovo ingresso: flip verso BUY1/BUY2 da qualcos'altro
            if seg in ('BUY1','BUY2') and seg != prev_seg:
                entry_i = i
                entry_tier = seg
                # Cerca in avanti il primo EXIT1/EXIT2
                exit_i = None
                j = i+1
                while j < n:
                    if segnale_arr[j] in ('EXIT1','EXIT2'):
                        exit_i = j
                        break
                    j += 1
                if exit_i is None:
                    # Evento ancora aperto a fine storico: censurato, escluso dal training
                    i += 1
                    prev_seg = seg
                    continue
                if has_anomalous_jump(closes, entry_i, exit_i):
                    i = exit_i+1
                    prev_seg = segnale_arr[exit_i] if exit_i < n else None
                    continue

                entry_price = closes[entry_i]
                exit_price = closes[exit_i]
                ret = (exit_price/entry_price - 1)*100 if entry_price else 0
                # Rendimento massimo raggiunto nella finestra (per il target "uscita ottimale")
                window = closes[entry_i:exit_i+1]
                peak_i = max(range(len(window)), key=lambda k: window[k])
                peak_ret = (window[peak_i]/entry_price - 1)*100 if entry_price else 0
                days_to_peak = peak_i
                hold_days = exit_i - entry_i

                events.append({
                    'ticker': info['t'], 'entry_date': dates[entry_i],
                    'entry_tier': entry_tier,
                    'er': er_arr[entry_i], 'baff': baff_arr[entry_i],
                    'rsi': rsi_arr[entry_i] if rsi_arr[entry_i] is not None else '',
                    'ao': ao_arr[entry_i] if ao_arr[entry_i] is not None else '',
                    'cross_days': cross_arr[entry_i], 'mm_align': int(mm_arr[entry_i]),
                    'atr_pct': round(atr/entry_price*100,3) if atr and entry_price else '',
                    'vol_ratio': round(vols[entry_i]/(sum(vols[max(0,entry_i-20):entry_i])/max(1,min(20,entry_i)) or 1),3) if entry_i>0 else '',
                    'hold_days': hold_days,
                    'return_pct': round(ret,3),
                    'success': 1 if ret > 0 else 0,
                    'peak_return_pct': round(peak_ret,3),
                    'days_to_peak': days_to_peak,
                })
                i = exit_i+1
                prev_seg = segnale_arr[exit_i] if exit_i < n else None
                continue
            prev_seg = seg
            i += 1

        return events
    except Exception as e:
        print(f"  ERR {symbol}: {e}")
        return []

def main():
    all_events = []
    ok = 0; errors = 0
    for i, info in enumerate(TICKERS):
        events = process_ticker(info)
        all_events.extend(events)
        if events: ok += 1
        else: errors += 1
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(TICKERS)} — ticker ok:{ok} vuoti/errori:{errors} — eventi finora:{len(all_events)}")
        time.sleep(0.3)

    if not all_events:
        print("Nessun evento raccolto.")
        return

    fields = list(all_events[0].keys())
    with open('ml_dataset.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_events)

    print(f"\n✅ Salvato ml_dataset.csv — {len(all_events)} eventi da {ok} ticker")
    succ = sum(e['success'] for e in all_events)
    print(f"Successi: {succ}/{len(all_events)} ({succ/len(all_events)*100:.1f}%)")

if __name__ == '__main__':
    main()
