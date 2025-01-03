import logging
import pandas as pd
import numpy as np
import ta
import yaml
import os

import trading.indicators as indic
import trading.trade as trade
import trading.influx_utils as idb

from datetime import datetime, timedelta

# Charger les configurations à partir du fichier config.yaml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def backtest_strategy(fiat_amount, crypto_amount, data, config, time_interval):
    trade_in_progress = False
    buy_ready = True
    sell_ready = False
    bench_mode = True
    protection = config['trading']['protection']
    my_truncate = config['trading']['my_truncate']
    pair_symbol = config['trading']['pair_symbol']
    analysis = {
        "fiat_amount": fiat_amount,
        "crypto_amount": crypto_amount
    }

    for i in range(1, len(data)):
        # Préparer les données pour cette itération
        current_data = data.iloc[:i+1]

        # Calculer les indicateurs techniques
        indicators = {
            "adi": indic.analyse_adi(current_data['adi'].iloc[-1], current_data['adi'].iloc[-2]),
            "bollinger": indic.analyse_bollinger(current_data['high'].iloc[-1], current_data['low'].iloc[-1], current_data['close'].rolling(window=20).mean().iloc[-1], current_data['close'].iloc[-1]),
            "ema": indic.analyse_ema([current_data['ema7'].iloc[-1], current_data['ema30'].iloc[-1], current_data['ema50'].iloc[-1], current_data['ema100'].iloc[-1]]),
            "fear_and_greed": indic.analyse_fear_and_greed(current_data['fear_and_greed'].iloc[-1]),
            "macd": indic.analyse_macd(current_data['macd'].iloc[-1], current_data['signal'].iloc[-1], current_data['histogram'].iloc[-1], current_data['macd'].iloc[-2], current_data['signal'].iloc[-2]),
            "rsi": indic.analyse_rsi(current_data['rsi'].iloc[-1], current_data['rsi'].iloc[-2]),
            "stoch_rsi": indic.analyse_stoch_rsi(current_data['stochastic'].iloc[-1], current_data['stoch_signal'].iloc[-1], current_data['stochastic'].iloc[-2], current_data['stoch_signal'].iloc[-2]),
            "volume": indic.analyse_volume(current_data)
        }

        # Analyser la tendance du marché
        market_trend, score = trade.analyze_market_trend(indicators)

        # Exécuter les actions de trading
        trade_in_progress = trade.trade_action(
            bench_mode=bench_mode,
            time_interval=time_interval,
            pair_symbol=pair_symbol,
            values=current_data,
            buy_ready=buy_ready,
            sell_ready=sell_ready,
            my_truncate=my_truncate,
            protection=protection,
            analysis=analysis,
            market_trend=market_trend,
            score=score,
            trade_in_progress=trade_in_progress
        )

    return analysis

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
    data['ema7'] = data['close'].ewm(span=7, adjust=False).mean()
    data['ema30'] = data['close'].ewm(span=30, adjust=False).mean()
    data['ema50'] = data['close'].ewm(span=50, adjust=False).mean()
    data['ema100'] = data['close'].ewm(span=100, adjust=False).mean()

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

    # Exécution du backtest
    backtest_result = backtest_strategy(fiat_amount=10000, crypto_amount=0, data=data, config=config, time_interval='1d')
    print(backtest_result)