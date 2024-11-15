import pandas as pd
import numpy as np
import logging

import influx_utils as idb

from datetime import datetime, timedelta

###################### Analyse des indicateurs techniques ######################
def analyse_adi(adi, prev_adi):
    adi_trend = "neutral"
    if adi > prev_adi:
        adi_trend = "bullish"
    elif adi < prev_adi:
        adi_trend = "bearish"
    
    fields = {
        "adi": adi,
        "prev_adi": prev_adi,
        "trend": adi_trend
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="adi", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    return fields

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

    fields = {
        "spread_band": spread_band,
        "spread_price": spread_price,
        "volatility": volatility,
        "volatility_pc": volatility_pc,
        "trend": bol_trend
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="bollinger", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    return fields

def analyse_ema(emas):
    ema_trend = "neutral"
    if all(emas[i] > emas[i+1] for i in range(len(emas)-1)):
        ema_trend = "bullish"
    elif emas[-1] > emas[0]:
        ema_trend = "bearish"
    
    fields = {
        "ema7": emas[0],
        "ema30": emas[1],
        "ema50": emas[2],
        "ema100": emas[3],
        "ema150": emas[4],
        "ema200": emas[5],
        "trend": ema_trend
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="ema", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    return fields

# def analyse_macd(macd, signal, histogram, prev_macd, prev_signal):
def analyse_macd(macd, signal, histogram):
    macd_trend = "neutral"
    
    # Vérifier s'il y a divergence
    # bullish_divergence = prev_macd < prev_signal and macd > signal  # Divergence haussière
    # bearish_divergence = prev_macd > prev_signal and macd < signal  # Divergence baissière
    bullish_divergence = macd > signal  # Divergence haussière
    bearish_divergence = macd < signal  # Divergence baissière

    # Évaluation de la tendance
    if macd > 0:
        # if bullish_divergence:
        #     macd_trend = "bullish divergence"
        if macd > signal:
            macd_trend = "bullish"
    
    elif macd < 0:
        # if bearish_divergence:
        #     macd_trend = "bearish divergence"
        if macd < signal:
            macd_trend = "bearish"
    
    fields = {
        "macd": macd,
        "signal": signal,
        # "prev_macd": prev_macd,
        # "prev_signal": prev_signal,
        "histogram": histogram,
        "trend": macd_trend
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="macd", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    return fields

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
    
    fields = {
        "rsi": rsi,
        "prev_rsi": prev_rsi,
        "trend": rsi_trend
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="stoch_rsi", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    return fields

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
        
    fields = {
        "blue": blue,
        "orange": orange,
        "prev_blue": prev_blue,
        "prev_orange": prev_orange,
        "trend": srsi_trend
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="stoch_rsi", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    return fields

def analyse_volume(data, volume_column='volume', window=14):
    """Analyse le volume pour déterminer si la tendance est bullish ou bearish."""
    data['volume_ma'] = data[volume_column].rolling(window=window).mean()

    current_volume = data[volume_column].iloc[-1]  # Valeur actuelle de volume
    current_volume_ma = data['volume_ma'].iloc[-1]  # Moyenne mobile du volume

    vol_trend = 'neutral'  # Valeur par défaut

    # Conditions de tendance
    if current_volume > current_volume_ma:
        vol_trend = 'bullish'
    elif current_volume < current_volume_ma:
        vol_trend = 'bearish'
    
    fields = {
        "current_volume": current_volume,
        "current_volume_ma": current_volume_ma,
        "trend": vol_trend
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="volume", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    return fields

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
    
    # logging.info(f"Choppiness Indicator: Calculated for window={window}")

    fields = {
        "high": high,
        "low": low,
        "close": close,
        "highh": highh,
        "lowl": lowl,
        "window": window,
        "trend": chop_serie
    }   
    # idb.write_indicator_to_influx(fields=fields, indicator="chop_index", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    # return fields
    return pd.Series(chop_serie, name="CHOP")