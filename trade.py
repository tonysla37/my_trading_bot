import aiohttp
import asyncio
import datetime
import krakenex
import logging
import pandas as pd
import os
from pykrakenapi import KrakenAPI
from scipy.optimize import fsolve
from termcolor import colored

import informations as info
import influx_utils

# Configuration des clés API et des URLs (à sécuriser via des variables d'environnement)
API_KEY = os.getenv('KRAKEN_API_KEY')
API_SECRET = os.getenv('KRAKEN_API_SECRET')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Initialisation de l'API Kraken
api = krakenex.API(key=API_KEY, secret=API_SECRET)
kraken_api = KrakenAPI(api)

async def send_webhook_message(webhook_url, content):
    async with aiohttp.ClientSession() as session:
        data = {
            'content': content
        }
        async with session.post(webhook_url, json=data) as response:
            if response.status == 204:
                logging.info("Message sent successfully!")
            else:
                logging.error(f"Failed to send message: {response.status} - {await response.text()}")

def get_binance_data(client, symbol, interval, start_str):
    """
    Récupère les données historiques de Binance.
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

# Conditions d'achat et de vente
def buy_condition(row, previous_row):
    return (
        row['ema7'] > row['ema30'] > row['ema50'] > row['ema100'] > row['ema150'] > row['ema200']
        and row['stoch_rsi'] < 0.82
    )

def sell_condition(row, previous_row):
    return (
        row['ema200'] > row['ema7']
        and row['stoch_rsi'] > 0.2
    )

def enter_in_trade(res_ema, res_rsi, res_stoch_rsi, res_bollinger, res_macd):
    return (
        res_ema == "bullish"
        and res_rsi["trend"] == "bullish"
        and res_stoch_rsi["trend"] == "bullish"
    )

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
def trade_action(client, bench_mode, pair_symbol, fiat_amount, crypto_amount, values, buy_ready, sell_ready, min_token, trade_amount, my_truncate, protection, res_ema, res_rsi, res_stoch_rsi, res_bollinger, res_macd):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Journalisation des indicateurs
    logging.info(f"Trading Advisor at {now}")
    logging.info(f"Indicators: EMA={res_ema}, RSI={res_rsi['trend']}, StochRSI={res_stoch_rsi['trend']}, Bollinger={res_bollinger['trend']}, MACD={res_macd}")
    
    # # Exécuter la fonction asynchrone
    # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'################## TRADING ADVISOR {now} ##################'))
    # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'ema => {res_ema}'))
    # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'rsi => {res_rsi["trend"]}'))
    # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'stoch_rsi => {res_stoch_rsi["trend"]}'))
    # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'bollinger => {res_bollinger["trend"]}'))
    # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'macd => {res_macd}'))

    # Condition d'achat
    if buy_condition(values.iloc[-2], values.iloc[-3]):
        if float(fiat_amount) > 5 and buy_ready:
            buy_price = values['close'].iloc[-1]
            quantity_buy = info.truncate(trade_amount, my_truncate)
            sl_level = protection["sl_level"]
            tp1_level = protection["tp1_level"]
            sl_amount = protection["sl_amount"]
            tp1_amount = protection["tp1_amount"]

            stop_loss = buy_price - sl_level * buy_price
            take_profit_1 = buy_price + tp1_level * buy_price
            sl_quantity = sl_amount * float(quantity_buy)
            tp1_quantity = tp1_amount * float(quantity_buy)
            possible_gain = (take_profit_1 - buy_price) * float(quantity_buy)
            possible_loss = (buy_price - stop_loss) * float(quantity_buy)
            R = possible_gain / possible_loss if possible_loss != 0 else 0

            if bench_mode:
                buy_order = f"Buy Order placé pour la quantité : {quantity_buy}"
                sell_order_sl = f"SL Order placé à {stop_loss} pour la quantité : {sl_quantity}"
                sell_order_tp1 = f"TP1 Order placé à {take_profit_1} pour la quantité : {tp1_quantity}"
            else:
                buy_order = place_order('buy', pair_symbol, quantity_buy, buy_price)
                sell_order_sl = place_order('sell', pair_symbol, sl_quantity, stop_loss)
                sell_order_tp1 = place_order('sell', pair_symbol, tp1_quantity, take_profit_1)

            buy_ready = False
            sell_ready = True

            logging.info(f"Achat à {buy_price}, Stop loss à {stop_loss}, TP1 à {take_profit_1}")
            logging.info(f"Gain possible : {possible_gain}, Perte possible : {possible_loss}, Ratio R : {R}")
            logging.info(f"Ordres : {buy_order}, {sell_order_sl}, {sell_order_tp1}")
            
            # # Envoyer les messages via webhook
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Achat à {buy_price}"))
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Stop loss à {stop_loss}"))
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"TP1 à {take_profit_1}"))
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Gain possible : {possible_gain}, Perte possible : {possible_loss}, Ratio R : {R}"))
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, buy_order))
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, sell_order_sl))
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, sell_order_tp1))

            # Écrire dans InfluxDB après l'achat
            influx_utils.write_to_influx(
                measurement="live_trades",
                tags={"type": "buy"},
                fields={
                    "price": buy_price,
                    "wallet": fiat_amount,
                    "crypto_amount": crypto_amount
                },
                timestamp=datetime.datetime.now()
            )

    # Condition de vente
    elif sell_condition(values.iloc[-2], values.iloc[-3]):
        if float(crypto_amount) > min_token and sell_ready:
            sell_price = values['close'].iloc[-1]
            quantity_sell = info.truncate(crypto_amount, my_truncate)

            if bench_mode:
                sell_order = f"Sell Order placé pour la quantité : {quantity_sell}"
            else:
                sell_order = place_order('sell', pair_symbol, quantity_sell)
            
            buy_ready = True
            sell_ready = False

            logging.info(f"Vente de {quantity_sell}")
            logging.info(f"Ordre : {sell_order}")
            
            # # Envoyer les messages via webhook
            # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Vente de {quantity_sell}"))
            # if sell_order:
            #     asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, str(sell_order)))
            
            # Écrire dans InfluxDB après la vente
            influx_utils.write_to_influx(
                measurement="live_trades",
                tags={"type": "sell"},
                fields={
                    "price": sell_price,
                    "wallet": fiat_amount,
                    "crypto_amount": crypto_amount
                },
                timestamp=datetime.datetime.now()
            )
    else:
        logging.info("Aucune opportunité de trade")
    #     asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, "Aucune opportunité de trade"))

    # asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, '################## FIN DU TRADING ADVISOR ##################'))