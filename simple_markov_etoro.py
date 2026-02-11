import numpy as np
import pandas as pd
import requests
import uuid
from collections import defaultdict
from datetime import datetime
import pytz

API_KEY = "YOUR_API_KEY_HERE"
USER_KEY = "YOUR_USER_KEY_HERE"
BASE_URL = "https://public-api.etoro.com/api/v1"

def headers():
    return {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": API_KEY,
        "x-user-key": USER_KEY,
    }

def is_us_market_open():
    """
    Check if US stock market is currently open.
    
    Market hours: 9:30 AM - 4:00 PM EST, Monday-Friday
    """
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    
    # Check if weekend
    if now_est.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Check market hours (9:30 AM - 4:00 PM EST)
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now_est <= market_close

def get_instrument_id(ticker):
    url = f"{BASE_URL}/market-data/search"
    r = requests.get(url, headers=headers(), params={"internalSymbolFull": ticker})
    r.raise_for_status()
    data = r.json()
    
    if isinstance(data, dict) and 'items' in data and len(data['items']) > 0:
        instrument = data['items'][0]
        instrument_id = (
            instrument.get("internalInstrumentId") or 
            instrument.get("InstrumentID") or 
            instrument.get("instrumentId")
        )
        if instrument_id:
            name = instrument.get("internalInstrumentDisplayName", ticker)
            print(f"✓ Found: {name}")
            print(f"✓ Instrument ID: {instrument_id}")
            return int(instrument_id)
    
    raise Exception(f"Instrument not found: {ticker}")

def get_ohlc_data(ticker, timeframe="1d", limit=1000):
    print(f"\n{'='*70}")
    print(f"Fetching {limit} candles for {ticker}...")
    print(f"{'='*70}\n")
    
    instrument_id = get_instrument_id(ticker)
    
    timeframe_map = {
        "1m": "OneMinute", "5m": "FiveMinutes", "10m": "TenMinutes",
        "15m": "FifteenMinutes", "30m": "ThirtyMinutes", "1h": "OneHour",
        "4h": "FourHours", "1d": "OneDay", "1w": "OneWeek"
    }
    
    interval = timeframe_map.get(timeframe, "OneDay")
    candlesCount = min(limit, 1000)
    
    url = f"{BASE_URL}/market-data/instruments/{instrument_id}/history/candles/asc/{interval}/{candlesCount}"
    
    r = requests.get(url, headers=headers())
    r.raise_for_status()
    data = r.json()
    
    candles_data = []
    for instrument_candles in data.get("candles", []):
        for candle in instrument_candles.get("candles", []):
            candles_data.append({
                "datetime": candle.get("fromDate"),
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
                "volume": candle.get("volume", 0)
            })
    
    if not candles_data:
        raise Exception("No candle data found")
    
    df = pd.DataFrame(candles_data)
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    print(f"✓ Fetched {len(df)} candles\n")
    
    return df

def get_candle_colors(df):
    return ["G" if df.iloc[i]["close"] >= df.iloc[i]["open"] else "R" for i in range(len(df))]

def get_volume_category(df):
    volumes = df["volume"].values
    categories = []
    for i in range(len(volumes)):
        avg_vol = np.mean(volumes[:i+1]) if i < 20 else np.mean(volumes[i-20:i])
        categories.append("H" if volumes[i] > avg_vol else "L")
    return categories

def build_markov_model(df, pattern_length=3):
    colors = get_candle_colors(df)
    volumes = get_volume_category(df)
    transitions = defaultdict(list)
    
    for i in range(pattern_length, len(colors)):
        pattern = "".join(colors[i-pattern_length:i])
        volume_cat = volumes[i-1]
        pattern_key = f"{pattern}_{volume_cat}"
        next_color = colors[i]
        transitions[pattern_key].append({
            "next": next_color,
            "index": i,
            "date_offset": len(colors) - i
        })
    
    pattern_stats = {}
    for pattern, occurrences in transitions.items():
        total = len(occurrences)
        if total == 0:
            continue
        
        green_count = sum(np.exp(-0.01 * occ["date_offset"]) for occ in occurrences if occ["next"] == "G")
        red_count = sum(np.exp(-0.01 * occ["date_offset"]) for occ in occurrences if occ["next"] == "R")
        total_weighted = green_count + red_count
        
        pattern_stats[pattern] = {
            "total_occurrences": total,
            "p_bullish": green_count / total_weighted if total_weighted > 0 else 0.5,
            "p_bearish": red_count / total_weighted if total_weighted > 0 else 0.5,
            "last_seen": min([occ["date_offset"] for occ in occurrences]),
            "occurrences": occurrences
        }
    
    return pattern_stats, colors, volumes

def build_full_transition_matrix(df, pattern_length=3):
    pattern_stats, colors, volumes = build_markov_model(df, pattern_length)
    
    all_patterns = []
    for c1 in ['G', 'R']:
        for c2 in ['G', 'R']:
            for c3 in ['G', 'R']:
                for vol in ['H', 'L']:
                    pattern = f"{c1}{c2}{c3}_{vol}"
                    all_patterns.append(pattern)
    
    matrix_data = []
    for pattern in sorted(all_patterns):
        if pattern in pattern_stats:
            stats = pattern_stats[pattern]
            matrix_data.append({
                "State": pattern,
                "Count": stats["total_occurrences"],
                "P(Green)": f"{stats['p_bullish']:.1%}",
                "P(Red)": f"{stats['p_bearish']:.1%}",
                "LastSeen": stats["last_seen"],
                "Bias": "🟢 BULL" if stats['p_bullish'] > stats['p_bearish'] else "🔴 BEAR"
            })
        else:
            matrix_data.append({
                "State": pattern,
                "Count": 0,
                "P(Green)": "N/A",
                "P(Red)": "N/A",
                "LastSeen": "N/A",
                "Bias": "⚪ NONE"
            })
    
    return pd.DataFrame(matrix_data)

def analyze(df, pattern_length=3):
    """
    Simple analysis based on US market hours.
    
    - Market OPEN → last candle is forming, use -4, -3, -2
    - Market CLOSED → last candle is complete, use -3, -2, -1
    """
    market_open = is_us_market_open()
    
    pattern_stats, colors, volumes = build_markov_model(df, pattern_length)
    
    # Determine indices based on market status
    if market_open:
        # Market is OPEN → last candle is forming
        idx1, idx2, idx3 = -4, -3, -2
        vol_idx = -2
        status = "🟢 MARKET OPEN - Last candle is forming"
    else:
        # Market is CLOSED → last candle is complete
        idx1, idx2, idx3 = -3, -2, -1
        vol_idx = -1
        status = "🔴 MARKET CLOSED - All candles complete"
    
    current_pattern = "".join([colors[idx1], colors[idx2], colors[idx3]])
    current_volume = volumes[vol_idx]
    current_state = f"{current_pattern}_{current_volume}"
    
    print(f"\n{'='*70}")
    print(f"MARKET STATUS")
    print(f"{'='*70}\n")
    print(f"  {status}\n")
    
    print(f"{'='*70}")
    print(f"CURRENT STATE (Last 3 COMPLETED Candles)")
    print(f"{'='*70}\n")
    
    print(f"  {df['datetime'].iloc[idx1].date()}: {colors[idx1]} ({'🟢 Green' if colors[idx1] == 'G' else '🔴 Red'})")
    print(f"  {df['datetime'].iloc[idx2].date()}: {colors[idx2]} ({'🟢 Green' if colors[idx2] == 'G' else '🔴 Red'})")
    print(f"  {df['datetime'].iloc[idx3].date()}: {colors[idx3]} ({'🟢 Green' if colors[idx3] == 'G' else '🔴 Red'})")
    print(f"\n  Volume ({df['datetime'].iloc[vol_idx].date()}): {current_volume} ({'High' if current_volume == 'H' else 'Low'})")
    print(f"  State: {current_state}\n")
    
    # PREDICTION
    if current_state in pattern_stats:
        stats = pattern_stats[current_state]
        
        print(f"{'='*70}")
        print(f"PREDICTION FROM STATE: {current_state}")
        print(f"{'='*70}\n")
        print(f"Historical occurrences: {stats['total_occurrences']}")
        print(f"Last seen: {stats['last_seen']} candles ago\n")
        print(f"P(Next = Green): {stats['p_bullish']:.2%}")
        print(f"P(Next = Red):   {stats['p_bearish']:.2%}\n")
        
        bias = "🟢 BULLISH" if stats['p_bullish'] > stats['p_bearish'] else "🔴 BEARISH"
        confidence = max(stats['p_bullish'], stats['p_bearish'])
        
        print(f"Prediction: {bias}")
        print(f"Confidence: {confidence:.2%}\n")
    else:
        print(f"⚠️  State {current_state} has NEVER occurred!\n")
    
    # FULL TRANSITION MATRIX
    print(f"{'='*70}")
    print(f"FULL TRANSITION MATRIX (ALL 16 STATES)")
    print(f"{'='*70}\n")
    
    matrix = build_full_transition_matrix(df, pattern_length)
    print(matrix.to_string(index=False))
    print(f"\n👉 Current state: {current_state}")
    print()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("ETORO MARKOV MODEL - SIMPLE VERSION")
    print("Checks US market hours to determine complete candles")
    print("="*70 + "\n")
    
    ticker = input("Ticker (NVDA): ").strip().upper() or "NVDA"
    timeframe = input("Timeframe (1d): ").strip().lower() or "1d"
    
    try:
        df = get_ohlc_data(ticker, timeframe, 1000)
        analyze(df)
        
        print(f"{'='*70}")
        print("✓ Analysis Complete!")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
