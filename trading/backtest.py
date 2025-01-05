import logging
import pandas as pd
import numpy as np
import ta
import yaml
import os

import trading.indicators as indic
import trading.trade as trade
import trading.influx_utils as idb
import trading.informations as info  # Votre module optimisé
import trading.trading_bot as tb

from datetime import datetime, timedelta

# Charger les configurations à partir du fichier config.yaml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def check_and_initialize_keys(data, keys):
    for key in keys:
        if key not in data.columns:
            # logging.warning(f"Missing key in data: {key}")
            data[key] = None
    return data

def backtest_strategy(fiat_amount, crypto_amount, data, config, time_interval, risk):
    # Vérifiez et initialisez les clés manquantes
    required_keys = [
        'prev_adi', 'average', 'emas', 'index_value', 'signal', 'histogram',
        'prev_macd', 'prev_signal', 'prev_rsi', 'smas', 'blue', 'orange',
        'prev_blue', 'prev_orange', 'price', 'crypto_term'
    ]
    data = check_and_initialize_keys(data, required_keys)
    
    trade_in_progress = False
    buy_ready = config['trading']['buy_ready']
    sell_ready = config['trading']['sell_ready']
    bench_mode = True
    protection = config['trading']['protection']
    my_truncate = config['trading']['my_truncate']
    pair_symbol = config['trading']['pair_symbol']

    for i in range(1, len(data)):
        # Préparer les données pour cette itération
        current_data = data.iloc[:i+1]
                # Récupérer le timestamp de current_data
        current_timestamp = current_data.index[-1]
        logging.info(f"Current timestamp: {current_timestamp}")

        if i != 1 and result is not None:
            fiat_amount = result['fiat_amount']
            crypto_amount = result['crypto_amount']
        else:
            fiat_amount = fiat_amount
            crypto_amount = crypto_amount
        
        logging.info(f"Fiat amount: {fiat_amount}")
        logging.info(f"Crypto amount: {crypto_amount}")
    
        # Calculer les indicateurs techniques et analyser la tendance du marché
        analysis = tb.run_analysis(current_data, fiat_amount=fiat_amount, crypto_amount=crypto_amount, risk=risk, protection=protection)
        # logging.info(f"Analysis: {analysis}")
        
        # Exécuter les actions de trading
        result = trade.trade_action(
            bench_mode=bench_mode,
            time_interval=time_interval,
            pair_symbol=pair_symbol,
            values=current_data,
            buy_ready=buy_ready,
            sell_ready=sell_ready,
            my_truncate=my_truncate,
            protection=protection,
            analysis=analysis,
            trade_in_progress=trade_in_progress
        )

    return result

if __name__ == "__main__":
    # Charger les configurations
    config = load_config()

    # Exemple fictif de DataFrame
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'close': np.random.random(100) * 100,
        'high': np.random.random(100) * 100,
        'low': np.random.random(100) * 100,
        'volume': np.random.random(100) * 100
    }, index=dates)

    # Calcul des EMA
    data['ema5'] = data['close'].ewm(span=5, adjust=False).mean()
    data['ema10'] = data['close'].ewm(span=10, adjust=False).mean()
    data['ema20'] = data['close'].ewm(span=20, adjust=False).mean()
    data['ema50'] = data['close'].ewm(span=50, adjust=False).mean()

    # Calcul des autres indicateurs nécessaires
    data['rsi'] = ta.momentum.rsi(data['close'], window=14)
    data['stochastic'] = ta.momentum.stoch(data['high'], data['low'], data['close'], window=14)
    data['stoch_signal'] = ta.momentum.stoch_signal(data['high'], data['low'], data['close'], window=14)
    data['adi'] = ta.volume.acc_dist_index(data['high'], data['low'], data['close'], data['volume'])
    data['macd'] = ta.trend.macd(data['close'])
    data['signal'] = ta.trend.macd_signal(data['close'])
    data['histogram'] = ta.trend.macd_diff(data['close'])
    data['fear_and_greed'] = np.random.random(100) * 100  # Exemple fictif

    # Calcul des indicateurs supplémentaires si nécessaire
    data['chop'] = indic.get_chop(data['high'], data['low'], data['close'])

    # Vérifier que toutes les colonnes nécessaires sont présentes
    required_columns = ['adi', 'high', 'low', 'close', 'ema5', 'ema10', 'ema20', 'ema50', 'fear_and_greed', 'macd', 'signal', 'histogram', 'rsi', 'stochastic', 'stoch_signal']
    for col in required_columns:
        if col not in data.columns:
            logging.error(f"Missing column: {col}")
            exit(1)

    # Exécution du backtest
    backtest_result = backtest_strategy(fiat_amount=10000, crypto_amount=0, data=data, config=config, time_interval='1d', risk=0.02, market_trend='bull', score=0.5)
    print(backtest_result)