import logging
import pandas as pd
import numpy as np
import ta
import yaml
import os

import trading.indicators as indic
import trading.trade as trade
import trading.influx_utils as idb
import trading.trading_bot as tb

from datetime import datetime, timedelta

# Charger les configurations à partir du fichier config.yaml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def backtest_strategy(fiat_amount, crypto_amount, data, config, time_interval, risk, market_trend, score):
    trade_in_progress = False
    buy_ready = config['trading']['buy_ready']
    sell_ready = config['trading']['sell_ready']
    bench_mode = True
    protection = config['trading']['protection']
    my_truncate = config['trading']['my_truncate']
    pair_symbol = config['trading']['pair_symbol']

    # Calculer les indicateurs techniques et analyser la tendance du marché
    analysis = tb.run_analysis(data=data, fiat_amount=fiat_amount, crypto_amount=crypto_amount, risk=risk, protection=protection)
    # Exécuter les actions de trading
    result = trade.trade_action(
        bench_mode=bench_mode,
        time_interval=time_interval,
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