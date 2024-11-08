import pandas as pd
import numpy as np
import logging

# Analyse des indicateurs techniques
def analyse_adi(adi, prev_adi):
    trend = "neutral"
    if adi > prev_adi:
        trend = "bullish"
    elif adi < prev_adi:
        trend = "bearish"
    
    logging.info(f"ADI Analysis: Current ADI={adi}, Previous ADI={prev_adi}, Trend={trend}")
    return trend

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

    result = {
        "trend": bol_trend,
        "spread_band": spread_band,
        "spread_price": spread_price,
        "volatility": volatility,
        "volatility_pc": volatility_pc
    }
    
    logging.info(f"Bollinger Analysis: Close={close}, High={high}, Low={low}, Average={average}, Result={result}")
    return result

def analyse_ema(emas):
    trend = "neutral"
    if all(emas[i] > emas[i+1] for i in range(len(emas)-1)):
        trend = "bullish"
    elif emas[-1] > emas[0]:
        trend = "bearish"
    
    logging.info(f"EMA Analysis: EMAs={emas}, Trend={trend}")
    return trend

def analyse_macd(macd, signal, histogram):
    trend = "neutral"
    if signal < 0 and histogram < 0:
        trend = "bearish"
    elif signal > 0 and histogram > 0:
        trend = "bullish"
    
    logging.info(f"MACD Analysis: MACD={macd}, Signal={signal}, Histogram={histogram}, Trend={trend}")
    return trend

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
    
    result = {"trend": rsi_trend, "rsi": rsi, "prev_rsi": prev_rsi}
    logging.info(f"RSI Analysis: Current RSI={rsi}, Previous RSI={prev_rsi}, Result={result}")
    return result

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
    
    result = {"trend": srsi_trend, "blue": blue, "orange": orange, "prev_blue": prev_blue, "prev_orange": prev_orange}
    logging.info(f"Stochastic RSI Analysis: Current Blue={blue}, Current Orange={orange}, Previous Blue={prev_blue}, Previous Orange={prev_orange}, Result={result}")
    return result

def get_chop(high, low, close, window):
    ''' Choppiness indicator
    '''
    tr1 = pd.DataFrame(high - low).rename(columns={0: 'tr1'})
    tr2 = pd.DataFrame(abs(high - close.shift(1))).rename(columns={0: 'tr2'})
    tr3 = pd.DataFrame(abs(low - close.shift(1))).rename(columns={0: 'tr3'})
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').dropna().max(axis=1)
    atr = tr.rolling(1).mean()
    highh = high.rolling(window).max()
    lowl = low.rolling(window).min()
    chop_serie = 100 * np.log10((atr.rolling(window).sum()) / (highh - lowl)) / np.log10(window)
    
    logging.info(f"Choppiness Indicator: Calculated for window={window}")
    return pd.Series(chop_serie, name="CHOP")