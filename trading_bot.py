import os
import time
import logging
import pandas as pd
import time
import yaml

from binance.client import Client
from datetime import datetime, timedelta

import backtest as bt
import indicators as indic  # Votre module optimisé
import influx_utils as idb
import informations as info  # Votre module optimisé
import trade as trade  # Votre module optimisé

import warnings

# Ignorer tous les FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)

# Configuration de la journalisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)

# Charger le fichier de configuration YAML
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Charger la configuration
config = load_config('config.yaml')

# Extraire les paramètres de configuration
trading_config = config['trading']
pair_symbol = trading_config['pair_symbol']
fiat_symbol = trading_config['fiat_symbol']
crypto_symbol = trading_config['crypto_symbol']
my_truncate = trading_config['my_truncate']
protection = trading_config['protection']
buy_ready = trading_config['buy_ready']
sell_ready = trading_config['sell_ready']
bench_mode = trading_config['bench_mode']
backtest = trading_config['backtest']
risk_level = trading_config['risk_level']
capital = trading_config['capital']
cible = trading_config['cible']
temps = trading_config['temps']
dca = trading_config['dca']

# Obtenir la date d'aujourd'hui et Formater la date au format 'YYYY-MM-DD'
today = datetime.now()
today_format = today.strftime('%Y-%m-%d')

perf_percentage = info.calculate_rendement(capital, cible, temps, dca)
risk = info.define_risk(risk_level)

# Initialiser la variable pour suivre l'état du trade
monthly_trade_in_progress = False
weekly_trade_in_progress = False
daily_trade_in_progress = False
intraday_trade_in_progress = False

# Client Binance avec clés API
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

def gather_datas(key, secret, interval, start):
    # Your existing trading logic goes here
    # Initialisation des clients API
    if bench_mode:
        client = Client()  # Client sans clés API pour le backtest
        fiat_amount = 10000.0
        crypto_amount = 1
    else:
        client = Client(key, secret)
        fiat_amount = trade.get_balance(client, fiat_symbol)
        crypto_amount = trade.get_balance(client, crypto_symbol)

    data = trade.get_binance_data(client, pair_symbol, interval, start)

    if data.empty:
        logging.error("Le DataFrame est vide. Arrêt du script.")
        return

    # Préparer les données avec les indicateurs techniques
    data = info.prepare_data(data)
    return client, data, fiat_amount, crypto_amount

def run_analysis(data, fiat_amount, crypto_amount):
    # Analyse des indicateurs techniques sur la dernière ligne
    try:
        res_ema = indic.analyse_ema([
            data['ema7'].iloc[-1],
            data['ema30'].iloc[-1],
            data['ema50'].iloc[-1],
            data['ema100'].iloc[-1],
            data['ema150'].iloc[-1],
            data['ema200'].iloc[-1]
        ])
        res_rsi = indic.analyse_rsi(rsi=data['rsi'].iloc[-1], prev_rsi=data['rsi'].iloc[-3])
        res_stoch_rsi = indic.analyse_stoch_rsi(
            blue=data['stochastic'].iloc[-1],
            orange=data['stoch_signal'].iloc[-1],
            prev_blue=data['stochastic'].iloc[-3],
            prev_orange=data['stoch_signal'].iloc[-3]
        )
        res_bollinger = indic.analyse_bollinger(
            high=data['bol_high'].iloc[-1],
            low=data['bol_low'].iloc[-1],
            average=data['bol_medium'].iloc[-1],
            close=data['close'].iloc[-1]
        )
        res_macd = indic.analyse_macd(
            macd=data['macd'].iloc[-1],
            signal=data['macd_signal'].iloc[-1],
            prev_macd=data['macd'].iloc[-2],
            prev_signal=data['macd_signal'].iloc[-2],
            histogram=data['macd_histo'].iloc[-1]
        )
        res_volume = indic.analyse_volume(data)  # Assurez-vous que data['volume'] existe

        logging.info("Analyse des indicateurs terminée")
    except Exception as e:
        logging.error(f"Erreur lors de l'analyse des indicateurs : {e}")
        return

    # Définir les variables de trading
    actual_price = data['close'].iloc[-1]
    trade_amount = (float(fiat_amount) * risk) / actual_price
    min_token = 5 / actual_price
    position = (float(fiat_amount) * risk) / protection["sl_level"]

    # Afficher les informations pertinentes
    # logging.info(f"#############################################################")
    logging.info(f"Prix actuel : {actual_price}, Solde USD : {fiat_amount}, Solde BTC : {crypto_amount}, Position de trading : {position}")
    logging.info(f"EMA : {res_ema}")
    logging.info(f"État RSI : {res_rsi}")
    logging.info(f"État Stoch RSI : {res_stoch_rsi}")
    logging.info(f"MACD : {res_macd}")
    logging.info(f"Bollinger : {res_bollinger}")
    logging.info(f"Volume : {res_volume}")

    analysis = {
        "actual_price": actual_price,
        "trade_amount": trade_amount,
        "min_token": min_token,
        "position": position,
        "fiat_amount": fiat_amount,
        "crypto_amount": crypto_amount,
        "ema": res_ema,
        "rsi": res_rsi,
        "stoch_rsi": res_stoch_rsi,
        "macd": res_macd,
        "bollinger": res_bollinger,
        "volume": res_volume,
    }

    return analysis

def run_trading(client, time_interval, data, analysis, trade_in_progress):
    if backtest:
        # Exécuter le backtest
        # logging.info(f"#############################################################")
        logging.info("Début du backtest")
        bt.backtest_strategy(analysis.fiat_amount, analysis.crypto_amount, data)
        pass
    else:
        # Exécuter les actions de trading
        # logging.info(f"#############################################################")
        logging.info("Exécution des actions de trading en live")
        trade_in_progress = trade.trade_action(
            bench_mode=bench_mode,
            time_interval = time_interval,
            pair_symbol=pair_symbol,
            values=data,
            buy_ready=buy_ready,
            sell_ready=sell_ready,
            my_truncate=my_truncate,
            protection=protection,
            analysis=analysis,
            trade_in_progress=trade_in_progress
        )
        return trade_in_progress

def trading(key, secret, time_interval):
    global monthly_trade_in_progress
    global weekly_trade_in_progress
    global daily_trade_in_progress
    global intraday_trade_in_progress

    match time_interval:
        case "monthly":
            interval = Client.KLINE_INTERVAL_1MONTH
            trade_in_progress = monthly_trade_in_progress
        case "weekly":
            interval = Client.KLINE_INTERVAL_1WEEK
            trade_in_progress = weekly_trade_in_progress
        case "daily":
            interval = Client.KLINE_INTERVAL_1DAY
            trade_in_progress = daily_trade_in_progress
        case "intraday":
            interval = Client.KLINE_INTERVAL_1HOUR
            trade_in_progress = intraday_trade_in_progress

    # Log or print the time to track execution
    logging.info(f"#############################################################")
    logging.info("Execution " + time_interval + " at: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ti_client, ti_data, ti_fiat_amount, ti_crypto_amount = gather_datas(key=key, secret=secret, interval=interval, start="1 Jan, 2020")
    ti_analysis = run_analysis(data=ti_data, fiat_amount=ti_fiat_amount, crypto_amount=ti_crypto_amount)
    if not trade_in_progress:
        trade_in_progress = run_trading(client=ti_client, time_interval = time_interval, data=ti_data, analysis=ti_analysis, trade_in_progress=trade_in_progress)
    else:
        logging.info(f"Trade " + time_interval + " deja en cours")
    
    pass

def main():

    while True:
        try:
            monthly_result = trading(key=API_KEY, secret=API_SECRET, time_interval="monthly")
            weekly_result = trading(key=API_KEY, secret=API_SECRET, time_interval="weekly")
            daily_result = trading(key=API_KEY, secret=API_SECRET, time_interval="daily")
            intraday_result = trading(key=API_KEY, secret=API_SECRET, time_interval="intraday")
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        # Wait for 60 seconds before the next execution
        time.sleep(60)

if __name__ == '__main__':
    main()