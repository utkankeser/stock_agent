"""
Teknik Analiz Modülü — 19 İndikatör
RSI, MACD, SMA, EMA, Bollinger, Stokastik, ADX, CCI, Williams %R,
OBV, MFI, Parabolic SAR, Ichimoku, ROC, CMF, ATR, McGinley, SMI, Zigzag
Sinyal etiketleri: AL / SAT / NÖTR
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def calculate_indicators(df):
    """
    Verilen OHLCV DataFrame'i üzerinde 15 teknik göstergeyi hesaplar.

    Returns:
        dict: Tüm teknik gösterge değerleri ve sinyalleri
    """
    if df is None:
        return None
        
    # yfinance kaynaklı eksik/boş satırları temizle
    df = df.dropna(subset=["Kapanış"])
    
    if len(df) < config.SMA_LONG:
        return None

    close = df["Kapanış"]
    high = df["Yüksek"]
    low = df["Düşük"]
    volume = df["Hacim"] if "Hacim" in df.columns else None

    results = {}

    # --- 1. RSI ---
    try:
        rsi = ta.rsi(close, length=config.RSI_PERIOD)
        if rsi is not None and len(rsi.dropna()) > 0:
            rsi_value = round(rsi.iloc[-1], 2)
            results["rsi"] = {
                "value": rsi_value,
                "signal": _rsi_signal(rsi_value),
                "description": _rsi_description(rsi_value),
            }
    except Exception:
        pass

    # --- 2. MACD ---
    try:
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
                "description": _macd_description(macd_line, macd_signal),
            }
    except Exception:
        pass

    # --- 3. SMA ---
    try:
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
                "signal": _ma_signal(current_price, sma_s, sma_l),
                "description": _ma_description("SMA", current_price, sma_s, sma_l,
                                                config.SMA_SHORT, config.SMA_LONG),
            }
    except Exception:
        pass

    # --- 4. EMA ---
    try:
        ema_short = ta.ema(close, length=config.EMA_SHORT)
        ema_long = ta.ema(close, length=config.EMA_LONG)
        if ema_short is not None and ema_long is not None:
            ema_s = round(ema_short.iloc[-1], 2)
            ema_l = round(ema_long.iloc[-1], 2)
            current_price = round(close.iloc[-1], 2)
            results["ema"] = {
                "ema_short": ema_s,
                "ema_long": ema_l,
                "signal": _ma_signal(current_price, ema_s, ema_l),
                "description": _ma_description("EMA", current_price, ema_s, ema_l,
                                                config.EMA_SHORT, config.EMA_LONG),
            }
    except Exception:
        pass

    # --- 5. Bollinger Bantları ---
    try:
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
                "signal": _bollinger_signal(current_price, bb_upper, bb_lower),
                "description": _bollinger_description(current_price, bb_upper, bb_lower),
            }
    except Exception:
        pass

    # --- 6. Stokastik ---
    try:
        stoch = ta.stoch(high, low, close, k=config.STOCH_K, d=config.STOCH_D, smooth_k=config.STOCH_SMOOTH)
        if stoch is not None and len(stoch.dropna()) > 0:
            stoch_k = round(stoch.iloc[-1, 0], 2)
            stoch_d = round(stoch.iloc[-1, 1], 2)
            results["stochastic"] = {
                "k": stoch_k,
                "d": stoch_d,
                "signal": _stoch_signal(stoch_k, stoch_d),
                "description": _stoch_description(stoch_k, stoch_d),
            }
    except Exception:
        pass

    # --- 7. ADX ---
    try:
        adx_data = ta.adx(high, low, close, length=config.ADX_PERIOD)
        if adx_data is not None and len(adx_data.dropna()) > 0:
            adx_value = round(adx_data.iloc[-1, 0], 2)
            plus_di = round(adx_data.iloc[-1, 1], 2)
            minus_di = round(adx_data.iloc[-1, 2], 2)
            results["adx"] = {
                "value": adx_value,
                "plus_di": plus_di,
                "minus_di": minus_di,
                "signal": _adx_signal(adx_value, plus_di, minus_di),
                "description": _adx_description(adx_value, plus_di, minus_di),
            }
    except Exception:
        pass

    # --- 8. CCI ---
    try:
        # pandas_ta'in pure-python CCI formülünde işlem önceliği hatası (parantez eksikliği) olduğu için elle hesaplıyoruz
        tp = (high + low + close) / 3
        tp_sma = tp.rolling(window=config.CCI_PERIOD).mean()
        tp_mad = tp.rolling(window=config.CCI_PERIOD).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        
        mad_val = tp_mad.iloc[-1]
        if mad_val > 0:
            cci_value = round((tp.iloc[-1] - tp_sma.iloc[-1]) / (0.015 * mad_val), 2)
        else:
            cci_value = 0.0
            
        results["cci"] = {
            "value": cci_value,
            "signal": _cci_signal(cci_value),
            "description": _cci_description(cci_value),
        }
    except Exception:
        pass

    # --- 9. Williams %R ---
    try:
        willr = ta.willr(high, low, close, length=config.WILLIAMS_PERIOD)
        if willr is not None and len(willr.dropna()) > 0:
            willr_value = round(willr.iloc[-1], 2)
            results["williams"] = {
                "value": willr_value,
                "signal": _williams_signal(willr_value),
                "description": _williams_description(willr_value),
            }
    except Exception:
        pass

    # --- 10. OBV (On Balance Volume) ---
    if volume is not None:
        try:
            obv = ta.obv(close, volume)
            if obv is not None and len(obv.dropna()) >= config.OBV_SMA_PERIOD:
                obv_current = round(obv.iloc[-1], 0)
                obv_sma = round(obv.rolling(window=config.OBV_SMA_PERIOD).mean().iloc[-1], 0)
                results["obv"] = {
                    "value": int(obv_current),
                    "sma": int(obv_sma),
                    "signal": _obv_signal(obv_current, obv_sma),
                    "description": _obv_description(obv_current, obv_sma),
                }
        except Exception:
            pass

    # --- 11. MFI (Money Flow Index) ---
    if volume is not None:
        try:
            mfi = ta.mfi(high, low, close, volume, length=config.MFI_PERIOD)
            if mfi is not None and len(mfi.dropna()) > 0:
                mfi_value = round(mfi.iloc[-1], 2)
                results["mfi"] = {
                    "value": mfi_value,
                    "signal": _mfi_signal(mfi_value),
                    "description": _mfi_description(mfi_value),
                }
        except Exception:
            pass

    # --- 12. Parabolic SAR ---
    try:
        psar = ta.psar(high, low, close, af0=config.PSAR_AF, af=config.PSAR_AF, max_af=config.PSAR_MAX_AF)
        if psar is not None and len(psar.dropna(how="all")) > 0:
            current_price = round(close.iloc[-1], 2)
            # psar returns PSARl (long/bullish) and PSARs (short/bearish)
            psar_long = psar.iloc[-1, 0]  # PSARl_ — NaN when bearish
            psar_short = psar.iloc[-1, 1]  # PSARs_ — NaN when bullish
            if not pd.isna(psar_long):
                sar_value = round(psar_long, 2)
                sar_trend = "AL"
            elif not pd.isna(psar_short):
                sar_value = round(psar_short, 2)
                sar_trend = "SAT"
            else:
                sar_value = current_price
                sar_trend = "NÖTR"
            results["psar"] = {
                "value": sar_value,
                "price": current_price,
                "signal": sar_trend,
                "description": _psar_description(current_price, sar_value, sar_trend),
            }
    except Exception:
        pass

    # --- 13. Ichimoku Cloud ---
    try:
        ichimoku_data, _ = ta.ichimoku(high, low, close,
                                        tenkan=config.ICHIMOKU_TENKAN,
                                        kijun=config.ICHIMOKU_KIJUN,
                                        senkou=config.ICHIMOKU_SENKOU)
        if ichimoku_data is not None and len(ichimoku_data.dropna()) > 0:
            current_price = round(close.iloc[-1], 2)
            
            # Dinamik sütun eşleme (pandas_ta sütun sırası işletim sistemine/sürüme göre değişebilir)
            tenkan_col = [c for c in ichimoku_data.columns if "ITS" in c][0]
            kijun_col = [c for c in ichimoku_data.columns if "IKS" in c][0]
            senkou_a_col = [c for c in ichimoku_data.columns if "ISA" in c][0]
            senkou_b_col = [c for c in ichimoku_data.columns if "ISB" in c][0]
            
            tenkan = round(float(ichimoku_data[tenkan_col].iloc[-1]), 2)
            kijun = round(float(ichimoku_data[kijun_col].iloc[-1]), 2)
            senkou_a = round(float(ichimoku_data[senkou_a_col].iloc[-1]), 2)
            senkou_b = round(float(ichimoku_data[senkou_b_col].iloc[-1]), 2)
            
            cloud_top = max(senkou_a, senkou_b)
            cloud_bottom = min(senkou_a, senkou_b)
            results["ichimoku"] = {
                "tenkan": tenkan,
                "kijun": kijun,
                "senkou_a": senkou_a,
                "senkou_b": senkou_b,
                "signal": _ichimoku_signal(current_price, cloud_top, cloud_bottom, tenkan, kijun),
                "description": _ichimoku_description(current_price, cloud_top, cloud_bottom),
            }
    except Exception:
        pass

    # --- 14. ROC (Rate of Change) ---
    try:
        roc = ta.roc(close, length=config.ROC_PERIOD)
        if roc is not None and len(roc.dropna()) > 0:
            roc_value = round(roc.iloc[-1], 2)
            results["roc"] = {
                "value": roc_value,
                "signal": _roc_signal(roc_value),
                "description": _roc_description(roc_value),
            }
    except Exception:
        pass

    # --- 15. CMF (Chaikin Money Flow) ---
    if volume is not None:
        try:
            cmf = ta.cmf(high, low, close, volume, length=config.CMF_PERIOD)
            if cmf is not None and len(cmf.dropna()) > 0:
                cmf_value = round(cmf.iloc[-1], 4)
                results["cmf"] = {
                    "value": cmf_value,
                    "signal": _cmf_signal(cmf_value),
                    "description": _cmf_description(cmf_value),
                }
        except Exception:
            pass

    # --- 16. ATR (Average True Range) ---
    try:
        atr = ta.atr(high, low, close, length=config.ATR_PERIOD)
        if atr is not None and len(atr.dropna()) > 0:
            atr_value = round(atr.iloc[-1], 2)
            current_price = round(close.iloc[-1], 2)
            results["atr"] = {
                "value": atr_value,
                "signal": _atr_signal(current_price, atr_value),
                "description": _atr_description(current_price, atr_value),
            }
    except Exception:
        pass

    # --- 17. McGinley Dynamic ---
    try:
        mcgd = ta.mcgd(close, length=config.MCGINLEY_PERIOD)
        if mcgd is not None and len(mcgd.dropna()) > 0:
            mcgd_value = round(mcgd.iloc[-1], 2)
            current_price = round(close.iloc[-1], 2)
            results["mcginley"] = {
                "value": mcgd_value,
                "signal": _mcginley_signal(current_price, mcgd_value),
                "description": _mcginley_description(current_price, mcgd_value),
            }
    except Exception:
        pass

    # --- 18. SMI (Stochastic Momentum Index) ---
    try:
        smi = ta.smi(close, fast=config.SMI_FAST, slow=config.SMI_SLOW, signal=config.SMI_SIGNAL)
        if smi is not None and len(smi.dropna()) > 0:
            smi_value = round(smi.iloc[-1, 0], 2)
            smi_signal_line = round(smi.iloc[-1, 1], 2)
            results["smi"] = {
                "value": smi_value,
                "signal_line": smi_signal_line,
                "signal": _smi_signal(smi_value, smi_signal_line),
                "description": _smi_description(smi_value, smi_signal_line),
            }
    except Exception:
        pass

    # --- 19. Zigzag ---
    try:
        zigzag = _calculate_zigzag(close, deviation=config.ZIGZAG_DEVIATION)
        if zigzag is not None:
            zz_non_null = zigzag["ZIGZAGv"].dropna()
            if len(zz_non_null) >= 2:
                last_pivot = zz_non_null.iloc[-1]
                prev_pivot = zz_non_null.iloc[-2]
                current_price = round(close.iloc[-1], 2)
                results["zigzag"] = {
                    "last_pivot": round(last_pivot, 2),
                    "signal": _zigzag_signal(current_price, last_pivot, prev_pivot),
                    "description": _zigzag_description(current_price, last_pivot, prev_pivot),
                }
    except Exception:
        pass

    # --- Genel Fiyat Bilgisi ---
    import math
    def _clean_val(v):
        try:
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                return 0.0
            return fv
        except Exception:
            return 0.0

    current_val = _clean_val(close.iloc[-1])
    
    # Takvim gününe göre en yakın geçmiş fiyatı bulma yardımcısı
    def _get_price_at_delta(df_in, delta_days):
        try:
            if df_in is None or len(df_in) < 2:
                return 0.0
            df_past = df_in.iloc[:-1].dropna(subset=["Kapanış"])
            timestamps = pd.to_datetime(df_past.index)
            last_time = pd.to_datetime(df_in.index[-1])
            target_time = last_time - pd.Timedelta(days=delta_days)
            idx = np.abs((timestamps - target_time).total_seconds()).argmin()
            return float(df_past["Kapanış"].iloc[idx])
        except Exception:
            return 0.0

    change_1d = 0.0
    price_1d = _get_price_at_delta(df, 1)
    if price_1d > 0:
        change_1d = round(((current_val - price_1d) / price_1d) * 100, 2)
    elif len(close) > 1:
        c2 = _clean_val(close.iloc[-2])
        if c2 > 0:
            change_1d = round(((current_val - c2) / c2) * 100, 2)
            
    change_1w = 0.0
    price_1w = _get_price_at_delta(df, 7)
    if price_1w > 0:
        change_1w = round(((current_val - price_1w) / price_1w) * 100, 2)
    elif len(close) > 5:
        c5 = _clean_val(close.iloc[-5])
        if c5 > 0:
            change_1w = round(((current_val - c5) / c5) * 100, 2)
            
    change_1m = 0.0
    price_1m = _get_price_at_delta(df, 30)
    if price_1m > 0:
        change_1m = round(((current_val - price_1m) / price_1m) * 100, 2)
    elif len(close) > 22:
        c22 = _clean_val(close.iloc[-22])
        if c22 > 0:
            change_1m = round(((current_val - c22) / c22) * 100, 2)

    results["price_info"] = {
        "current": round(current_val, 2),
        "change_1d": _clean_val(change_1d),
        "change_1w": _clean_val(change_1w),
        "change_1m": _clean_val(change_1m),
        "high_period": round(_clean_val(high.max()), 2),
        "low_period": round(_clean_val(low.min()), 2),
    }

    return results


# ============================================================
# SİNYAL FONKSİYONLARI — AL / SAT / NÖTR
# ============================================================

# --- 1. RSI ---
def _rsi_signal(rsi):
    """RSI ≤30 → AL (aşırı satım), RSI ≥70 → SAT (aşırı alım), arası → NÖTR"""
    if rsi <= config.RSI_OVERSOLD:
        return "AL"
    elif rsi >= config.RSI_OVERBOUGHT:
        return "SAT"
    return "NÖTR"

def _rsi_description(rsi):
    if rsi >= config.RSI_OVERBOUGHT:
        return f"RSI {rsi} → Aşırı alım bölgesi, satış baskısı gelebilir"
    elif rsi <= config.RSI_OVERSOLD:
        return f"RSI {rsi} → Aşırı satım bölgesi, alım fırsatı"
    return f"RSI {rsi} → Nötr bölge"


# --- 2. MACD ---
def _macd_signal(macd_line, signal_line, histogram):
    """MACD > Signal + Hist > 0 → AL, tersi → SAT"""
    if macd_line > signal_line and histogram > 0:
        return "AL"
    elif macd_line < signal_line and histogram < 0:
        return "SAT"
    return "NÖTR"

def _macd_description(macd_line, signal_line):
    if macd_line > signal_line:
        return f"MACD ({macd_line}) sinyal çizgisinin ({signal_line}) üzerinde → Yükseliş"
    return f"MACD ({macd_line}) sinyal çizgisinin ({signal_line}) altında → Düşüş"


# --- 3 & 4. SMA / EMA (ortak fonksiyon) ---
def _ma_signal(price, short_ma, long_ma):
    """Fiyat > Kısa MA > Uzun MA → AL, tersi → SAT"""
    if price > short_ma > long_ma:
        return "AL"
    elif price < short_ma < long_ma:
        return "SAT"
    return "NÖTR"

def _ma_description(ma_type, price, short_ma, long_ma, short_period, long_period):
    if price > short_ma > long_ma:
        return f"Fiyat ({price}) > {ma_type}{short_period} ({short_ma}) > {ma_type}{long_period} ({long_ma}) → Güçlü yükseliş"
    elif price < short_ma < long_ma:
        return f"Fiyat ({price}) < {ma_type}{short_period} ({short_ma}) < {ma_type}{long_period} ({long_ma}) → Güçlü düşüş"
    return f"Fiyat ({price}) | {ma_type}{short_period}: {short_ma} | {ma_type}{long_period}: {long_ma} → Kararsız"


# --- 5. Bollinger ---
def _bollinger_signal(price, upper, lower):
    """Alt banda yakın → AL, üst banda yakın → SAT"""
    band_width = upper - lower
    if band_width == 0:
        return "NÖTR"
    pct = (price - lower) / band_width
    if pct <= 0.15:
        return "AL"
    elif pct >= 0.85:
        return "SAT"
    return "NÖTR"

def _bollinger_description(price, upper, lower):
    band_width = upper - lower
    if band_width == 0:
        return "Bantlar sıkışmış → Belirsiz"
    pct = (price - lower) / band_width
    if pct <= 0.15:
        return f"Fiyat ({price}) alt banda ({lower}) yakın → Alım fırsatı"
    elif pct >= 0.85:
        return f"Fiyat ({price}) üst banda ({upper}) yakın → Aşırı alım"
    return f"Fiyat ({price}) bantlar arasında → Normal dalgalanma"


# --- 6. Stokastik ---
def _stoch_signal(k, d):
    """K,D ≤20 → AL, K,D ≥80 → SAT"""
    if k <= config.STOCH_OVERSOLD and d <= config.STOCH_OVERSOLD:
        return "AL"
    elif k >= config.STOCH_OVERBOUGHT and d >= config.STOCH_OVERBOUGHT:
        return "SAT"
    return "NÖTR"

def _stoch_description(k, d):
    if k <= config.STOCH_OVERSOLD:
        return f"Stokastik %K:{k} %D:{d} → Aşırı satım bölgesi"
    elif k >= config.STOCH_OVERBOUGHT:
        return f"Stokastik %K:{k} %D:{d} → Aşırı alım bölgesi"
    return f"Stokastik %K:{k} %D:{d} → Nötr bölge"


# --- 7. ADX ---
def _adx_signal(adx, plus_di, minus_di):
    """ADX ≥25 + DI yönü → AL/SAT, ADX < 25 → NÖTR"""
    if adx >= config.ADX_STRONG_TREND:
        if plus_di > minus_di:
            return "AL"
        elif minus_di > plus_di:
            return "SAT"
    return "NÖTR"

def _adx_description(adx, plus_di, minus_di):
    trend = "Güçlü" if adx >= config.ADX_STRONG_TREND else "Zayıf"
    direction = "Yükseliş (+DI üstün)" if plus_di > minus_di else "Düşüş (-DI üstün)"
    return f"ADX: {adx} ({trend} trend) | +DI: {plus_di} | -DI: {minus_di} → {direction}"


# --- 8. CCI ---
def _cci_signal(cci):
    """CCI ≤-100 → AL, ≥100 → SAT"""
    if cci <= config.CCI_OVERSOLD:
        return "AL"
    elif cci >= config.CCI_OVERBOUGHT:
        return "SAT"
    return "NÖTR"

def _cci_description(cci):
    if cci >= config.CCI_OVERBOUGHT:
        return f"CCI {cci} → Aşırı alım bölgesi"
    elif cci <= config.CCI_OVERSOLD:
        return f"CCI {cci} → Aşırı satım bölgesi"
    return f"CCI {cci} → Nötr bölge"


# --- 9. Williams %R ---
def _williams_signal(willr):
    """Williams %R ≤-80 → AL, ≥-20 → SAT"""
    if willr <= config.WILLIAMS_OVERSOLD:
        return "AL"
    elif willr >= config.WILLIAMS_OVERBOUGHT:
        return "SAT"
    return "NÖTR"

def _williams_description(willr):
    if willr >= config.WILLIAMS_OVERBOUGHT:
        return f"Williams %R: {willr} → Aşırı alım bölgesi"
    elif willr <= config.WILLIAMS_OVERSOLD:
        return f"Williams %R: {willr} → Aşırı satım bölgesi"
    return f"Williams %R: {willr} → Nötr bölge"


# --- 10. OBV ---
def _obv_signal(obv_current, obv_sma):
    """OBV > SMA → AL (hacim artıyor), OBV < SMA → SAT"""
    diff_pct = abs(obv_current - obv_sma) / max(abs(obv_sma), 1) * 100
    if diff_pct < 3:  # %3'ten az fark → nötr
        return "NÖTR"
    if obv_current > obv_sma:
        return "AL"
    elif obv_current < obv_sma:
        return "SAT"
    return "NÖTR"

def _obv_description(obv_current, obv_sma):
    if obv_current > obv_sma:
        return f"OBV ortalamanın üzerinde → Hacim alıcıları destekliyor"
    elif obv_current < obv_sma:
        return f"OBV ortalamanın altında → Hacim satıcıları destekliyor"
    return f"OBV ortalamaya yakın → Hacim nötr"


# --- 11. MFI ---
def _mfi_signal(mfi):
    """MFI ≤20 → AL (aşırı satım), ≥80 → SAT (aşırı alım)"""
    if mfi <= config.MFI_OVERSOLD:
        return "AL"
    elif mfi >= config.MFI_OVERBOUGHT:
        return "SAT"
    return "NÖTR"

def _mfi_description(mfi):
    if mfi >= config.MFI_OVERBOUGHT:
        return f"MFI {mfi} → Aşırı alım, para çıkışı olabilir"
    elif mfi <= config.MFI_OVERSOLD:
        return f"MFI {mfi} → Aşırı satım, para girişi olabilir"
    return f"MFI {mfi} → Nötr bölge"


# --- 12. Parabolic SAR ---
def _psar_description(price, sar_value, trend):
    if trend == "AL":
        return f"SAR ({sar_value}) fiyatın ({price}) altında → Yükseliş trendi"
    elif trend == "SAT":
        return f"SAR ({sar_value}) fiyatın ({price}) üzerinde → Düşüş trendi"
    return f"SAR: {sar_value} | Fiyat: {price} → Belirsiz"


# --- 13. Ichimoku ---
def _ichimoku_signal(price, cloud_top, cloud_bottom, tenkan, kijun):
    """Fiyat > Bulut → AL, Fiyat < Bulut → SAT, Bulut içinde → NÖTR"""
    if price > cloud_top and tenkan > kijun:
        return "AL"
    elif price < cloud_bottom and tenkan < kijun:
        return "SAT"
    return "NÖTR"

def _ichimoku_description(price, cloud_top, cloud_bottom):
    if price > cloud_top:
        return f"Fiyat ({price}) bulutun ({cloud_top}) üzerinde → Güçlü yükseliş"
    elif price < cloud_bottom:
        return f"Fiyat ({price}) bulutun ({cloud_bottom}) altında → Güçlü düşüş"
    return f"Fiyat ({price}) bulut içinde ({cloud_bottom}-{cloud_top}) → Kararsız"


# --- 14. ROC ---
def _roc_signal(roc):
    """ROC > 2 → AL, ROC < -2 → SAT, -2 ile 2 arası → NÖTR"""
    if roc > 2:
        return "AL"
    elif roc < -2:
        return "SAT"
    return "NÖTR"

def _roc_description(roc):
    if roc > 0:
        return f"ROC %{roc} → Pozitif momentum"
    elif roc < 0:
        return f"ROC %{roc} → Negatif momentum"
    return f"ROC %{roc} → Momentum yok"


# --- 15. CMF ---
def _cmf_signal(cmf):
    """CMF > 0.05 → AL, CMF < -0.05 → SAT"""
    if cmf > config.CMF_BULLISH:
        return "AL"
    elif cmf < config.CMF_BEARISH:
        return "SAT"
    return "NÖTR"

def _cmf_description(cmf):
    if cmf > config.CMF_BULLISH:
        return f"CMF {cmf:.4f} → Para girişi var, alım baskısı"
    elif cmf < config.CMF_BEARISH:
        return f"CMF {cmf:.4f} → Para çıkışı var, satış baskısı"
    return f"CMF {cmf:.4f} → Nötr para akışı"


# --- 16. ATR ---
def _atr_signal(price, atr):
    """ATR dalgalanma ölçer. Nötr kalarak stop-loss takibi sağlar."""
    return "NÖTR"

def _atr_description(price, atr):
    return f"ATR: {atr} → Günlük ortalama dalgalanma payı. Stop-loss: {round(price - atr*config.ATR_MULTIPLIER, 2)} seviyesine çekilebilir."

# --- 17. McGinley Dynamic ---
def _mcginley_signal(price, mcgd):
    """Fiyat > McGinley → AL, Fiyat < McGinley → SAT"""
    if price > mcgd:
        return "AL"
    elif price < mcgd:
        return "SAT"
    return "NÖTR"

def _mcginley_description(price, mcgd):
    if price > mcgd:
        return f"Fiyat ({price}), McGinley ({mcgd}) üzerinde → Yükseliş"
    elif price < mcgd:
        return f"Fiyat ({price}), McGinley ({mcgd}) altında → Düşüş"
    return f"Fiyat ({price}) McGinley ({mcgd}) seviyesinde → Nötr"

# --- 18. SMI ---
def _smi_signal(smi_val, smi_sig):
    """SMI > Signal → AL, SMI < Signal → SAT"""
    if smi_val > smi_sig:
        return "AL"
    elif smi_val < smi_sig:
        return "SAT"
    return "NÖTR"

def _smi_description(smi_val, smi_sig):
    if smi_val > smi_sig:
        return f"SMI ({smi_val}) Sinyal ({smi_sig}) üzerinde → Pozitif momentum"
    elif smi_val < smi_sig:
        return f"SMI ({smi_val}) Sinyal ({smi_sig}) altında → Negatif momentum"
    return "SMI ve Sinyal kesişiyor → Kararsız"

# --- 19. Zigzag ---
def _zigzag_signal(price, last_pivot, prev_pivot):
    """Son pivot dip ise ve fiyat yükseliyorsa AL, tepe ise ve fiyat düşüyorsa SAT"""
    if last_pivot > prev_pivot: # Son pivot bir tepeydi
        if price > last_pivot:
            return "AL"
        else:
            return "SAT"
    else: # Son pivot bir dipti
        if price > last_pivot:
            return "AL"
        else:
            return "SAT"

def _zigzag_description(price, last_pivot, prev_pivot):
    if last_pivot > prev_pivot:
        if price > last_pivot:
            return f"Zigzag: Son tepe ({last_pivot}) aşıldı → Yükseliş"
        else:
            return f"Zigzag: Son tepe ({last_pivot}) altında → Düzeltme"
    else:
        if price > last_pivot:
            return f"Zigzag: Son dip ({last_pivot}) korundu → Tepki Alımı"
        else:
            return f"Zigzag: Son dip ({last_pivot}) kırıldı → Düşüş"


# ============================================================
# TEKNİK SKOR HESAPLAMA — 19 İndikatör
# ============================================================

def get_technical_score(indicators):
    """
    19 teknik göstergeden 0-100 arası skor hesaplar.
    AL = yüksek skor, SAT = düşük skor, NÖTR = 50

    Returns:
        int: 0-100 arası teknik skor
    """
    if not indicators:
        return 50

    scores = []

    # Sinyal → skor dönüşümü
    signal_score = {"AL": 100, "SAT": 0, "NÖTR": 50}

    # RSI — özel: değer bazlı interpolasyon
    if "rsi" in indicators:
        rsi = indicators["rsi"]["value"]
        sig = indicators["rsi"]["signal"]
        if sig == "AL":
            score = 100
        elif sig == "SAT":
            score = 0
        else:
            # 30-70 arası → 50 merkezli (RSI 50 = skor 50)
            score = 50 + (50 - rsi) * 1.25
            score = max(10, min(90, score))
        scores.append(("rsi", score))

    # Genel desenli indikatörler
    indicator_keys = [
        "macd", "sma", "ema", "bollinger", "stochastic",
        "adx", "cci", "williams", "obv", "mfi",
        "psar", "ichimoku", "roc", "cmf", "atr", "mcginley", "smi", "zigzag"
    ]

    for key in indicator_keys:
        if key in indicators:
            sig = indicators[key]["signal"]
            scores.append((key, signal_score.get(sig, 50)))

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
        "obv": config.WEIGHT_OBV,
        "mfi": config.WEIGHT_MFI,
        "psar": config.WEIGHT_PSAR,
        "ichimoku": config.WEIGHT_ICHIMOKU,
        "roc": config.WEIGHT_ROC,
        "cmf": config.WEIGHT_CMF,
        "atr": config.WEIGHT_ATR,
        "mcginley": config.WEIGHT_MCGINLEY,
        "smi": config.WEIGHT_SMI,
        "zigzag": config.WEIGHT_ZIGZAG,
    }

    total_weight = sum(weights.get(name, 0.05) for name, _ in scores)
    weighted_score = sum(weights.get(name, 0.05) * sc for name, sc in scores)

    return round(weighted_score / total_weight)


def _calculate_zigzag(close, deviation=5.0):
    """
    Çökme korumalı, saf Python Zigzag pivot hesaplaması.
    pandas_ta.zigzag'ın illikit veya yatay seyreden hisselerde sebep olduğu
    C-level çökme/kilitlenme (segfault) riskini sıfırlar.
    """
    n = len(close)
    if n < 2:
        return None
    
    pivots_v = [np.nan] * n
    pivots_d = [0] * n
    
    last_pivot_val = close.iloc[0]
    last_pivot_idx = 0
    trend = 0
    
    for i in range(1, n):
        if last_pivot_val == 0 or pd.isna(last_pivot_val):
            last_pivot_val = close.iloc[i]
            last_pivot_idx = i
            continue
        diff_pct = ((close.iloc[i] - last_pivot_val) / last_pivot_val) * 100
        if diff_pct >= deviation:
            trend = 1
            last_pivot_val = close.iloc[i]
            last_pivot_idx = i
            break
        elif diff_pct <= -deviation:
            trend = -1
            last_pivot_val = close.iloc[i]
            last_pivot_idx = i
            break
            
    if trend == 0:
        return None

    pivots_v[last_pivot_idx] = last_pivot_val
    pivots_d[last_pivot_idx] = trend
    
    for i in range(last_pivot_idx + 1, n):
        if trend == 1:
            if close.iloc[i] > last_pivot_val:
                last_pivot_val = close.iloc[i]
                last_pivot_idx = i
            else:
                if last_pivot_val != 0 and not pd.isna(last_pivot_val):
                    retrace = ((last_pivot_val - close.iloc[i]) / last_pivot_val) * 100
                    if retrace >= deviation:
                        pivots_v[last_pivot_idx] = last_pivot_val
                        pivots_d[last_pivot_idx] = 1
                        trend = -1
                        last_pivot_val = close.iloc[i]
                        last_pivot_idx = i
        else:
            if close.iloc[i] < last_pivot_val:
                last_pivot_val = close.iloc[i]
                last_pivot_idx = i
            else:
                if last_pivot_val != 0 and not pd.isna(last_pivot_val):
                    retrace = ((close.iloc[i] - last_pivot_val) / last_pivot_val) * 100
                    if retrace >= deviation:
                        pivots_v[last_pivot_idx] = last_pivot_val
                        pivots_d[last_pivot_idx] = -1
                        trend = 1
                        last_pivot_val = close.iloc[i]
                        last_pivot_idx = i
                        
    pivots_v[last_pivot_idx] = last_pivot_val
    pivots_d[last_pivot_idx] = trend
    
    df_out = pd.DataFrame({
        "ZIGZAGs": pivots_d,
        "ZIGZAGv": pivots_v,
    }, index=close.index)
    
    return df_out
