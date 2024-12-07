import os
import time
import logging
import pandas as pd
import time
import yaml

from binance.client import Client
from datetime import datetime, timedelta

import trading.backtest as bt
import trading.indicators as indic  # Votre module optimisé
import trading.influx_utils as idb
import trading.informations as info  # Votre module optimisé
import trading.trade as trade  # Votre module optimisé

import warnings

# Ignorer tous les FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)

# Définir le chemin vers le fichier de log à la racine du projet
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
logfile = os.path.join(project_root, 'trading_bot.log')

# Configuration de la journalisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(logfile),
        logging.StreamHandler()
    ]
)

# Chemin vers le fichier de configuration à la racine du projet
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')

# print(f"Looking for config.yaml at: {CONFIG_PATH}")

# Charger le fichier de configuration YAML
def load_config(file_path=CONFIG_PATH):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Exemple d'utilisation
config = load_config()

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

# perf_percentage = info.calculate_rendement(capital, cible, temps, dca)
risk = info.define_risk(risk_level)

# Initialiser la variable pour suivre l'état du trade
monthly_trade_in_progress = False
weekly_trade_in_progress = False
daily_trade_in_progress = False
intraday_trade_in_progress = False
scalping_trade_in_progress = False

# Client Binance avec clés API
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

def gather_datas(key, secret, cur_fiat_amount, cur_crypto_amount, interval, start):
    # Your existing trading logic goes here
    # Initialisation des clients API
    if bench_mode:
        client = Client()  # Client sans clés API pour le backtest
        fiat_amount = cur_fiat_amount
        crypto_amount = cur_crypto_amount
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

        # Récupération de l'indice
        bitcoin_fear_and_greed_index = info.get_bitcoin_fear_and_greed_index()
        # print(f"Bitcoin Fear and Greed Index: {bitcoin_fear_and_greed_index}")
        res_adi = indic.analyse_adi(
            data['adi'].iloc[-1],
            data['adi'].iloc[-2]
        )
        res_bollinger = indic.analyse_bollinger(
            high=data['bol_high'].iloc[-1],
            low=data['bol_low'].iloc[-1],
            average=data['bol_medium'].iloc[-1],
            close=data['close'].iloc[-1]
        )
        # res_ema = indic.analyse_ema([
        #     data['ema7'].iloc[-1],
        #     data['ema30'].iloc[-1],
        #     data['ema50'].iloc[-1],
        #     data['ema100'].iloc[-1],
        #     data['ema150'].iloc[-1],
        #     data['ema200'].iloc[-1]
        # ])
        res_ema = indic.analyse_ema([
            data['ema5'].iloc[-1],
            data['ema10'].iloc[-1],
            data['ema20'].iloc[-1],
            data['ema50'].iloc[-1]
        ])
        res_fear_and_greed = indic.analyse_fear_and_greed(
            int(bitcoin_fear_and_greed_index)
        )
        # print(f"Bitcoin Fear and Greed Index: {res_fear_and_greed}")
        res_macd = indic.analyse_macd(
            macd=data['macd'].iloc[-1],
            signal=data['macd_signal'].iloc[-1],
            prev_macd=data['macd'].iloc[-2],
            prev_signal=data['macd_signal'].iloc[-2],
            histogram=data['macd_histo'].iloc[-1]
        )
        res_rsi = indic.analyse_rsi(
            rsi=data['rsi'].iloc[-1],
            prev_rsi=data['rsi'].iloc[-3]
        )
        res_sma = indic.analyse_sma([
            data['sma50'].iloc[-1],
            data['sma200'].iloc[-1]
        ])
        res_stoch_rsi = indic.analyse_stoch_rsi(
            blue=data['stochastic'].iloc[-1],
            orange=data['stoch_signal'].iloc[-1],
            prev_blue=data['stochastic'].iloc[-3],
            prev_orange=data['stoch_signal'].iloc[-3]
        )
        res_support_resistance = indic.analyse_support_resistance(
            price=data['close'].iloc[-1],
            support=data["support"].iloc[-1], 
            resistance=data["resistance"].iloc[-1]
        )
        res_volume = indic.analyse_volume(data)  # Assurez-vous que data['volume'] existe

        # Calculer les niveaux de retracement de Fibonacci
        retracement_levels, extension_levels = indic.calculate_fibonacci_retracement(data)

        google_trend = indic.define_googletrend(crypto_term='Bitcoin')

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
    logging.info(f"ADI : {res_adi}")
    logging.info(f"Bollinger : {res_bollinger}")
    logging.info(f"EMA : {res_ema}")
    logging.info(f"Fear and greed (Bitcoin) : {res_fear_and_greed}")
    logging.info(f"MACD : {res_macd}")
    logging.info(f"RSI : {res_rsi}")
    logging.info(f"SMA : {res_sma}")
    logging.info(f"Stoch RSI : {res_stoch_rsi}")
    logging.info(f"Support et resistance : {res_support_resistance}")
    logging.info(f"Volume : {res_volume}")
    logging.info(f"Retracement Fibonacci : {retracement_levels}")
    logging.info(f"Extensions Fibonacci : {extension_levels}")
    logging.info(f"Google trend : {google_trend}")

    analysis = {
        "pair_symbol": pair_symbol,
        "actual_price": actual_price,
        "trade_amount": trade_amount,
        "min_token": min_token,
        "position": position,
        "fiat_amount": fiat_amount,
        "crypto_amount": crypto_amount,
        "adi": res_adi,
        "bollinger": res_bollinger,
        "ema": res_ema,
        "fear_and_greed": res_fear_and_greed,
        "macd": res_macd,
        "rsi": res_rsi,
        "sma": res_sma,
        "stoch_rsi": res_stoch_rsi,
        "support_resistance": res_support_resistance,
        "volume": res_volume,
        "retracements_fibonacci": retracement_levels,
        "extensions_fibonacci": extension_levels,
        "google_trend": google_trend
    }

    return analysis

def run_trading(client, time_interval, data, analysis, market_trend, score, trade_in_progress):
    if backtest:
        # Exécuter le backtest
        # logging.info(f"#############################################################")
        logging.info("Début du backtest")
        result = bt.backtest_strategy(analysis.fiat_amount, analysis.crypto_amount, data)
        pass
    else:
        # Exécuter les actions de trading
        # logging.info(f"#############################################################")
        logging.info("Exécution des actions de trading en live")
        result = trade.trade_action(
            bench_mode=bench_mode,
            time_interval = time_interval,
            pair_symbol=pair_symbol,
            values=data,
            buy_ready=buy_ready,
            sell_ready=sell_ready,
            my_truncate=my_truncate,
            protection=protection,
            analysis=analysis,
            market_trend=market_trend,
            score=score,
            trade_in_progress=trade_in_progress
        )
        return result

def trading(key, secret, cur_fiat_amount, cur_crypto_amount, time_interval):
    global monthly_trade_in_progress
    global weekly_trade_in_progress
    global daily_trade_in_progress
    global intraday_trade_in_progress
    global scalping_trade_in_progress

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
        case "scalping":
            interval = Client.KLINE_INTERVAL_15MINUTE
            trade_in_progress = scalping_trade_in_progress

    # Log or print the time to track execution
    logging.info(f"#############################################################")
    logging.info("Execution " + time_interval + " at: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ti_client, ti_data, ti_fiat_amount, ti_crypto_amount = gather_datas(key=key, secret=secret, cur_fiat_amount=cur_fiat_amount, cur_crypto_amount=cur_crypto_amount, interval=interval, start="1 Jan, 2020") ### /!\ soldes ecrasées car bench mode
    ti_analysis = run_analysis(data=ti_data, fiat_amount=ti_fiat_amount, crypto_amount=ti_crypto_amount)
    ti_market_trend, ti_score = trade.analyze_market_trend(indicators=ti_analysis)
    logging.info(f"Tendance globale : {ti_market_trend}")
    logging.info(f"Score : {ti_score}")
    if not trade_in_progress:
        result = run_trading(client=ti_client, time_interval = time_interval, data=ti_data, analysis=ti_analysis, market_trend=ti_market_trend, score=ti_score, trade_in_progress=trade_in_progress)

        match time_interval:
            case "monthly":
                monthly_trade_in_progress = result["trade_in_progress"]
            case "weekly":
                weekly_trade_in_progress = result["trade_in_progress"]
            case "daily":
                daily_trade_in_progress = result["trade_in_progress"]
            case "intraday":
                intraday_trade_in_progress = result["trade_in_progress"]
            case "intraday":
                scalping_trade_in_progress = result["trade_in_progress"]
        
        return result

    else:
        logging.info(f"Trade " + time_interval + " deja en cours")
    
    pass

def main():
    logging.info("Trading bot started.")

    monthly_fiat_amount = 10000
    monthly_crypto_amount = 1
    weekly_fiat_amount = 10000
    weekly_crypto_amount = 1
    daily_fiat_amount = 10000
    daily_crypto_amount = 1
    intraday_fiat_amount = 10000
    intraday_crypto_amount = 1
    scalping_fiat_amount = 10000
    scalping_crypto_amount = 1

    while True:
        try:
            monthly_result = trading(key=API_KEY, secret=API_SECRET, cur_fiat_amount=monthly_fiat_amount, cur_crypto_amount=monthly_crypto_amount, time_interval="monthly")
            weekly_result = trading(key=API_KEY, secret=API_SECRET, cur_fiat_amount=weekly_fiat_amount, cur_crypto_amount=weekly_crypto_amount, time_interval="weekly")
            daily_result = trading(key=API_KEY, secret=API_SECRET, cur_fiat_amount=daily_fiat_amount, cur_crypto_amount=daily_crypto_amount, time_interval="daily")
            intraday_result = trading(key=API_KEY, secret=API_SECRET, cur_fiat_amount=intraday_fiat_amount, cur_crypto_amount=intraday_crypto_amount, time_interval="intraday")
            scalping_result = trading(key=API_KEY, secret=API_SECRET, cur_fiat_amount=scalping_fiat_amount, cur_crypto_amount=scalping_crypto_amount, time_interval="scalping")
            monthly_fiat_amount = monthly_result["new_fiat_amount"]
            monthly_crypto_amount = monthly_result["new_crypto_amount"]
            weekly_fiat_amount = weekly_result["new_fiat_amount"]
            weekly_crypto_amount = weekly_result["new_crypto_amount"]
            daily_fiat_amount = daily_result["new_fiat_amount"]
            daily_crypto_amount = daily_result["new_crypto_amount"]
            intraday_fiat_amount = intraday_result["new_fiat_amount"]
            intraday_crypto_amount = intraday_result["new_crypto_amount"]
            scalping_fiat_amount = scalping_result["new_fiat_amount"]
            scalping_crypto_amount = scalping_result["new_crypto_amount"]
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        # Wait for 60 seconds before the next execution
        time.sleep(60)

if __name__ == '__main__':
    main()