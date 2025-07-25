# __all__ liste les fonctions que vous souhaitez exposer
__all__ = [
    'send_webhook_message',
    'klines_to_dataframe',
    'get_binance_data',
    'get_kraken_data',
    'buy_condition',
    'sell_condition',
    'analyze_market_trend',
    'place_order',
    'trade_action'
]

import aiohttp
import asyncio
import datetime
import krakenex
import logging
import pandas as pd
import os
import ssl

from datetime import datetime, timedelta
from pykrakenapi import KrakenAPI
from scipy.optimize import fsolve
from termcolor import colored

import trading.informations as info
import trading.influx_utils as idb

# DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/984026868552433674/yw6FcEhCZYPzgFdKJG6aAo7m52xGRIHLs9g0OocEQzYSofCGqCjsagtUMcTh26ewpOJs"

# Initialisation de l'API Kraken
API_KEY = os.getenv('KRAKEN_API_KEY')
API_SECRET = os.getenv('KRAKEN_API_SECRET')
api = krakenex.API(key=API_KEY, secret=API_SECRET)
kraken_api = KrakenAPI(api)

async def send_webhook_message(webhook_url, content):
    # Crée un contexte SSL qui ignore la vérification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        data = {
            'content': content
        }
        async with session.post(webhook_url, json=data, ssl=ssl_context) as response:
            if response.status != 204:
                logging.error(f"Failed to send message: {response.status} - {await response.text()}")

def log_trade_action(msg):
    logging.info(f'<span class="highlight">{msg}</span>')

def klines_to_dataframe(klines):
    return pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
    ])

def get_binance_data(client, symbol, interval, start_str):
    """
    Récupère les données historiques de Binance.
    """
    try:
        klines = client.get_historical_klines(symbol, interval, start_str)
        df = klines_to_dataframe(klines)
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

def buy_condition(analysis, market_trend, score, time_interval):
    return (
        score > 0
        and market_trend == "bullish"
    )

def sell_condition(analysis, market_trend, score, time_interval):
    return (
        score < 0
        and market_trend == "bearish"
    )

def analyze_market_trend(indicators):
    score = 0

    # FEAR AND GREED
    if indicators['fear_and_greed']['trend'] == 'bullish' and indicators['fear_and_greed']['index_value'] < 60 :
        score += 1
    elif indicators['fear_and_greed']['trend'] == 'bearish' and indicators['fear_and_greed']['index_value'] >= 60:
        score -= 1

    # ADI
    if indicators['adi']['trend'] == 'bullish':
        score += 1
    elif indicators['adi']['trend'] == 'bearish':
        score -= 1

    # Bollinger Bands
    # if indicators['bollinger']['trend'] == 'oversell' or indicators['bollinger']['trend'] == 'over_sma':
    if indicators['bollinger']['trend'] == 'oversell':
        score += 1
    # elif indicators['bollinger']['trend'] == 'overbuy' or indicators['bollinger']['trend'] == 'under_sma':
    elif indicators['bollinger']['trend'] == 'overbuy':
        score -= 1

    # EMA
    if indicators['ema']['trend'] == 'bullish':
        score += 1
    elif indicators['ema']['trend'] == 'bearish':
        score -= 1

    # MACD
    if indicators['macd']['trend'] == 'bullish':
        score += 1
    elif indicators['macd']['trend'] == 'bearish':
        score -= 1

    # RSI
    if indicators['rsi']['trend'] == 'overbuy':
        score -= 1
    elif indicators['rsi']['trend'] == 'oversell':
        score += 1
        
    # SMA
    if indicators['sma']['trend'] == 'bullish':
        score += 1
    elif indicators['sma']['trend'] == 'bearish':
        score -= 1

    # Stoch RSI
    if indicators['stoch_rsi']['trend'] == 'overbuy':
        score -= 1
    elif indicators['stoch_rsi']['trend'] == 'oversell':
        score += 1

    # Volume
    if indicators['volume']['trend'] == 'bullish':
        score += 1
    elif indicators['volume']['trend'] == 'bearish':
        score -= 1

    # Évaluation de la tendance globale
    if score > 0:
        trend = "bullish"
    elif score < 0:
        trend = "bearish"
    else:
        trend = "neutral"
    
    return trend, score

# Fonctions pour placer les ordres
def place_order(order_type, pair, volume, price=None):
    try:
        if order_type == 'buy':
            order = api.query_private('AddOrder', {
                'pair': pair,
                'type': 'buy',
                'ordertype': 'limit' if price else 'market',
                'price': price if price else '',
                'volume': volume
            })
        elif order_type == 'sell':
            order = api.query_private('AddOrder', {
                'pair': pair,
                'type': 'sell',
                'ordertype': 'limit' if price else 'market',
                'price': price if price else '',
                'volume': volume
            })
        logging.info(f"Ordre {order_type} placé : {order}")
        return order
    except Exception as e:
        logging.error(f"Erreur lors de la placement de l'ordre {order_type} : {e}")
        return None

# Fonction principale de trading
def trade_action(bench_mode, time_interval, pair_symbol, values, buy_ready, sell_ready, my_truncate, protection, analysis, trade_in_progress):
    # Assurez-vous que 'analysis' est un dictionnaire et non une chaîne de caractères
    if not isinstance(analysis, dict):
        logging.error(f"Expected 'analysis' to be a dictionary, but got {type(analysis)}")
        return

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    market_trend, score = analyze_market_trend(analysis)
    logging.info(f"Market trend: {market_trend}, Score: {score}")
    
    # Journalisation des indicateurs
    logging.info(f"Run trading Advisor at {now}")

    price = values['close'].iloc[-1]
    quantity = info.truncate(analysis['trade_amount'], my_truncate)

    # Condition d'achat
    if buy_condition(analysis, market_trend, score, time_interval) and not trade_in_progress:
        if float(analysis['fiat_amount']) > 5 and buy_ready:

            sl_level = protection["sl_level"]
            tp1_level = protection["tp1_level"]
            sl_amount = protection["sl_amount"]
            tp1_amount = protection["tp1_amount"]

            stop_loss = price - sl_level * price
            take_profit_1 = price + tp1_level * price
            sl_quantity = sl_amount * float(quantity)
            tp1_quantity = tp1_amount * float(quantity)
            possible_gain = (take_profit_1 - price) * float(quantity)
            possible_loss = (price - stop_loss) * float(quantity)
            R = possible_gain / possible_loss if possible_loss != 0 else 0

            if bench_mode:
                buy_order = f"Buy Order placé pour la quantité : {quantity}"
                sell_order_sl = f"SL Order placé à {stop_loss} pour la quantité : {sl_quantity}"
                sell_order_tp1 = f"TP1 Order placé à {take_profit_1} pour la quantité : {tp1_quantity}"
            else:
                buy_order = place_order('buy', pair_symbol, quantity, price)
                sell_order_sl = place_order('sell', pair_symbol, sl_quantity, stop_loss)
                sell_order_tp1 = place_order('sell', pair_symbol, tp1_quantity, take_profit_1)

            buy_ready = False
            sell_ready = True

            # Mise à jour des balances
            fiat_after_trade = float(analysis['fiat_amount']) - (float(quantity) * price)  # Moins le montant dépensé en fiat
            crypto_after_trade = float(analysis['crypto_amount']) + float(quantity)  # Ajoute la quantité achetée
            analysis['fiat_amount'] = fiat_after_trade
            analysis['crypto_amount'] = crypto_after_trade
            total_portfolio_value = fiat_after_trade + (crypto_after_trade * price)

            log_trade_action(f"Gain possible : {possible_gain}, Perte possible : {possible_loss}, Ratio R : {R}")
            log_trade_action(f"Ordres : {buy_order}, {sell_order_sl}, {sell_order_tp1}")
            log_trade_action(f"Nouveau solde fiat: {fiat_after_trade}, Nouveau solde crypto: {crypto_after_trade}")
            try:
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'################## TRADING ADVISOR {now} ##################'))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Interval de temps : {time_interval}"))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Gain possible : {possible_gain}, Perte possible : {possible_loss}, Ratio R : {R}"))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Ordres : {buy_order}, {sell_order_sl}, {sell_order_tp1}"))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Nouveau solde fiat: {fiat_after_trade}, Nouveau solde crypto: {crypto_after_trade}"))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, '################## FIN DU TRADING ADVISOR ##################'))
            except Exception as e:
                logging.error(f"Erreur lors de l'envoi des messages discord")
            
            # Écrire dans InfluxDB après l'achat
            fields = {
                "fiat_amount": float(analysis['fiat_amount']),
                "crypto_amount": float(analysis['crypto_amount']),
                "new_fiat_amount": float(fiat_after_trade),
                "new_crypto_amount": float(crypto_after_trade),
                "total_portfolio_value": float(total_portfolio_value),
                "price": float(price),
                "pair_symbol": pair_symbol,
                "quantity": float(quantity),
                "sl": float(stop_loss),
                "sl_quantity": float(sl_quantity),
                "tp1": float(take_profit_1),
                "tp1_quantity": float(tp1_quantity),
                "possible_gain": float(possible_gain),
                "possible_loss": float(possible_loss),
                "R": float(R),
                "trade_in_progress": True
            }
            idb.write_trade_to_influx(fields=fields, trade_type="buy", timestamp=int(datetime.now().timestamp() * 1e9))


    # Condition de vente
    elif sell_condition(analysis, market_trend, score, time_interval) and trade_in_progress:
        if float(analysis['crypto_amount']) > analysis['min_token'] and sell_ready:
            if bench_mode:
                sell_order = f"Sell Order placé pour la quantité : {quantity}"
            else:
                sell_order = place_order('sell', pair_symbol, quantity)
            
            buy_ready = True
            sell_ready = False

            # Mise à jour des balances
            fiat_after_trade = float(analysis['fiat_amount']) + (float(quantity) * price)  # Ajoute le montant reçu en fiat
            crypto_after_trade = float(analysis['crypto_amount']) - float(quantity)  # Réduit la quantité de crypto vendue
            analysis['fiat_amount'] = fiat_after_trade
            analysis['crypto_amount'] = crypto_after_trade
            total_portfolio_value = fiat_after_trade + (crypto_after_trade * price)

            logging.info(f"Vente de {quantity}")
            logging.info(f"Ordre : {sell_order}")
            logging.info(f"Nouveau solde fiat: {fiat_after_trade}, Nouveau solde crypto: {crypto_after_trade}")
            try:
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'################## TRADING ADVISOR {now} ##################'))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Interval de temps : {time_interval}"))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Vente de {quantity}"))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, str(sell_order)))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Nouveau solde fiat: {fiat_after_trade}, Nouveau solde crypto: {crypto_after_trade}"))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, '################## FIN DU TRADING ADVISOR ##################'))
            except Exception as e:
                logging.error(f"Erreur lors de l'envoi des messages discord")            

            # Écrire dans InfluxDB après la vente
            fields = {
                "fiat_amount": float(analysis['fiat_amount']),
                "crypto_amount": float(analysis['crypto_amount']),
                "new_fiat_amount": float(fiat_after_trade),
                "new_crypto_amount": float(crypto_after_trade),
                "total_portfolio_value": float(total_portfolio_value),
                "price": float(price),
                "pair_symbol": pair_symbol,
                "quantity": float(quantity),
                "trade_in_progress": False
            }
            idb.write_trade_to_influx(fields=fields, trade_type="sell", timestamp=int(datetime.now().timestamp() * 1e9))

    else:
        total_portfolio_value = analysis['fiat_amount'] + (analysis['crypto_amount'] * price)
        logging.info("Aucune opportunité de trade")

        # Écrire dans InfluxDB
        fields = {
            "fiat_amount": float(analysis['fiat_amount']),
            "crypto_amount": float(analysis['crypto_amount']),
            "new_fiat_amount": float(analysis['fiat_amount']),
            "new_crypto_amount": float(analysis['crypto_amount']),
            "total_portfolio_value": float(total_portfolio_value),
            "price": float(price),
            "pair_symbol": pair_symbol,
            "quantity": float(quantity),
            "trade_in_progress": False
        }

    return fields