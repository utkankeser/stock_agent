"""
Veri Çekme Modülü
yfinance kullanarak BIST hisse/fon verilerini çeker.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def fetch_stock_data(ticker, period=None, interval=None):
    """
    Belirli bir hissenin geçmiş fiyat verilerini çeker.
    
    Args:
        ticker: yfinance ticker sembolü (ör: "THYAO.IS")
        period: Veri periyodu (1mo, 3mo, 6mo, 1y, 2y)
        interval: Mum süresi (1h, 1d, 1wk vb.)
    
    Returns:
        pandas DataFrame (OHLCV verileri) veya hata durumunda None
    """
    if period is None:
        period = config.DEFAULT_PERIOD
    if interval is None:
        interval = config.DATA_INTERVAL
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            print(f"[UYARI] {ticker} için veri bulunamadı.")
            return None
        
        # Sütun isimlerini Türkçeleştir
        df = df.rename(columns={
            "Open": "Açılış",
            "High": "Yüksek",
            "Low": "Düşük",
            "Close": "Kapanış",
            "Volume": "Hacim"
        })
        
        # Gereksiz sütunları kaldır
        cols_to_drop = [col for col in ["Dividends", "Stock Splits", "Capital Gains"] if col in df.columns]
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
        
        # Sürüm/timezone uyumluluğu için index'i datetime yapalım
        df.index = pd.to_datetime(df.index)

        # Günlük veri için canlı yfinance fast_info yamasını uygula
        if interval == "1d":
            try:
                fast = stock.fast_info
                live_price = fast.get("lastPrice", None)
                if live_price is not None and live_price > 0:
                    live_open = fast.get("open", live_price)
                    live_high = fast.get("dayHigh", live_price)
                    live_low = fast.get("dayLow", live_price)
                    live_vol = fast.get("lastVolume", 0)
                    
                    if not df.empty:
                        last_idx = df.index[-1]
                        last_row = df.iloc[-1]
                        # 1. Son satırda NaN fiyatlar varsa bunları canlı verilerle güncelle
                        if pd.isna(last_row["Kapanış"]) or pd.isna(last_row["Açılış"]):
                            df.at[last_idx, "Açılış"] = live_open if not pd.isna(live_open) else live_price
                            df.at[last_idx, "Yüksek"] = live_high if not pd.isna(live_high) else live_price
                            df.at[last_idx, "Düşük"] = live_low if not pd.isna(live_low) else live_price
                            df.at[last_idx, "Kapanış"] = live_price
                            if live_vol > 0:
                                df.at[last_idx, "Hacim"] = live_vol
                        else:
                            # 2. Son satır doluysa ancak bugün için yeni bir işlem günü başlamışsa (saat 10:00 sonrası), yeni satır ekle
                            tz = df.index.tz if df.index.tz is not None else "Europe/Istanbul"
                            current_date = pd.Timestamp.now(tz=tz).normalize()
                            last_date = df.index[-1].normalize()
                            
                            if current_date > last_date and current_date.weekday() < 5:
                                now_istanbul = pd.Timestamp.now(tz="Europe/Istanbul")
                                if now_istanbul.hour >= 10:
                                    new_row = pd.DataFrame({
                                        "Açılış": [live_open],
                                        "Yüksek": [live_high],
                                        "Düşük": [live_low],
                                        "Kapanış": [live_price],
                                        "Hacim": [live_vol]
                                    }, index=[current_date])
                                    df = pd.concat([df, new_row])
            except Exception as e:
                print(f"[UYARI] Canlı fiyat yaması uygulanamadı: {e}")
        
        return df
        
    except Exception as e:
        print(f"[HATA] {ticker} verisi çekilirken hata: {e}")
        return None


def fetch_stock_info(ticker):
    """
    Hissenin temel bilgilerini çeker.
    
    Returns:
        dict: Hisse bilgileri veya None
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "ticker": ticker,
            "name": info.get("longName", info.get("shortName", ticker)),
            "currency": info.get("currency", "TRY"),
            "market_cap": info.get("marketCap", None),
            "pe_ratio": info.get("trailingPE", None),
            "sector": info.get("sector", "Bilinmiyor"),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", None)),
            "previous_close": info.get("previousClose", None),
            "day_high": info.get("dayHigh", None),
            "day_low": info.get("dayLow", None),
            "volume": info.get("volume", None),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh", None),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow", None),
        }
    except Exception as e:
        print(f"[HATA] {ticker} bilgisi çekilirken hata: {e}")
        return None


def fetch_multiple_stocks(tickers, period=None, interval=None):
    """
    Birden fazla hissenin verilerini çeker.
    
    Args:
        tickers: Ticker listesi
        period: Veri periyodu
        interval: Mum süresi
    
    Returns:
        dict: {ticker: DataFrame} formatında
    """
    results = {}
    total = len(tickers)
    
    for i, ticker in enumerate(tickers, 1):
        print(f"  [{i}/{total}] {ticker} verisi çekiliyor...")
        data = fetch_stock_data(ticker, period, interval)
        if data is not None:
            results[ticker] = data
    
    print(f"\n[OK] {len(results)}/{total} hisse verisi basariyla cekildi.")
    return results
