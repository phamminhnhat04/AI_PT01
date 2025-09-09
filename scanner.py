# Cấu hình Telegram
TELEGRAM_TOKEN = "8259612868:AAG6NyXf79hW4JB1ZkQNIViMTDBFd6hE0WE"   # dán token bạn lấy từ BotFather vào đây
TELEGRAM_CHAT_ID = "6952647629"# dán chat_id bạn lấy từ @userinfobot

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Lỗi gửi Telegram:", e)
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

BASE_URL = "https://api.binance.com"

# Lấy danh sách cặp USDT
def get_symbols():
    url = BASE_URL + "/api/v3/exchangeInfo"
    data = requests.get(url).json()
    symbols = [s["symbol"] for s in data["symbols"] if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING"]
    return symbols

# Lấy dữ liệu nến
def get_klines(symbol, interval="1h", limit=500):
    url = BASE_URL + "/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()
    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

# EMA
def ema(series, period=200):
    return series.ewm(span=period, adjust=False).mean()

# Xác định swing high/low
def get_swings(df, swing_window=9):
    swing_high = df['high'].rolling(swing_window, center=True).max()
    swing_low = df['low'].rolling(swing_window, center=True).min()
    return swing_high.dropna(), swing_low.dropna()

# Trendline đơn giản trên khung 15m
def check_trendline_15m(df_15m, direction):
    if df_15m.empty or len(df_15m) < 3:
        return None
    if direction == "LONG":
        lows = df_15m['low'].tail(2)
        if len(lows) < 2:
            return None
        trendline = lows.iloc[0] + (lows.iloc[1] - lows.iloc[0])  # đơn giản
        return df_15m['close'].iloc[-1] > trendline
    elif direction == "SHORT":
        highs = df_15m['high'].tail(2)
        if len(highs) < 2:
            return None
        trendline = highs.iloc[0] + (highs.iloc[1] - highs.iloc[0])
        return df_15m['close'].iloc[-1] < trendline
    return None

# Kiểm tra hợp lưu tín hiệu
def check_confluence(df, df_15m):
    # cần đủ dữ liệu
    if df.shape[0] < 210:
        return None

    df = df.copy()
    df["EMA200"] = ema(df["close"], 200)
    last_close = df["close"].iloc[-1]
    ema200 = df["EMA200"].iloc[-1]

    swing_high, swing_low = get_swings(df, 9)

    # Swing gần EMA200 ±1.5%
    if ema200 == 0 or pd.isna(ema200):
        return None

    swing_high_near = swing_high[(abs(swing_high - ema200) / ema200) <= 0.015]
    swing_low_near = swing_low[(abs(swing_low - ema200) / ema200) <= 0.015]

    # Giá gần EMA200 ±2%
    if abs(last_close - ema200) / ema200 > 0.02:
        return None

    # LONG setup
    if not swing_low_near.empty:
        trend = check_trendline_15m(df_15m, "LONG")
        if trend is False:
            return None
        return "LONG setup"

    # SHORT setup
    if not swing_high_near.empty:
        trend = check_trendline_15m(df_15m, "SHORT")
        if trend is False:
            return None
        return "SHORT setup"

    return None

# Quét 1 cặp
def scan_symbol(symbol, intervals={"1h": 9, "4h": 7}):
    results = []
    for interval, swing_window in intervals.items():
        try:
            df = get_klines(symbol, interval, 500)
            df_15m = get_klines(symbol, "15m", 100)
            signal = check_confluence(df, df_15m)
            if signal:
                results.append((interval, signal))
        except Exception as e:
            # in lỗi và tiếp tục cặp tiếp theo
            print(f"Lỗi khi quét {symbol} | {interval}: {e}")
            continue
    return results

# Main
if __name__ == "__main__":
    symbols = get_symbols()
    start_msg = f"🤖 Bot đã khởi động, đang theo dõi {len(symbols)} cặp USDT..."
    print(start_msg)
    send_telegram(start_msg)

    while True:
        now = datetime.utcnow()
        header = f"\n===== 🔔 QUÉT LÚC {now} ====="
        print(header)
        send_telegram(f"🔔 Bắt đầu lượt quét lúc {now.strftime('%Y-%m-%d %H:%M:%S')}")

        for sym in symbols:
            results = scan_symbol(sym)
            if results:
                for interval, signal in results:
                    msg = f"{sym} | {interval} | {signal}"
                    print(msg)          # In ra màn hình
                    send_telegram(msg)  # Gửi về Telegram

        # Nghỉ theo khung lớn nhất (1h)
        next_run = (now + timedelta(hours=1)).replace(minute=0, second=5)
        sleep_seconds = (next_run - datetime.utcnow()).total_seconds()
        footer = f"===== HẾT MỘT LƯỢT, NGHỈ {int(sleep_seconds)} giây =====\n"
        print(footer)
        send_telegram(f"✅ Hoàn thành lượt quét. Nghỉ {int(sleep_seconds)} giây.")
        time.sleep(max(sleep_seconds, 5))
