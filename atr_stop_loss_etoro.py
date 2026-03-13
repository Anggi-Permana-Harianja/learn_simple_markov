import requests
import numpy as np
import uuid

# ─────────────────────────────────────────────
#  CONFIG — paste your eToro API keys here
# ─────────────────────────────────────────────
API_KEY  = "YOUR API KEY"
USER_KEY = "YOUR USER KEY"

BASE_URL = "https://public-api.etoro.com/api/v1"

HEADERS = {
    "x-api-key"    : API_KEY,
    "x-user-key"   : USER_KEY,
    "x-request-id" : str(uuid.uuid4()),
}

def get_instrument_id(ticker):
    url    = f"{BASE_URL}/market-data/search"
    params = {"internalSymbolFull": ticker.upper(), "fields": "instrumentId,internalSymbolFull,displayName"}
    resp   = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    data   = resp.json()
    items  = data.get("items") or data.get("instruments") or data.get("data") or []
    if not items:
        raise ValueError(f"No instrument found for {ticker}")
    return int(items[0]["instrumentId"])


def get_candles(instrument_id, interval="OneDay", count=20):
    url  = f"{BASE_URL}/market-data/instruments/{instrument_id}/history/candles/desc/{interval}/{count}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    raw  = resp.json()
    # eToro structure: { "candles": [ { "instrumentId": ..., "candles": [ {OHLC}, ... ] } ] }
    outer = raw.get("candles", [])
    if outer and isinstance(outer[0], dict) and "candles" in outer[0]:
        return outer[0]["candles"]
    return outer


def calculate_atr(candles, period=14):
    candles = sorted(candles, key=lambda c: c.get("fromDate") or c.get("timestamp") or 0)
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]
    closes = [float(c["close"]) for c in candles]

    tr_list = []
    for i in range(1, len(closes)):
        tr_list.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i]  - closes[i-1])
        ))

    atr = float(np.mean(tr_list[:period]))
    for tr in tr_list[period:]:
        atr = (atr * (period - 1) + tr) / period

    return atr, closes[-1]


def print_results(ticker, current_price, atr, period=14, mult=2):
    print("\n" + "="*50)
    print(f"    📊 ATR STOP LOSS CALCULATOR (eToro API)")
    print("="*50)
    print(f"\n  🔍 Ticker        : {ticker.upper()}")
    print(f"  💰 Current Price : ${current_price:.2f}")
    print(f"  📐 ATR ({period})     : ${atr:.2f}")
    print("="*50)

    print("\n  🎯 SHORT Stop Loss (above price)")
    print("-"*50)
    for m in [1, 1.5, 2, 2.5, 3]:
        stop = current_price + (m * atr)
        pct  = (m * atr / current_price) * 100
        tag  = "  ✅ RECOMMENDED" if m == mult else ""
        print(f"  {m}x ATR → ${stop:.2f}  (+{pct:.2f}%){tag}")

    print("\n  🎯 LONG Stop Loss (below price)")
    print("-"*50)
    for m in [1, 1.5, 2, 2.5, 3]:
        stop = current_price - (m * atr)
        pct  = (m * atr / current_price) * 100
        tag  = "  ✅ RECOMMENDED" if m == mult else ""
        print(f"  {m}x ATR → ${stop:.2f}  (-{pct:.2f}%){tag}")

    short_stop    = current_price + (mult * atr)
    stop_dist_pct = (mult * atr / current_price) * 100

    print(f"\n  ⚡ LEVERAGE IMPACT (SHORT stop = ${short_stop:.2f})")
    print("-"*50)
    for lev in [1, 2, 3, 5, 10]:
        loss    = stop_dist_pct * lev
        warning = " ☠️" if loss > 40 else (" ⚠️" if loss > 20 else "")
        print(f"  {lev:>2}x leverage → Capital loss: {loss:.1f}%{warning}")

    print("\n" + "="*50)
    print(f"  ✅ RECOMMENDED STOP (SHORT, 2x ATR) → ${short_stop:.2f}")
    print("="*50 + "\n")


if __name__ == "__main__":
    ticker   = input("Enter ticker (e.g. KMI, AAPL, TSLA): ").strip().upper()
    interval = input("Interval [OneDay/OneHour/FourHours] (default=OneDay): ").strip() or "OneDay"
    period   = int(input("ATR period (default=14): ").strip() or 14)

    print("\n⏳ Fetching data from eToro API...")
    try:
        iid                = get_instrument_id(ticker)
        print(f"  ✅ Instrument ID : {iid}")
        candles            = get_candles(iid, interval=interval, count=period + 5)
        atr, current_price = calculate_atr(candles, period=period)
        print_results(ticker, current_price, atr, period=period)
    except requests.HTTPError as e:
        print(f"\n❌ API Error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        import traceback; traceback.print_exc()
