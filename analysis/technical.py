"""
Teknik Analiz Modülü
RSI, MACD, Bollinger Bantları, SMA, EMA, Stokastik, ADX, CCI, Williams %R
göstergelerini hesaplar ve teknik skor üretir.
"""

import pandas as pd
import pandas_ta as ta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def calculate_indicators(df):
    """
    Verilen OHLCV DataFrame'i üzerinde tüm teknik göstergeleri hesaplar.
    
    Args:
        df: OHLCV verileri içeren DataFrame (Açılış, Yüksek, Düşük, Kapanış, Hacim)
    
    Returns:
        dict: Tüm teknik gösterge değerleri ve sinyalleri
    """
    if df is None or len(df) < config.SMA_LONG:
        return None
    
    close = df["Kapanış"]
    high = df["Yüksek"]
    low = df["Düşük"]
    
    results = {}
    
    # --- RSI ---
    rsi = ta.rsi(close, length=config.RSI_PERIOD)
    if rsi is not None and len(rsi.dropna()) > 0:
        rsi_value = round(rsi.iloc[-1], 2)
        results["rsi"] = {
            "value": rsi_value,
            "signal": _rsi_signal(rsi_value),
            "description": _rsi_description(rsi_value)
        }
    
    # --- MACD ---
    macd = ta.macd(close, fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
    if macd is not None and len(macd.dropna()) > 0:
        macd_line = round(macd.iloc[-1, 0], 4)
        macd_signal = round(macd.iloc[-1, 2], 4)
        macd_hist = round(macd.iloc[-1, 1], 4)
        results["macd"] = {
            "macd_line": macd_line,
            "signal_line": macd_signal,
            "histogram": macd_hist,
            "signal": _macd_signal(macd_line, macd_signal, macd_hist),
            "description": _macd_description(macd_line, macd_signal, macd_hist)
        }
    
    # --- SMA ---
    sma_short = ta.sma(close, length=config.SMA_SHORT)
    sma_long = ta.sma(close, length=config.SMA_LONG)
    if sma_short is not None and sma_long is not None:
        sma_s = round(sma_short.iloc[-1], 2)
        sma_l = round(sma_long.iloc[-1], 2)
        current_price = round(close.iloc[-1], 2)
        results["sma"] = {
            "sma_short": sma_s,
            "sma_long": sma_l,
            "current_price": current_price,
            "signal": _sma_signal(current_price, sma_s, sma_l),
            "description": _sma_description(current_price, sma_s, sma_l)
        }
    
    # --- EMA ---
    ema_short = ta.ema(close, length=config.EMA_SHORT)
    ema_long = ta.ema(close, length=config.EMA_LONG)
    if ema_short is not None and ema_long is not None:
        ema_s = round(ema_short.iloc[-1], 2)
        ema_l = round(ema_long.iloc[-1], 2)
        current_price = round(close.iloc[-1], 2)
        results["ema"] = {
            "ema_short": ema_s,
            "ema_long": ema_l,
            "signal": _ema_signal(current_price, ema_s, ema_l),
            "description": _ema_description(current_price, ema_s, ema_l)
        }
    
    # --- Bollinger Bantları ---
    bbands = ta.bbands(close, length=config.BOLLINGER_PERIOD, std=config.BOLLINGER_STD)
    if bbands is not None and len(bbands.dropna()) > 0:
        bb_lower = round(bbands.iloc[-1, 0], 2)
        bb_mid = round(bbands.iloc[-1, 1], 2)
        bb_upper = round(bbands.iloc[-1, 2], 2)
        current_price = round(close.iloc[-1], 2)
        results["bollinger"] = {
            "upper": bb_upper,
            "middle": bb_mid,
            "lower": bb_lower,
            "current_price": current_price,
            "signal": _bollinger_signal(current_price, bb_upper, bb_lower, bb_mid),
            "description": _bollinger_description(current_price, bb_upper, bb_lower)
        }
    
    # --- Stokastik ---
    stoch = ta.stoch(high, low, close, k=config.STOCH_K, d=config.STOCH_D, smooth_k=config.STOCH_SMOOTH)
    if stoch is not None and len(stoch.dropna()) > 0:
        stoch_k = round(stoch.iloc[-1, 0], 2)
        stoch_d = round(stoch.iloc[-1, 1], 2)
        results["stochastic"] = {
            "k": stoch_k,
            "d": stoch_d,
            "signal": _stoch_signal(stoch_k, stoch_d),
            "description": _stoch_description(stoch_k, stoch_d)
        }
    
    # --- ADX (Average Directional Index) ---
    try:
        adx_data = ta.adx(high, low, close, length=config.ADX_PERIOD)
        if adx_data is not None and len(adx_data.dropna()) > 0:
            adx_value = round(adx_data.iloc[-1, 0], 2)  # ADX
            plus_di = round(adx_data.iloc[-1, 1], 2)     # +DI
            minus_di = round(adx_data.iloc[-1, 2], 2)    # -DI
            results["adx"] = {
                "value": adx_value,
                "plus_di": plus_di,
                "minus_di": minus_di,
                "signal": _adx_signal(adx_value, plus_di, minus_di),
                "description": _adx_description(adx_value, plus_di, minus_di)
            }
    except Exception:
        pass
    
    # --- CCI (Commodity Channel Index) ---
    try:
        cci = ta.cci(high, low, close, length=config.CCI_PERIOD)
        if cci is not None and len(cci.dropna()) > 0:
            cci_value = round(cci.iloc[-1], 2)
            results["cci"] = {
                "value": cci_value,
                "signal": _cci_signal(cci_value),
                "description": _cci_description(cci_value)
            }
    except Exception:
        pass
    
    # --- Williams %R ---
    try:
        willr = ta.willr(high, low, close, length=config.WILLIAMS_PERIOD)
        if willr is not None and len(willr.dropna()) > 0:
            willr_value = round(willr.iloc[-1], 2)
            results["williams"] = {
                "value": willr_value,
                "signal": _williams_signal(willr_value),
                "description": _williams_description(willr_value)
            }
    except Exception:
        pass
    
    # --- Genel Fiyat Bilgisi ---
    results["price_info"] = {
        "current": round(close.iloc[-1], 2),
        "change_1d": round(((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) * 100, 2) if len(close) > 1 else 0,
        "change_1w": round(((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]) * 100, 2) if len(close) > 5 else 0,
        "change_1m": round(((close.iloc[-1] - close.iloc[-22]) / close.iloc[-22]) * 100, 2) if len(close) > 22 else 0,
        "high_period": round(high.max(), 2),
        "low_period": round(low.min(), 2),
    }
    
    return results


# ============================================================
# Sinyal Fonksiyonları — DÜZELTILMIŞ
# ============================================================

def _rsi_signal(rsi):
    """RSI sinyali: standart 30/70 eşikleri."""
    if rsi >= config.RSI_OVERBOUGHT:
        return "SAT"
    elif rsi <= config.RSI_OVERSOLD:
        return "AL"
    return "TUT"


def _rsi_description(rsi):
    if rsi >= config.RSI_OVERBOUGHT:
        return f"RSI {rsi} → Aşırı alım bölgesinde, satış baskısı gelebilir"
    elif rsi <= config.RSI_OVERSOLD:
        return f"RSI {rsi} → Aşırı satım bölgesinde, alım fırsatı olabilir"
    return f"RSI {rsi} → Nötr bölgede"


def _macd_signal(macd_line, signal_line, histogram):
    """MACD sinyali: çizgi kesişimi + histogram yönü."""
    if macd_line > signal_line and histogram > 0:
        return "AL"
    elif macd_line < signal_line and histogram < 0:
        return "SAT"
    return "TUT"


def _macd_description(macd_line, signal_line, histogram):
    if macd_line > signal_line:
        return f"MACD sinyal çizgisinin üzerinde → Yükseliş trendi"
    return f"MACD sinyal çizgisinin altında → Düşüş trendi"


def _sma_signal(price, sma_short, sma_long):
    """SMA sinyali: fiyat ve ortalama pozisyonları."""
    if price > sma_short > sma_long:
        return "AL"
    elif price < sma_short < sma_long:
        return "SAT"
    return "TUT"


def _sma_description(price, sma_short, sma_long):
    if price > sma_short > sma_long:
        return f"Fiyat ({price}) her iki ortalamanın üzerinde → Güçlü yükseliş"
    elif price < sma_short < sma_long:
        return f"Fiyat ({price}) her iki ortalamanın altında → Güçlü düşüş"
    return f"Fiyat ({price}) ortalamalar arasında → Kararsız"


def _ema_signal(price, ema_short, ema_long):
    """EMA sinyali: fiyat ve EMA konumları."""
    if price > ema_short > ema_long:
        return "AL"
    elif price < ema_short < ema_long:
        return "SAT"
    return "TUT"


def _ema_description(price, ema_short, ema_long):
    if price > ema_short > ema_long:
        return f"EMA{config.EMA_SHORT}({ema_short}) > EMA{config.EMA_LONG}({ema_long}) → Yükseliş trendi"
    elif price < ema_short < ema_long:
        return f"EMA{config.EMA_SHORT}({ema_short}) < EMA{config.EMA_LONG}({ema_long}) → Düşüş trendi"
    return f"EMA{config.EMA_SHORT}: {ema_short} | EMA{config.EMA_LONG}: {ema_long} → Kararsız"


def _bollinger_signal(price, upper, lower, mid):
    """
    Bollinger sinyali — DÜZELTILDI.
    Sadece bantlara %5 yakınlıkta sinyal üretir.
    """
    band_width = upper - lower
    if band_width == 0:
        return "TUT"
    
    # Fiyatın bantlara olan yakınlığını hesapla
    pct_position = (price - lower) / band_width  # 0=alt bant, 1=üst bant
    
    if pct_position <= 0.05:     # Alt banda çok yakın (%5 içinde)
        return "AL"
    elif pct_position >= 0.95:   # Üst banda çok yakın (%5 içinde)
        return "SAT"
    elif pct_position <= 0.20:   # Alt banda yakın
        return "AL"
    elif pct_position >= 0.80:   # Üst banda yakın
        return "SAT"
    return "TUT"


def _bollinger_description(price, upper, lower):
    if price <= lower * 1.02:
        return f"Fiyat alt banda yakın → Potansiyel alım fırsatı"
    elif price >= upper * 0.98:
        return f"Fiyat üst banda yakın → Aşırı alım, dikkatli ol"
    return f"Fiyat bantlar arasında → Normal dalgalanma"


def _stoch_signal(k, d):
    """Stokastik sinyali: standart 20/80 eşikleri."""
    if k <= config.STOCH_OVERSOLD and d <= config.STOCH_OVERSOLD:
        return "AL"
    elif k >= config.STOCH_OVERBOUGHT and d >= config.STOCH_OVERBOUGHT:
        return "SAT"
    return "TUT"


def _stoch_description(k, d):
    if k <= config.STOCH_OVERSOLD:
        return f"Stokastik %K:{k} %D:{d} → Aşırı satım bölgesi"
    elif k >= config.STOCH_OVERBOUGHT:
        return f"Stokastik %K:{k} %D:{d} → Aşırı alım bölgesi"
    return f"Stokastik %K:{k} %D:{d} → Nötr"


def _adx_signal(adx, plus_di, minus_di):
    """
    ADX sinyali:
    - ADX > 25 = güçlü trend
    - +DI > -DI = yükseliş trendi → AL
    - -DI > +DI = düşüş trendi → SAT
    - ADX < 25 = zayıf trend → TUT
    """
    if adx >= config.ADX_STRONG_TREND:
        if plus_di > minus_di:
            return "AL"
        elif minus_di > plus_di:
            return "SAT"
    return "TUT"


def _adx_description(adx, plus_di, minus_di):
    trend = "Güçlü" if adx >= config.ADX_STRONG_TREND else "Zayıf"
    direction = "Yükseliş" if plus_di > minus_di else "Düşüş"
    return f"ADX: {adx} ({trend} trend) | +DI: {plus_di} -DI: {minus_di} → {direction}"


def _cci_signal(cci):
    """
    CCI sinyali:
    - CCI > 100 = aşırı alım → SAT
    - CCI < -100 = aşırı satım → AL
    """
    if cci >= config.CCI_OVERBOUGHT:
        return "SAT"
    elif cci <= config.CCI_OVERSOLD:
        return "AL"
    return "TUT"


def _cci_description(cci):
    if cci >= config.CCI_OVERBOUGHT:
        return f"CCI {cci} → Aşırı alım bölgesinde"
    elif cci <= config.CCI_OVERSOLD:
        return f"CCI {cci} → Aşırı satım bölgesinde"
    return f"CCI {cci} → Nötr bölgede"


def _williams_signal(willr):
    """
    Williams %R sinyali:
    - %R > -20 = aşırı alım → SAT
    - %R < -80 = aşırı satım → AL
    """
    if willr >= config.WILLIAMS_OVERBOUGHT:
        return "SAT"
    elif willr <= config.WILLIAMS_OVERSOLD:
        return "AL"
    return "TUT"


def _williams_description(willr):
    if willr >= config.WILLIAMS_OVERBOUGHT:
        return f"Williams %R: {willr} → Aşırı alım bölgesinde"
    elif willr <= config.WILLIAMS_OVERSOLD:
        return f"Williams %R: {willr} → Aşırı satım bölgesinde"
    return f"Williams %R: {willr} → Nötr bölgede"


# ============================================================
# Teknik Skor Hesaplama — 9 İndikatör
# ============================================================

def get_technical_score(indicators):
    """
    Teknik göstergelerden 0-100 arası bir skor hesaplar.
    Yüksek skor = AL sinyali, Düşük skor = SAT sinyali
    
    9 gösterge: RSI, MACD, SMA, EMA, Bollinger, Stochastic, ADX, CCI, Williams %R
    
    Returns:
        int: 0-100 arası teknik skor
    """
    if not indicators:
        return 50
    
    scores = []
    
    # RSI skoru — düzeltildi
    if "rsi" in indicators:
        rsi = indicators["rsi"]["value"]
        if rsi <= config.RSI_OVERSOLD:
            # Aşırı satım = güçlü AL sinyali
            scores.append(("rsi", 80))
        elif rsi >= config.RSI_OVERBOUGHT:
            # Aşırı alım = güçlü SAT sinyali
            scores.append(("rsi", 20))
        else:
            # Nötr bölge: 30-70 arası → 50 skor (tam nötr)
            # RSI 50 = skor 50, RSI 30 = skor 65, RSI 70 = skor 35
            score = 50 + (50 - rsi) * 0.375
            scores.append(("rsi", max(25, min(75, score))))
    
    # MACD skoru
    if "macd" in indicators:
        sig = indicators["macd"]["signal"]
        if sig == "AL":
            scores.append(("macd", 75))
        elif sig == "SAT":
            scores.append(("macd", 25))
        else:
            scores.append(("macd", 50))
    
    # SMA skoru
    if "sma" in indicators:
        sig = indicators["sma"]["signal"]
        if sig == "AL":
            scores.append(("sma", 75))
        elif sig == "SAT":
            scores.append(("sma", 25))
        else:
            scores.append(("sma", 50))
    
    # EMA skoru — NEW: artık skora dahil
    if "ema" in indicators:
        sig = indicators["ema"]["signal"]
        if sig == "AL":
            scores.append(("ema", 75))
        elif sig == "SAT":
            scores.append(("ema", 25))
        else:
            scores.append(("ema", 50))
    
    # Bollinger skoru — düzeltildi
    if "bollinger" in indicators:
        sig = indicators["bollinger"]["signal"]
        if sig == "AL":
            scores.append(("bollinger", 75))
        elif sig == "SAT":
            scores.append(("bollinger", 25))
        else:
            scores.append(("bollinger", 50))
    
    # Stokastik skoru
    if "stochastic" in indicators:
        sig = indicators["stochastic"]["signal"]
        if sig == "AL":
            scores.append(("stochastic", 75))
        elif sig == "SAT":
            scores.append(("stochastic", 25))
        else:
            scores.append(("stochastic", 50))
    
    # ADX skoru — NEW
    if "adx" in indicators:
        sig = indicators["adx"]["signal"]
        if sig == "AL":
            scores.append(("adx", 75))
        elif sig == "SAT":
            scores.append(("adx", 25))
        else:
            scores.append(("adx", 50))
    
    # CCI skoru — NEW
    if "cci" in indicators:
        sig = indicators["cci"]["signal"]
        if sig == "AL":
            scores.append(("cci", 80))
        elif sig == "SAT":
            scores.append(("cci", 20))
        else:
            scores.append(("cci", 50))
    
    # Williams %R skoru — NEW
    if "williams" in indicators:
        sig = indicators["williams"]["signal"]
        if sig == "AL":
            scores.append(("williams", 80))
        elif sig == "SAT":
            scores.append(("williams", 20))
        else:
            scores.append(("williams", 50))
    
    if not scores:
        return 50
    
    # Ağırlıklı ortalama
    weights = {
        "rsi": config.WEIGHT_RSI,
        "macd": config.WEIGHT_MACD,
        "sma": config.WEIGHT_SMA,
        "ema": config.WEIGHT_EMA,
        "bollinger": config.WEIGHT_BOLLINGER,
        "stochastic": config.WEIGHT_STOCHASTIC,
        "adx": config.WEIGHT_ADX,
        "cci": config.WEIGHT_CCI,
        "williams": config.WEIGHT_WILLIAMS,
    }
    
    total_weight = sum(weights.get(name, 0.1) for name, _ in scores)
    weighted_score = sum(weights.get(name, 0.1) * score for name, score in scores)
    
    return round(weighted_score / total_weight)
