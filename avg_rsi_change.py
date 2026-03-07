import numpy as np
import pandas as pd
import requests
import uuid

API_KEY  = "PUBLIC KEY"
USER_KEY = "GENERATED KEY"
BASE_URL = "https://public-api.etoro.com/api/v1"


RSI_PERIOD = 14


def headers():
    return {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key":    API_KEY,
        "x-user-key":   USER_KEY,
    }


def get_instrument_id(ticker):
    url = f"{BASE_URL}/market-data/search"
    r = requests.get(url, headers=headers(), params={"internalSymbolFull": ticker})
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "items" in data and data["items"]:
        inst = data["items"][0]
        iid  = inst.get("internalInstrumentId") or inst.get("InstrumentID") or inst.get("instrumentId")
        if iid:
            print(f"✓ Found: {inst.get('internalInstrumentDisplayName', ticker)}  |  ID: {iid}")
            return int(iid)
    raise Exception(f"Instrument not found: {ticker}")


def get_ohlc_data(ticker, timeframe="1d", limit=1000):
    iid = get_instrument_id(ticker)
    tf_map = {
        "1m": "OneMinute", "5m": "FiveMinutes", "10m": "TenMinutes",
        "15m": "FifteenMinutes", "30m": "ThirtyMinutes", "1h": "OneHour",
        "4h": "FourHours", "1d": "OneDay", "1w": "OneWeek",
    }
    interval = tf_map.get(timeframe, "OneDay")
    url = f"{BASE_URL}/market-data/instruments/{iid}/history/candles/asc/{interval}/{min(limit, 1000)}"
    r = requests.get(url, headers=headers())
    r.raise_for_status()
    data = r.json()

    rows = []
    for ic in data.get("candles", []):
        for c in ic.get("candles", []):
            rows.append({
                "datetime": c.get("fromDate"),
                "close":    c.get("close"),
            })

    if not rows:
        raise Exception("No candle data found")

    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"✓ Fetched {len(df)} candles  ({df['datetime'].iloc[0].date()} -> {df['datetime'].iloc[-1].date()})")
    return df


def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's smoothed RSI using numpy (avoids pandas iloc write-back issues)."""
    arr = closes.values.astype(float)
    n   = len(arr)
    out = np.full(n, np.nan)

    if n < period + 1:
        return pd.Series(out, index=closes.index)

    deltas = np.diff(arr)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Seed with simple mean of first `period` changes
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    out[period] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))

    # Wilder smoothing for the rest
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i]   = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))

    return pd.Series(out, index=closes.index)


def analyze_rsi_changes(df: pd.DataFrame, rsi_period: int = 14, analysis_window: int = 14):
    df = df.copy()
    df["rsi"] = compute_rsi(df["close"], rsi_period)
    df = df.dropna(subset=["rsi"]).reset_index(drop=True)
    df["rsi_change"] = df["rsi"].diff()
    df = df.dropna(subset=["rsi_change"]).reset_index(drop=True)

    # Limit analysis to last `analysis_window` candles only
    df = df.tail(analysis_window).reset_index(drop=True)

    if df.empty:
        print("\n  Not enough candles to compute RSI. Need at least 15.\n")
        return None, None

    increases = df.loc[df["rsi_change"] > 0, "rsi_change"]
    decreases = df.loc[df["rsi_change"] < 0, "rsi_change"]

    avg_increase = increases.mean() if not increases.empty else 0
    avg_decrease = decreases.mean() if not decreases.empty else 0

    print(f"\n{'='*60}")
    print(f"  RSI({rsi_period}) CHANGE ANALYSIS  —  Last {analysis_window} candles")
    print(f"{'='*60}")
    print(f"  Total candles analysed : {len(df)}")
    print(f"  Rising  RSI sessions   : {len(increases)}  ({len(increases)/len(df):.1%})")
    print(f"  Falling RSI sessions   : {len(decreases)}  ({len(decreases)/len(df):.1%})")
    print(f"  Flat    RSI sessions   : {len(df) - len(increases) - len(decreases)}")
    print(f"\n  Avg RSI INCREASE  : +{avg_increase:.4f} pts")
    print(f"  Avg RSI DECREASE  :  {avg_decrease:.4f} pts")
    print(f"\n  Max single increase : +{increases.max():.4f} pts")
    print(f"  Max single decrease :  {decreases.min():.4f} pts")
    print(f"\n  Current RSI         :  {df['rsi'].iloc[-1]:.2f}")
    print(f"  Last RSI change     :  {df['rsi_change'].iloc[-1]:+.4f} pts")
    print(f"{'='*60}\n")

    return avg_increase, abs(avg_decrease)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  RSI AVERAGE INCREASE / DECREASE ANALYZER")
    print("="*60 + "\n")

    ticker    = input("Ticker (NVDA): ").strip().upper() or "NVDA"
    timeframe = input("Timeframe (1d): ").strip().lower() or "1d"

    try:
        df = get_ohlc_data(ticker, timeframe, limit=1000)
        analyze_rsi_changes(df, RSI_PERIOD, analysis_window=14)
    except Exception as e:
        print(f"\n  Error: {e}\n")
        import traceback
        traceback.print_exc()
