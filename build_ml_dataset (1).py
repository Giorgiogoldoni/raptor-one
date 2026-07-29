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

v2: aggiunta ampiezza di mercato (breadth) come feature di regime — quanti
ticker dell'universo sono in BUY vs EXIT quel giorno, e rendimento medio
dell'universo nei 5gg precedenti. Richiede due passate: la prima raccoglie
segnale/rendimento per tutti i ticker (serve per calcolare la breadth per
data), la seconda usa quella mappa per arricchire gli eventi.
"""
import json, time, csv
from collections import defaultdict
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

def fetch_ticker_series(info):
    """Passata 1: scarica e calcola dati/indicatori per un ticker. Ritorna
    None se non disponibile, altrimenti un dict con tutto il necessario per
    la passata 2 (eventi) e per la mappa di ampiezza di mercato."""
    symbol = info['y']
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period='1y', interval='1d', timeout=20)
        if hist.empty or len(hist) < 60:
            return None

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

        return {
            'ticker': info['t'], 'dates': dates, 'closes': closes, 'vols': vols,
            'er': er_arr, 'baff': baff_arr, 'rsi': rsi_arr, 'ao': ao_arr,
            'cross': cross_arr, 'mm': mm_arr, 'segnale': segnale_arr, 'atr': atr,
        }
    except Exception as e:
        print(f"  ERR {symbol}: {e}")
        return None

def build_breadth_map(all_series):
    """Per ogni data presente, calcola: frazione di ticker in BUY, frazione
    in EXIT, rendimento medio giornaliero dell'universo (equal-weight).
    Poi deriva anche il rendimento medio dell'universo sui 5gg precedenti
    per ogni data — il vero segnale di 'regime' da usare come feature."""
    by_date_buy = defaultdict(int)
    by_date_exit = defaultdict(int)
    by_date_n = defaultdict(int)
    by_date_ret = defaultdict(list)

    for s in all_series:
        closes = s['closes']; dates = s['dates']; seg = s['segnale']
        for i, d in enumerate(dates):
            by_date_n[d] += 1
            if seg[i] in ('BUY1','BUY2','BUY3'): by_date_buy[d] += 1
            elif seg[i] in ('EXIT1','EXIT2'): by_date_exit[d] += 1
            if i > 0 and closes[i-1]:
                by_date_ret[d].append(closes[i]/closes[i-1]-1)

    all_dates = sorted(by_date_n.keys())
    breadth_buy = {}; breadth_exit = {}; mkt_ret = {}
    for d in all_dates:
        n = by_date_n[d] or 1
        breadth_buy[d] = round(by_date_buy[d]/n, 4)
        breadth_exit[d] = round(by_date_exit[d]/n, 4)
        rets = by_date_ret[d]
        mkt_ret[d] = round(sum(rets)/len(rets)*100, 4) if rets else 0.0

    # Rendimento medio universo sui 5gg precedenti (trailing, per data)
    mkt_ret_5d = {}
    for idx, d in enumerate(all_dates):
        window = [mkt_ret[all_dates[j]] for j in range(max(0,idx-4), idx+1)]
        mkt_ret_5d[d] = round(sum(window)/len(window), 4) if window else 0.0

    return breadth_buy, breadth_exit, mkt_ret_5d

def extract_events(s, breadth_buy, breadth_exit, mkt_ret_5d):
    closes = s['closes']; dates = s['dates']; vols = s['vols']
    er_arr = s['er']; baff_arr = s['baff']; rsi_arr = s['rsi']; ao_arr = s['ao']
    cross_arr = s['cross']; mm_arr = s['mm']; segnale_arr = s['segnale']; atr = s['atr']

    events = []
    n = len(closes)
    i = 0
    prev_seg = None
    while i < n:
        seg = segnale_arr[i]
        if seg in ('BUY1','BUY2') and seg != prev_seg:
            entry_i = i
            entry_tier = seg
            exit_i = None
            j = i+1
            while j < n:
                if segnale_arr[j] in ('EXIT1','EXIT2'):
                    exit_i = j
                    break
                j += 1
            if exit_i is None:
                i += 1; prev_seg = seg; continue
            if has_anomalous_jump(closes, entry_i, exit_i):
                i = exit_i+1; prev_seg = segnale_arr[exit_i] if exit_i < n else None; continue

            entry_price = closes[entry_i]
            exit_price = closes[exit_i]
            ret = (exit_price/entry_price - 1)*100 if entry_price else 0
            window = closes[entry_i:exit_i+1]
            peak_i = max(range(len(window)), key=lambda k: window[k])
            peak_ret = (window[peak_i]/entry_price - 1)*100 if entry_price else 0
            days_to_peak = peak_i
            hold_days = exit_i - entry_i
            d = dates[entry_i]

            events.append({
                'ticker': s['ticker'], 'entry_date': d,
                'entry_tier': entry_tier,
                'er': er_arr[entry_i], 'baff': baff_arr[entry_i],
                'rsi': rsi_arr[entry_i] if rsi_arr[entry_i] is not None else '',
                'ao': ao_arr[entry_i] if ao_arr[entry_i] is not None else '',
                'cross_days': cross_arr[entry_i], 'mm_align': int(mm_arr[entry_i]),
                'atr_pct': round(atr/entry_price*100,3) if atr and entry_price else '',
                'vol_ratio': round(vols[entry_i]/(sum(vols[max(0,entry_i-20):entry_i])/max(1,min(20,entry_i)) or 1),3) if entry_i>0 else '',
                'breadth_buy': breadth_buy.get(d, ''),
                'breadth_exit': breadth_exit.get(d, ''),
                'mkt_ret_5d': mkt_ret_5d.get(d, ''),
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

def main():
    print("Passata 1/2: scarico e calcolo indicatori per tutti i ticker...")
    all_series = []
    ok = 0; errors = 0
    for i, info in enumerate(TICKERS):
        s = fetch_ticker_series(info)
        if s: all_series.append(s); ok += 1
        else: errors += 1
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(TICKERS)} — ok:{ok} errori:{errors}")
        time.sleep(0.3)
    print(f"Passata 1 completata: {ok} ticker ok, {errors} errori\n")

    print("Costruisco la mappa di ampiezza di mercato (breadth) per data...")
    breadth_buy, breadth_exit, mkt_ret_5d = build_breadth_map(all_series)
    print(f"Date coperte: {len(breadth_buy)}\n")

    print("Passata 2/2: estraggo gli eventi BUY1/BUY2 con le feature di regime...")
    all_events = []
    for s in all_series:
        all_events.extend(extract_events(s, breadth_buy, breadth_exit, mkt_ret_5d))

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
