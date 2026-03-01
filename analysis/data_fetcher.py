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


def fetch_stock_data(ticker, period=None):
    """
    Belirli bir hissenin geçmiş fiyat verilerini çeker.
    
    Args:
        ticker: yfinance ticker sembolü (ör: "THYAO.IS")
        period: Veri periyodu (1mo, 3mo, 6mo, 1y, 2y)
    
    Returns:
        pandas DataFrame (OHLCV verileri) veya hata durumunda None
    """
    if period is None:
        period = config.DEFAULT_PERIOD
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=config.DATA_INTERVAL)
        
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


def fetch_multiple_stocks(tickers, period=None):
    """
    Birden fazla hissenin verilerini çeker.
    
    Args:
        tickers: Ticker listesi
        period: Veri periyodu
    
    Returns:
        dict: {ticker: DataFrame} formatında
    """
    results = {}
    total = len(tickers)
    
    for i, ticker in enumerate(tickers, 1):
        print(f"  [{i}/{total}] {ticker} verisi çekiliyor...")
        data = fetch_stock_data(ticker, period)
        if data is not None:
            results[ticker] = data
    
    print(f"\n✓ {len(results)}/{total} hisse verisi başarıyla çekildi.")
    return results
