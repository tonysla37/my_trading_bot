import os
import time
import logging

import pandas as pd

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
    risk_level = "Max"  # Low, Mid, Max

    capital = 100
    cible = 200000
    temps = 5
    dca = 100

    perf_percentage = info.calculate_rendement(capital, cible, temps, dca)
    risk = info.define_risk(risk_level)

    logging.info(f"#############################################################")
    logging.info(f"Le capital de départ {capital:.2f}€")
    logging.info(f"Le capital cible {cible:.2f}%")
    logging.info(f"L'horizon de placement {temps:.2f} an(s)")
    logging.info(f"Le montant d'investiment mensuel {dca:.2f}€")
    logging.info(f"Niveau de risque défini : {risk_level} ({risk})")
    logging.info(f"#############################################################")
    logging.info(f"Le taux de croissance annuel composé nécessaire sans dca est d'environ {perf_percentage['year_percentage']:.2f}%")
    logging.info(f"Le taux de croissance mensuelle composé nécessaire sans dca est d'environ {perf_percentage['monthly_percentage']:.2f}%")
    logging.info(f"Le taux de croissance journalier nécessaire sans dca est d'environ {perf_percentage['daily_percentage']:.6f}%")
    logging.info(f"La valeur future de l'investissement avec des contributions mensuelles est d'environ {perf_percentage['dca_value']:.2f}€")
    logging.info(f"Le taux de croissance annuel composé nécessaire avec dca est d'environ {perf_percentage['year_percentage_dca']:.2f}%")
    logging.info(f"Le taux de croissance mensuelle composé nécessaire avec dca est d'environ {perf_percentage['monthly_percentage_dca']:.2f}%")
    logging.info(f"Le taux de croissance journalier nécessaire avec dca est d'environ {perf_percentage['daily_percentage_dca']:.6f}%")
    logging.info(f"Le taux de croissance mensuel nécessaire pour atteindre {cible} € est d'environ {perf_percentage['ca_percentage']:.6f} % par mois.")
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