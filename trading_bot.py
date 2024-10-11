import pandas as pd
import pandas_ta as pda
import matplotlib.pyplot as plt
import numpy as np
import ta
import time
import json
from math import *
from termcolor import colored

import os
from binance.client import Client
from binance.enums import *
import krakenex
from pykrakenapi import KrakenAPI

import functions as fx

if __name__ == '__main__':
  accountName = ''
  pairSymbol = 'BTC/USD'
  fiatSymbol = 'USD'
  cryptoSymbol = 'BTC'
  myTruncate = 5
  protection ={}
  protection["sl_level"] = 0.02
  protection["tp1_level"] = 0.1
  protection["sl_amount"] = 1
  protection["tp1_amount"] = 1

  buyReady = True
  sellReady = True
  bench_mode = True
  backtest = True
  # backtest = False
  risk_level = "Mid"

  risk= fx.define_risk(risk_level)

  if bench_mode == True :
    client = Client()
    klinesT = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 january 2017")
    # klinesT = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 january 2022")
    df = pd.DataFrame(klinesT, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
    fiatAmount = 1000
    cryptoAmount = 0.5

  elif bench_mode == False :

    # api = krakenex.API()
    # # Assurez-vous d'avoir vos clés d'API configurées auparavant
    # k = KrakenAPI(api)

    # df = k.get_ohlc_data(pair="XXBTZUSD", interval=60, since=int(time.time())-(86400*30))[0]

    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')

    client = Client(API_KEY, API_SECRET)

    data = client.get_historical_data(
      market_name=pairSymbol,
      resolution=3600,
      limit=1000,
      start_time=float(
      round(time.time()))-100*3600,
      end_time=float(round(time.time())))
    df = pd.DataFrame(data)
    fiatAmount = fx.getBalance(client, fiatSymbol)
    cryptoAmount = fx.getBalance(client, cryptoSymbol)

  # Define timestamp
  df = df.set_index(df['timestamp'])
  df.index = pd.to_datetime(df.index, unit='ms')
  del df['timestamp']

  # Define Price Action
  df['close'] = pd.to_numeric(df['close'])
  df['high'] = pd.to_numeric(df['high'])
  df['low'] = pd.to_numeric(df['low'])
  df['open'] = pd.to_numeric(df['open'])

  ## Momentum (good moment)
  # Relative Strength Index (RSI)
  # beaucoup augmenté ou baissé => pas le bon moment
  # Chercher les divergences
  df['rsi'] = ta.momentum.rsi(close=df['close'], window=14)

  # Stochastic RSI
  # Quand on est en hausse continue, pas le moment d'acheter
  df['stoch_rsi'] = ta.momentum.stochrsi(close=df['close'], window=14)
  df['stochastic'] = ta.momentum.stoch(high=df['high'],low=df['low'],close=df['close'], window=14,smooth_window=3)
  df['stoch_signal'] =ta.momentum.stoch_signal(high =df['high'],low=df['low'],close=df['close'], window=14, smooth_window=3)

  ## Trend (neutal, bull, bear), late
  # MACD : Connaitre la force du marché
  # bleu au dessus orange = bull
  # orange au dessus de bleu = bear
  macd = ta.trend.MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
  df['macd'] = macd.macd()
  df['macd_signal'] = macd.macd_signal()
  df['macd_histo'] = macd.macd_diff() #Histogramme MACD

  # #Awesome Oscillator
  df['awesome_oscilllator'] = ta.momentum.awesome_oscillator(high=df['high'], low=df['low'], window1=5, window2=34)

  # Exponential Moving Average
  df['ema7']=ta.trend.ema_indicator(close=df['close'], window=7)
  df['ema30']=ta.trend.ema_indicator(close=df['close'], window=30)
  df['ema50']=ta.trend.ema_indicator(close=df['close'], window=50)
  df['ema100']=ta.trend.ema_indicator(close=df['close'], window=100)
  df['ema150']=ta.trend.ema_indicator(close=df['close'], window=150)
  df['ema200']=ta.trend.ema_indicator(close=df['close'], window=200)

  # # Simple Moving Average
  # df['sma7']=ta.trend.sma_indicator(close=df['close'], window=7)

  # # Fear and Greed 
  # # Défintion
  # def fear_and_greed(close):
  #     ''' Fear and greed indicator
  #     '''
  #     response = requests.get("https://api.alternative.me/fng/?limit=0&format=json")
  #     dataResponse = response.json()['data']
  #     fear = pd.DataFrame(dataResponse, columns = ['timestamp', 'value'])

  #     fear = fear.set_index(fear['timestamp'])
  #     fear.index = pd.to_datetime(fear.index, unit='s')
  #     del fear['timestamp']
  #     df = pd.DataFrame(close, columns = ['close'])
  #     df['fearResult'] = fear['value']
  #     df['FEAR'] = df['fearResult'].ffill()
  #     df['FEAR'] = df.FEAR.astype(float)
  #     return pd.Series(df['FEAR'], name="FEAR")

  # # Récupération des valeurs
  # df["f_g"] = fear_and_greed(df["close"])


  ## Volatility / Volume
  # # Bollinger Bands
  # # peu de volatilité quand les bandes se resserent
  # # 
  df["bol_high"] = ta.volatility.bollinger_hband(df['close'], window=20, window_dev=2)
  df["bol_low"] = ta.volatility.bollinger_lband(df['close'], window=20, window_dev=2)
  df["bol_medium"] = ta.volatility.bollinger_mavg(df['close'], window=20)
  df["bol_gap"] = ta.volatility.bollinger_wband(df['close'], window=20, window_dev=2)
  # Return binaire 0 ou 1 
  df["bol_higher"] = ta.volatility.bollinger_hband_indicator(df['close'], window=20, window_dev=2)
  df["bol_lower"] = ta.volatility.bollinger_lband_indicator(df['close'], window=20, window_dev=2)

  # # Average True Range (ATR)
  # # très bas quand la volatilité est basse
  # # très haute quand la volatilité est haute
  # # Permet de définir les stop loss ou take profit
  # df["atr"] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=2)

  # # Kaufman’s Adaptive Moving Average (KAMA)
  # df['KAMA1'] = ta.momentum.kama(close=ta.momentum.kama(close=ta.momentum.kama(close=df['close'], window=11, pow1=2, pow2=30), window=11, pow1=2, pow2=30), window=11, pow1=2, pow2=30)
  # df['KAMA2'] = ta.momentum.kama(close=df['close'], window=15, pow1=2, pow2=30)
  # df["kama"] = ta.momentum.kama(df['close'], window=10, pow1=2, pow2=30)

  # Choppiness index
  df['chop'] = fx.get_chop(high=df['high'], low=df['low'], close=df['close'], window=14)

  # ADI Indicator
  df['adi'] = ta.volume.acc_dist_index(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'])

  # # FI
  # df["fi"] = ta.volume.force_index(close=df['close'] ,volume=df['volume'], window=13)

  # #Volume anomaly
  # def volume_anomalu(df, volume_window=10):
  #     dfInd = df.copy()
  #     dfInd["VolAnomaly"] = 0
  #     dfInd["PreviousClose"] = dfInd["close"].shift(1)
  #     dfInd['MeanVolume'] = dfInd['volume'].rolling(volume_window).mean()
  #     dfInd['MaxVolume'] = dfInd['volume'].rolling(volume_window).max()
  #     dfInd.loc[dfInd['volume'] > 1.5 * dfInd['MeanVolume'], "VolAnomaly"] = 1
  #     dfInd.loc[dfInd['volume'] > 2 * dfInd['MeanVolume'], "VolAnomaly"] = 2
  #     dfInd.loc[dfInd['volume'] >= dfInd['MaxVolume'], "VolAnomaly"] = 3
  #     dfInd.loc[dfInd['PreviousClose'] > dfInd['close'],
  #               "VolAnomaly"] = (-1) * dfInd["VolAnomaly"]
  #     return dfInd["VolAnomaly"]

  # df["volume_anomaly"] = volume_anomalu(df, volume_window=10)

  # Define indicators
  res_ema = fx.analyse_ema(ema1=df['ema7'].iloc[-1],ema2=df['ema30'].iloc[-1],ema3=df['ema50'].iloc[-1],ema4=df['ema100'].iloc[-1],ema5=df['ema150'].iloc[-1],ema6=df['ema200'].iloc[-1])
  res_rsi = fx.analyse_rsi(rsi=df['rsi'].iloc[-1],prev_rsi=df['rsi'].iloc[-3])
  res_stoch_rsi = fx.analyse_stoch_rsi(blue=df['stochastic'].iloc[-1],orange=df['stoch_signal'].iloc[-1],prev_blue=df['stochastic'].iloc[-3],prev_orange=df['stoch_signal'].iloc[-3])
  res_bollinger = fx.analyse_bollinger(high=df['bol_high'].iloc[-1],low=df['bol_low'].iloc[-1],average=df['bol_medium'].iloc[-1],close=df['close'].iloc[-1])
  res_macd = fx.analyse_macd(macd=df['macd'].iloc[-1],signal=df['macd_signal'].iloc[-1],histogram=df['macd_histo'].iloc[-1])

  # Define variables from informations
  actualPrice = df['close'].iloc[-1]
  tradeAmount = float(fiatAmount)*risk/actualPrice
  minToken = 5/actualPrice
  position = (float(fiatAmount)*risk) / protection["sl_level"]

  # Print relevant informations
  print(df)
  print('coin price :',actualPrice, 'usd balance', fiatAmount, 'coin balance :',cryptoAmount, 'trading position :',position)

  print('ema :',res_ema)
  print('rsi state :',res_rsi)
  print('stoch rsi state :',res_stoch_rsi)
  print('bollinger :',res_bollinger)

  if backtest == True :
    fx.backtest_strategy(df)
  else :
    # Bot actions execution
    fx.trade_action(client,bench_mode,pairSymbol,fiatAmount,cryptoAmount,df,buyReady,sellReady,minToken,tradeAmount,myTruncate,protection,res_ema,res_rsi,res_stoch_rsi,res_bollinger,res_macd)