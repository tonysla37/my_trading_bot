import pandas as pd
import numpy as np

# Analyse des indicateurs techniques
def analyse_adi(adi, prev_adi):
    if adi > prev_adi:
        return "bullish"
    elif adi < prev_adi:
        return "bearish"
    else:
        return "neutral"

def analyse_bollinger(high, low, average, close):
    spread_band = high - low
    spread_price = close - average
    volatility_pc = (spread_band / close) * 100
    volatility = "high" if volatility_pc > 20 else "low"

    if close > high:
        bol_trend = "overbuy"
    elif close < low:
        bol_trend = "oversell"
    else:
        bol_trend = "over_sma" if close > average else "under_sma"

    return {
        "trend": bol_trend,
        "spread_band": spread_band,
        "spread_price": spread_price,
        "volatility": volatility,
        "volatility_pc": volatility_pc
    }

def analyse_ema(emas):
    if all(emas[i] > emas[i+1] for i in range(len(emas)-1)):
        return "bullish"
    elif emas[-1] > emas[0]:
        return "bearish"
    else:
        return "neutral"

def analyse_macd(macd, signal, histogram):
    if signal < 0 and histogram < 0:
        return "bearish"
    elif signal > 0 and histogram > 0:
        return "bullish"
    else:
        return "neutral"

def analyse_rsi(rsi, prev_rsi):
    rsi_trend = "undefined"
    if rsi <= 30:
        rsi_trend = "oversell"
    elif rsi >= 70:
        rsi_trend = "overbuy"
    else:
        if rsi > 50:
            if rsi > prev_rsi:
                rsi_trend = "bullish"
            elif rsi < prev_rsi:
                rsi_trend = "bearish divergence"
            else:
                rsi_trend = "neutral"
        elif rsi < 50:
            if rsi < prev_rsi:
                rsi_trend = "bearish"
            elif rsi > prev_rsi:
                rsi_trend = "bullish divergence"
            else:
                rsi_trend = "neutral"
    return {"trend": rsi_trend, "rsi": rsi, "prev_rsi": prev_rsi}

def analyse_stoch_rsi(blue, orange, prev_blue, prev_orange):
    srsi_trend = "undefined"
    if blue <= 20 or orange <= 20:
        srsi_trend = "oversell"
    elif blue >= 80 or orange >= 80:
        srsi_trend = "overbuy"
    else:
        if blue > orange and blue > prev_blue and orange > prev_orange:
            srsi_trend = "bullish"
        elif blue < orange and blue < prev_blue and orange < prev_orange:
            srsi_trend = "bearish"
        else:
            srsi_trend = "neutral"
    return {"trend": srsi_trend, "blue": blue, "orange": orange, "prev_blue": prev_blue, "prev_orange": prev_orange}

def get_chop(high, low, close, window):
    ''' Choppiness indicator
    '''
    tr1 = pd.DataFrame(high - low).rename(columns={0: 'tr1'})
    tr2 = pd.DataFrame(abs(high - close.shift(1))
                       ).rename(columns={0: 'tr2'})
    tr3 = pd.DataFrame(abs(low - close.shift(1))
                       ).rename(columns={0: 'tr3'})
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').dropna().max(axis=1)
    atr = tr.rolling(1).mean()
    highh = high.rolling(window).max()
    lowl = low.rolling(window).min()
    chop_serie = 100 * np.log10((atr.rolling(window).sum()) /
                          (highh - lowl)) / np.log10(window)
    return pd.Series(chop_serie, name="CHOP")
