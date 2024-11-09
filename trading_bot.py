import os
import time
import logging
import pandas as pd
import yaml

from binance.client import Client
from dotenv import load_dotenv

import backtest as bt
import indicators as indic  # Votre module optimisé
import informations as info  # Votre module optimisé
import trade as trade  # Votre module optimisé


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

# Charger le fichier de configuration YAML
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def main():
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

    logging.info(f"#############################################################")
    logging.info(f"Le capital de départ {capital:.2f}€")
    logging.info(f"Le capital cible {cible:.2f}%")
    logging.info(f"L'horizon de placement {temps:.2f} an(s)")
    logging.info(f"Le montant d'investiment mensuel {dca:.2f}€")
    logging.info(f"#############################################################")
    risk = info.define_risk(risk_level)
    perf_percentage = info.calculate_rendement(capital, cible, temps, dca)
    logging.info(f"#############################################################")

    # Initialisation des clients API
    if bench_mode:
        client = Client()  # Client sans clés API pour le backtest
        df = trade.get_binance_data(client, "BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 January 2017")
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
        fiat_amount = trade.get_balance(client, fiat_symbol)
        crypto_amount = trade.get_balance(client, crypto_symbol)

    if df.empty:
        logging.error("Le DataFrame est vide. Arrêt du script.")
        return

    # Préparer les données avec les indicateurs techniques
    df = info.prepare_data(df)

    # Analyse des indicateurs techniques sur la dernière ligne
    try:
        res_ema = indic.analyse_ema([
            df['ema7'].iloc[-1],
            df['ema30'].iloc[-1],
            df['ema50'].iloc[-1],
            df['ema100'].iloc[-1],
            df['ema150'].iloc[-1],
            df['ema200'].iloc[-1]
        ])
        res_rsi = indic.analyse_rsi(rsi=df['rsi'].iloc[-1], prev_rsi=df['rsi'].iloc[-3])
        res_stoch_rsi = indic.analyse_stoch_rsi(
            blue=df['stochastic'].iloc[-1],
            orange=df['stoch_signal'].iloc[-1],
            prev_blue=df['stochastic'].iloc[-3],
            prev_orange=df['stoch_signal'].iloc[-3]
        )
        # res_stoch_rsi = indic.analyse_stoch_rsi(
        #     blue=df['stochastic'].iloc[-1],
        #     orange=df['stoch_signal'].iloc[-1],
        #     prev_blue=df['stochastic'].iloc[-3],
        #     prev_orange=df['stoch_signal'].iloc[-3]
        # )
        res_bollinger = indic.analyse_bollinger(
            high=df['bol_high'].iloc[-1],
            low=df['bol_low'].iloc[-1],
            average=df['bol_medium'].iloc[-1],
            close=df['close'].iloc[-1]
        )
        res_macd = indic.analyse_macd(
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
    logging.info(f"#############################################################")
    logging.info(f"Prix actuel : {actual_price}, Solde USD : {fiat_amount}, Solde BTC : {crypto_amount}, Position de trading : {position}")
    logging.info(f"EMA : {res_ema}")
    logging.info(f"État RSI : {res_rsi}")
    logging.info(f"État Stoch RSI : {res_stoch_rsi}")
    logging.info(f"Bollinger : {res_bollinger}")

    if backtest:
        # Exécuter le backtest
        logging.info(f"#############################################################")
        logging.info("Début du backtest")
        bt.backtest_strategy(fiat_amount, crypto_amount, df)
    else:
        # Exécuter les actions de trading
        logging.info(f"#############################################################")
        logging.info("Exécution des actions de trading en live")
        trade.trade_action(
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