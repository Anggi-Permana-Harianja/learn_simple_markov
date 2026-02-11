import numpy as np
import pandas as pd
import requests
import uuid
from collections import defaultdict

API_KEY = API_KEY_
USER_KEY = USER_KEY_
BASE_URL = "https://public-api.etoro.com/api/v1"

def headers():
    return {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": API_KEY,
        "x-user-key": USER_KEY,
    }

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
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
                "volume": candle.get("volume", 0)
            })
    
    if not candles_data:
        raise Exception("No candle data found")
    
    df = pd.DataFrame(candles_data)
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
    """Build FULL transition matrix - ALL 16 patterns"""
    pattern_stats, colors, volumes = build_markov_model(df, pattern_length)
    
    # Generate ALL possible patterns
    all_patterns = []
    for c1 in ['G', 'R']:
        for c2 in ['G', 'R']:
            for c3 in ['G', 'R']:
                for vol in ['H', 'L']:
                    pattern = f"{c1}{c2}{c3}_{vol}"
                    all_patterns.append(pattern)
    
    # Build matrix data
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
    pattern_stats, colors, volumes = build_markov_model(df, pattern_length)
    
    # CURRENT STATE (pattern)
    current_pattern = "".join(colors[-pattern_length:])
    current_volume = volumes[-1]
    current_state = f"{current_pattern}_{current_volume}"
    
    print(f"\n{'='*70}")
    print(f"CURRENT STATE")
    print(f"{'='*70}\n")
    print(f"State: {current_state}")
    print(f"  └─ Last 3 candles: {' '.join(colors[-pattern_length:])}")
    print(f"  └─ Current volume: {current_volume} ({'High' if current_volume == 'H' else 'Low'})\n")
    
    # PREDICTION
    if current_state in pattern_stats:
        stats = pattern_stats[current_state]
        
        print(f"{'='*70}")
        print(f"PREDICTION FROM CURRENT STATE")
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
    
    # Highlight current state
    print(matrix.to_string(index=False))
    print(f"\n👉 Current state: {current_state}")
    print()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("ETORO MARKOV MODEL - TRANSITION MATRIX ANALYSIS")
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
