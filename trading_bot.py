import os
import time
import logging
import datetime
from math import floor

import pandas as pd
import numpy as np
import ta
from binance.client import Client
from pykrakenapi import KrakenAPI
# from discord import Webhook
# from discord import RequestsWebhookAdapter
from dotenv import load_dotenv

import functions as fx  # Votre module optimisé

import warnings

# Ignorer tous les FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration de la journalisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)

def get_binance_data(client, symbol, interval, start_str):
    """
    Récupère les données historiques de Binance.

    Args:
        client (Client): Instance du client Binance.
        symbol (str): Symbole de trading (e.g., 'BTCUSDT').
        interval (str): Intervalle de temps (e.g., Client.KLINE_INTERVAL_1HOUR).
        start_str (str): Date de début (e.g., '01 january 2017').

    Returns:
        pd.DataFrame: DataFrame contenant les données de trading.
    """
    try:
        klines = client.get_historical_klines(symbol, interval, start_str)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
        ])
        # Convertir les colonnes en types numériques
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        # Convertir le timestamp en datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        logging.info(f"Données Binance récupérées avec succès pour {symbol}")
        return df
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des données Binance : {e}")
        return pd.DataFrame()

def get_kraken_data(api, symbol, interval, since):
    """
    Récupère les données historiques de Kraken.

    Args:
        api (KrakenAPI): Instance de l'API Kraken.
        symbol (str): Symbole de trading (e.g., 'XXBTZUSD').
        interval (int): Intervalle de temps en minutes (e.g., 60).
        since (int): Timestamp Unix de début.

    Returns:
        pd.DataFrame: DataFrame contenant les données de trading.
    """
    try:
        df = api.get_ohlc_data(pair=symbol, interval=interval, since=since)[0]
        # Convertir les colonnes en types numériques
        for col in ['open', 'high', 'low', 'close', 'vwap', 'volume', 'count']:
            df[col] = pd.to_numeric(df[col])
        df.reset_index(inplace=True)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('timestamp', inplace=True)
        df.drop(columns=['time'], inplace=True)
        logging.info(f"Données Kraken récupérées avec succès pour {symbol}")
        return df
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des données Kraken : {e}")
        return pd.DataFrame()

def prepare_data(df):
    """
    Prépare les données en calculant les indicateurs techniques.

    Args:
        df (pd.DataFrame): DataFrame contenant les données de trading.

    Returns:
        pd.DataFrame: DataFrame enrichi avec les indicateurs techniques.
    """
    try:
        # Calcul des indicateurs techniques
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()

        # Assurez-vous que les colonnes nécessaires existent ('low', 'high', 'close')
        df['stoch_rsi'] = ta.momentum.stochrsi(close=df['close'], window=14, smooth1=3, smooth2=3)

        # Optionnellement, calculez les lignes de signal pour une meilleure interprétation
        df['stoch_rsi_k'] = ta.momentum.stochrsi_k(close=df['close'], window=14, smooth1=3, smooth2=3)
        df['stoch_rsi_d'] = ta.momentum.stochrsi_d(close=df['close'], window=14, smooth1=3, smooth2=3)
        
        stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
        df['stochastic'] = stoch.stoch()
        df['stoch_signal'] = stoch.stoch_signal()

        macd = ta.trend.MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histo'] = macd.macd_diff()

        df['awesome_oscillador'] = ta.momentum.AwesomeOscillatorIndicator(high=df['high'], low=df['low'], window1=5, window2=34).awesome_oscillator()

        # Moyennes mobiles exponentielles
        for window in [7, 30, 50, 100, 150, 200]:
            df[f'ema{window}'] = ta.trend.EMAIndicator(close=df['close'], window=window).ema_indicator()

        # Bandes de Bollinger
        bollinger = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bol_high'] = bollinger.bollinger_hband()
        df['bol_low'] = bollinger.bollinger_lband()
        df['bol_medium'] = bollinger.bollinger_mavg()
        df['bol_gap'] = bollinger.bollinger_wband()
        df['bol_higher'] = bollinger.bollinger_hband_indicator()
        df['bol_lower'] = bollinger.bollinger_lband_indicator()

        # Indicateur Choppiness
        df['chop'] = fx.get_chop(high=df['high'], low=df['low'], close=df['close'], window=14)

        # Indicateur ADI
        df['adi'] = ta.volume.acc_dist_index(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'])

        logging.info("Indicateurs techniques calculés avec succès")
        return df
    except Exception as e:
        logging.error(f"Erreur lors de la préparation des données : {e}")
        return df

def analyse_stoch_rsi(blue, orange, prev_blue, prev_orange):
    srsi_trend - "undefined"
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

def analyse_rsi(rsi, prev_rsi):
    rsi_trend - "undefined"
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

def main():
    # Configuration des paramètres
    pair_symbol = 'BTCUSDT'  # Symbole Binance
    fiat_symbol = 'USD'
    crypto_symbol = 'BTC'
    my_truncate = 5
    protection = {
        "sl_level": 0.02,
        "tp1_level": 0.1,
        "sl_amount": 1,
        "tp1_amount": 1
    }
    buy_ready = True
    sell_ready = True
    bench_mode = True  # Mode backtest
    backtest = True
    risk_level = "Max"

    # Définir le niveau de risque
    risk = fx.define_risk(risk_level)
    logging.info(f"Niveau de risque défini : {risk_level} ({risk})")

    # Initialisation des clients API
    if bench_mode:
        client = Client()  # Client sans clés API pour le backtest
        df = get_binance_data(client, "BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 January 2017")
        fiat_amount = 10000.0
        crypto_amount = 1
    else:
        # Client Binance avec clés API
        API_KEY = os.getenv('BINANCE_API_KEY')
        API_SECRET = os.getenv('BINANCE_API_SECRET')
        client = Client(API_KEY, API_SECRET)
        # Récupérer les données de Binance
        try:
            data = client.get_historical_klines(
                symbol=pair_symbol,
                interval=Client.KLINE_INTERVAL_1HOUR,
                start_str=str(int(time.time()) - 100 * 3600),
                end_str=str(int(time.time()))
            )
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            logging.info("Données Binance récupérées en mode live")
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des données en mode live : {e}")
            return

        # Obtenir les soldes
        fiat_amount = fx.get_balance(client, fiat_symbol)
        crypto_amount = fx.get_balance(client, crypto_symbol)

    if df.empty:
        logging.error("Le DataFrame est vide. Arrêt du script.")
        return

    # Préparer les données avec les indicateurs techniques
    df = prepare_data(df)

    # Analyse des indicateurs techniques sur la dernière ligne
    try:
        res_ema = fx.analyse_ema([
            df['ema7'].iloc[-1],
            df['ema30'].iloc[-1],
            df['ema50'].iloc[-1],
            df['ema100'].iloc[-1],
            df['ema150'].iloc[-1],
            df['ema200'].iloc[-1]
        ])
        res_rsi = fx.analyse_rsi(rsi=df['rsi'].iloc[-1], prev_rsi=df['rsi'].iloc[-3])
        res_stoch_rsi = fx.analyse_stoch_rsi(
            blue=df['stochastic'].iloc[-1],
            orange=df['stoch_signal'].iloc[-1],
            prev_blue=df['stochastic'].iloc[-3],
            prev_orange=df['stoch_signal'].iloc[-3]
        )
        # res_stoch_rsi = fx.analyse_stoch_rsi(
        #     blue=df['stochastic'].iloc[-1],
        #     orange=df['stoch_signal'].iloc[-1],
        #     prev_blue=df['stochastic'].iloc[-3],
        #     prev_orange=df['stoch_signal'].iloc[-3]
        # )
        res_bollinger = fx.analyse_bollinger(
            high=df['bol_high'].iloc[-1],
            low=df['bol_low'].iloc[-1],
            average=df['bol_medium'].iloc[-1],
            close=df['close'].iloc[-1]
        )
        res_macd = fx.analyse_macd(
            macd=df['macd'].iloc[-1],
            signal=df['macd_signal'].iloc[-1],
            histogram=df['macd_histo'].iloc[-1]
        )
        logging.info("Analyse des indicateurs terminée")
    except Exception as e:
        logging.error(f"Erreur lors de l'analyse des indicateurs : {e}")
        return

    # Définir les variables de trading
    actual_price = df['close'].iloc[-1]
    trade_amount = (float(fiat_amount) * risk) / actual_price
    min_token = 5 / actual_price
    position = (float(fiat_amount) * risk) / protection["sl_level"]

    # Afficher les informations pertinentes
    logging.info(f"Prix actuel : {actual_price}, Solde USD : {fiat_amount}, Solde BTC : {crypto_amount}, Position de trading : {position}")
    logging.info(f"EMA : {res_ema}")
    logging.info(f"État RSI : {res_rsi}")
    logging.info(f"État Stoch RSI : {res_stoch_rsi}")
    logging.info(f"Bollinger : {res_bollinger}")

    if backtest:
        # Exécuter le backtest
        logging.info("Début du backtest")
        fx.backtest_strategy(fiat_amount, crypto_amount, df)
    else:
        # Exécuter les actions de trading
        logging.info("Exécution des actions de trading en live")
        fx.trade_action(
            client=client,
            bench_mode=bench_mode,
            pairSymbol=pair_symbol,
            fiatAmount=fiat_amount,
            cryptoAmount=crypto_amount,
            values=df,
            buyReady=buy_ready,
            sellReady=sell_ready,
            minToken=min_token,
            tradeAmount=trade_amount,
            myTruncate=my_truncate,
            protection=protection,
            res_ema=res_ema,
            res_rsi=res_rsi,
            res_stoch_rsi=res_stoch_rsi,
            res_bollinger=res_bollinger,
            res_macd=res_macd
        )

if __name__ == '__main__':
    main()