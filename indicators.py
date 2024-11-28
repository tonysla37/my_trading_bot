import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging

import influx_utils as idb

from datetime import datetime, timedelta
from pytrends.request import TrendReq

###################### Analyse des indicateurs techniques ######################
def analyse_adi(adi, prev_adi):
    adi_trend = "neutral"
    
    # Définir des seuils pour les tendances fortes et faibles
    trend_strength = "weak"
    threshold = 0.1  # Ce seuil peut être ajusté selon vos besoins
    difference = adi - prev_adi

    if difference > 0:
        adi_trend = "bullish"
    elif difference < 0:
        adi_trend = "bearish"
    
    # Vérification de la force de la tendance
    if abs(difference) >= threshold:
        trend_strength = "strong"
    
    fields = {
        "trend": adi_trend,
        "adi": adi,
        "prev_adi": prev_adi,
        "strength": trend_strength
    }  
    idb.write_indicator_to_influx(fields=fields, indicator="adi", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_bollinger(high, low, average, close):
    spread_band = high - low
    spread_price = close - average
    volatility_pc = (spread_band / close) * 100
    volatility = "high" if volatility_pc > 20 else "low"

    # Analyse des conditions par rapport aux bandes
    if close > high:
        bol_trend = "overbuy"
    elif close < low:
        bol_trend = "oversell"
    else:
        bol_trend = "over_sma" if close > average else "under_sma"

    # Evaluation des signaux de retournement
    signal_strength = ""
    if bol_trend in ["overbuy", "oversell"]:
        signal_strength = "potential reversal"
    elif bol_trend in ["over_sma", "under_sma"]:
        signal_strength = "continuation possible"

    # Détection d'une condition extrême
    extreme_condition = "none"
    if close > (high + 2 * (high - low)):  # Par exemple, trop au-dessus de la bande supérieure
        extreme_condition = "extreme overbuy"
    elif close < (low - 2 * (high - low)):  # Trop en-dessous de la bande inférieure
        extreme_condition = "extreme oversell"

    fields = {
        "trend": bol_trend,
        "spread_band": spread_band,
        "spread_price": spread_price,
        "volatility": volatility,
        "volatility_pc": volatility_pc,
        "signal_strength": signal_strength,
        "extreme_condition": extreme_condition
    }
    idb.write_indicator_to_influx(fields=fields, indicator="bollinger", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_ema(emas):
    ema_trend = "neutral"
    if all(emas[i] > emas[i+1] for i in range(len(emas)-1)):
        ema_trend = "bullish"
    elif emas[-1] > emas[0]:
        ema_trend = "bearish"
    
    # /!\ définir la tendance de fond

    # fields = {
    #     "trend": ema_trend,
    #     "ema7": emas[0],
    #     "ema30": emas[1],
    #     "ema50": emas[2],
    #     "ema100": emas[3],
    #     "ema150": emas[4],
    #     "ema200": emas[5]
    # }
    fields = {
        "trend": ema_trend,
        "ema5": emas[0],
        "ema10": emas[1],
        "ema20": emas[2],
        "ema50": emas[3]
    }
    idb.write_indicator_to_influx(fields=fields, indicator="ema", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_fear_and_greed(index_value):
    """Analyse l'indice de peur et de cupidité et retourne un signal de trading."""
    
    if index_value < 20:
        sentiment = "extreme fear"
        trend = "bullish"
        strength = "strong"
        recommendation = "consider strong buying opportunities"
    elif index_value < 40:
        sentiment = "fear"
        trend = "bullish"
        strength = "weak"
        recommendation = "exercise caution; consider buying opportunities"
    elif index_value < 60:
        sentiment = "neutral"
        trend = "neutral"
        strength = "n/a"  # Pas de tendance claire
        recommendation = "hold; wait for stronger signals"
    elif index_value < 80:
        sentiment = "greed"
        trend = "bearish"
        strength = "weak"
        recommendation = "exercise caution; consider selling"
    else:
        sentiment = "extreme greed"
        trend = "bearish"
        strength = "strong"
        recommendation = "consider taking profits; sell positions"

    fields = {
        "trend": trend,
        "index_value": index_value,
        "sentiment": sentiment,
        "strength": strength,
        "recommendation": recommendation
    }
    idb.write_indicator_to_influx(fields=fields, indicator="fear_and_greed", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_macd(macd, signal, histogram, prev_macd, prev_signal):
# def analyse_macd(macd, signal, histogram):
    macd_trend = "neutral"
    
    # Vérifier s'il y a divergence
    bullish_divergence = prev_macd < prev_signal and macd > signal  # Divergence haussière
    bearish_divergence = prev_macd > prev_signal and macd < signal  # Divergence baissière
    # bullish_divergence = macd > signal  # Divergence haussière
    # bearish_divergence = macd < signal  # Divergence baissière

    # Évaluation de la tendance
    if macd > 0:
        if bullish_divergence:
            macd_trend = "bullish divergence"
        if macd > signal:
            macd_trend = "bullish"
    
    elif macd < 0:
        if bearish_divergence:
            macd_trend = "bearish divergence"
        # if macd < signal:
        #     macd_trend = "bearish"
    
    fields = {
        "trend": macd_trend,
        "macd": macd,
        "signal": signal,
        "prev_macd": prev_macd,
        "prev_signal": prev_signal,
        "histogram": histogram
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="macd", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_rsi(rsi, prev_rsi):
    rsi_trend = "undefined"

    # Analyse des zones de surachat et de survente
    if rsi <= 30:
        rsi_trend = "oversell"
    elif rsi >= 70:
        rsi_trend = "overbuy"
    else:
        # Zone neutre
        if rsi > 50:
            if rsi > prev_rsi:
                rsi_trend = "bullish trend"
            elif rsi < prev_rsi:
                rsi_trend = "bearish divergence"
            else:
                rsi_trend = "neutral"
        elif rsi < 50:
            if rsi < prev_rsi:
                rsi_trend = "bearish trend"
            elif rsi > prev_rsi:
                rsi_trend = "bullish divergence"
            else:
                rsi_trend = "neutral"
    
    # Ajout d'une nuance sur la force de la tendance
    if rsi_trend in ["bullish trend", "bearish trend"]:
        if abs(rsi - prev_rsi) < 5:
            rsi_trend += " (weak)"
        else:
            rsi_trend += " (strong)"
    
    fields = {
        "trend": rsi_trend,
        "rsi": rsi,
        "prev_rsi": prev_rsi
    }   
    idb.write_indicator_to_influx(fields=fields, indicator="stoch_rsi", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_sma(smas):
    sma_trend = "neutral"
    if all(smas[i] > smas[i+1] for i in range(len(smas)-1)):
        sma_trend = "bullish"
    elif smas[-1] > smas[0]:
        sma_trend = "bearish"
    
    fields = {
        "trend": sma_trend,
        "sma50": smas[0],
        "sma200": smas[1]
    }
    idb.write_indicator_to_influx(fields=fields, indicator="sma", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_stoch_rsi(blue, orange, prev_blue, prev_orange):
    srsi_trend = "undefined"
    srsi_strength = "weak"

    # Conditions de surachat et de survente
    if blue <= 20 or orange <= 20:
        srsi_trend = "oversell"
    elif blue >= 80 or orange >= 80:
        srsi_trend = "overbuy"
    else:
        # Analyse de la tendance principale
        if blue > orange:
            srsi_trend = "bullish"
            if blue > prev_blue and orange > prev_orange:
                srsi_strength = "strong"
        elif blue < orange:
            srsi_trend = "bearish"
            if blue < prev_blue and orange < prev_orange:
                srsi_strength = "strong"
        else:
            srsi_trend = "neutral"

    # Analyse de la divergence
    divergence = "none"
    if (blue > prev_blue and orange < prev_orange) or (blue < prev_blue and orange > prev_orange):
        divergence = "potential divergence"

    fields = {
        "trend": srsi_trend,
        "blue": blue,
        "orange": orange,
        "prev_blue": prev_blue,
        "prev_orange": prev_orange,
        "strength": srsi_strength,
        "divergence": divergence
    } 
    idb.write_indicator_to_influx(fields=fields, indicator="stoch_rsi", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_support_resistance(price, support, resistance):
    if price > resistance:
        sr_trend = "bullish"
    elif price < support:
        sr_trend = "bearish"
    else:
        sr_trend = "neutral"

    fields = {
        "trend": sr_trend,
        "price": price,
        "support": support,
        "resistance": resistance
    }
    idb.write_indicator_to_influx(fields=fields, indicator="support_resistance", timestamp=int(datetime.now().timestamp() * 1e9))
    return fields

def analyse_volume(data, volume_column='volume', short_window=5, long_window=14):
    """Analyse le volume pour déterminer si la tendance est bullish ou bearish et détecter des activités de baleines."""
    data['volume_short_ma'] = data[volume_column].rolling(window=short_window).mean()
    data['volume_long_ma'] = data[volume_column].rolling(window=long_window).mean()
    
    current_volume = data[volume_column].iloc[-1]  # Valeur actuelle de volume
    current_long_ma = data['volume_long_ma'].iloc[-1]   # Moyenne mobile longue

    vol_trend = 'neutral'  # Valeur par défaut
    volume_change_strength = ''

    # Conditions de tendance
    if current_volume > current_long_ma:
        vol_trend = 'bullish'
    elif current_volume < current_long_ma:
        vol_trend = 'bearish'

    # Évaluation de la variation de volume par rapport à la période précédente
    previous_volume = data[volume_column].iloc[-2]
    volume_trend_change = current_volume - previous_volume

    # Détection d'un volume élevé suggérant l'action d'une baleine
    volume_alert = 'normal'
    whale_activity = False
    if current_volume > 2 * current_long_ma:
        volume_alert = 'high volume'
        whale_activity = True  # Volume significatif identifié

    # Analyse directionnelle : pression d'achat ou de vente
    if volume_trend_change > 0 and vol_trend == 'bullish':
        price_direction = "strong buying pressure"
    elif volume_trend_change < 0 and vol_trend == 'bearish':
        price_direction = "strong selling pressure"
    else:
        price_direction = ""

    fields = {
        "trend": vol_trend,
        "current_volume": current_volume,
        "current_long_ma": current_long_ma,
        "volume_trend_change": volume_trend_change,
        "volume_alert": volume_alert,
        "whale_activity": whale_activity,
        "price_direction": price_direction
    }
    idb.write_indicator_to_influx(fields=fields, indicator="volume", timestamp=int(datetime.now().timestamp() * 1e9))
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
        "trend": chop_serie,
        "high": high,
        "low": low,
        "close": close,
        "highh": highh,
        "lowl": lowl,
        "window": window
    }   
    # idb.write_indicator_to_influx(fields=fields, indicator="chop_index", timestamp=int(datetime.utcnow().timestamp() * 1e9))
    # return fields
    return pd.Series(chop_serie, name="CHOP")

def calculate_fibonacci_retracement(data):
    # Supposons que data soit un DataFrame avec des colonnes de prix

    # Trouver le point haut et le point bas dans la période choisie
    price_max = data['close'].max()
    price_min = data['close'].min()

    # Calculer les niveaux de Fibonacci
    diff = price_max - price_min
    retracement_levels = {
        "Level 0%": price_max,
        "Level 23.6%": price_max - diff * 0.236,
        "Level 38.2%": price_max - diff * 0.382,
        "Level 50%": price_max - diff * 0.5,
        "Level 61.8%": price_max - diff * 0.618,
        "Level 100%": price_min,
    }
    
    # Calcul des niveaux d'extension
    extension_levels = {
        "Level 161.8%": price_max + diff * 0.618,
        "Level 261.8%": price_max + diff * 1.618,
    }

    idb.write_indicator_to_influx(fields=retracement_levels, indicator="retracement_fibonacci", timestamp=int(datetime.now().timestamp() * 1e9))
    idb.write_indicator_to_influx(fields=extension_levels, indicator="extension_fibonacci", timestamp=int(datetime.now().timestamp() * 1e9))
    return retracement_levels, extension_levels


def define_googletrend(crypto_term):
    # Initialiser Pytrends
    pytrends = TrendReq(hl='en-US', tz=360)

    # Obtenir les données de Google Trends
    pytrends.build_payload([crypto_term], timeframe='today 3-m', geo='', gprop='')
    trend_data = pytrends.interest_over_time()

    # Vérifie si les données existent
    if not trend_data.empty:
        # Extraire les dates et les valeurs d'intérêt
        trend_data = trend_data[crypto_term]
        
        # Visualisation des données
        plt.figure(figsize=(12, 6))
        trend_data.plot(title=f'Google Trends Interest for {crypto_term}', ylabel='Interest', xlabel='Date')
        plt.grid()
        plt.show()

        # Calcul de la tendance de fond
        growing_interest = trend_data.diff().dropna()
        
        if growing_interest.iloc[-1] > 0:
            trend_status = "Growing Interest"
        else:
            trend_status = "Declining Interest"

        fields = {
            "trend_status": trend_status
        }

    idb.write_indicator_to_influx(fields=fields, indicator="google_trend", timestamp=int(datetime.now().timestamp() * 1e9))
    return trend_status
