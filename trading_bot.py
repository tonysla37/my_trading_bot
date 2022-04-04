import ftx
import pandas as pd
import pandas_ta as pda
import matplotlib.pyplot as plt
import numpy as np
import ta
import time
import json
from math import *
from binance.client import Client
from termcolor import colored

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
  protection["tp2_level"] = 0.12
  protection["tp3_level"] = 0.15
  protection["sl_amount"] = 1
  protection["tp1_amount"] = 0.5
  protection["tp2_amount"] = 0.3
  protection["tp3_amount"] = 0.2

  buyReady = True
  sellReady = True
  bench_mode = True
  risk_level = "Mid"

  risk= fx.define_risk(risk_level)

  if bench_mode == True :
    client = Client()
    klinesT = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 january 2021")
    df = pd.DataFrame(klinesT, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
    fiatAmount = 1000
    cryptoAmount = 0.5

  elif bench_mode == False :
    client = ftx.FtxClient(api_key='', api_secret='', subaccount_name=accountName)
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

  ## Indicators
  # Define Price Action
  df['close'] = pd.to_numeric(df['close'])
  df['high'] = pd.to_numeric(df['high'])
  df['low'] = pd.to_numeric(df['low'])
  df['open'] = pd.to_numeric(df['open'])
  # Exponential Moving Average
  df['EMA1']=ta.trend.ema_indicator(close=df['close'], window=13)
  df['EMA2']=ta.trend.ema_indicator(close=df['close'], window=38)
  # Relative Strength Index (RSI)
  df['RSI'] =ta.momentum.rsi(close=df['close'], window=14)
  # MACD
  MACD = ta.trend.MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
  df['MACD'] = MACD.macd()
  df['MACD_SIGNAL'] = MACD.macd_signal()
  df['MACD_DIFF'] = MACD.macd_diff() # Histogramme MACD
  # Stochastic RSI
  df['STOCH_RSI'] = ta.momentum.stochrsi(close=df['close'], window=14, smooth1=3, smooth2=3) # Non moyenné 
  df['STOCH_RSI_D'] = ta.momentum.stochrsi_d(close=df['close'], window=14, smooth1=3, smooth2=3) # Orange sur TradingView
  df['STOCH_RSI_K'] =ta.momentum.stochrsi_k(close=df['close'], window=14, smooth1=3, smooth2=3) # Bleu sur TradingView
  # Choppiness index
  df['CHOP'] = fx.get_chop(high=df['high'], low=df['low'], close=df['close'], window=14)

  res_ema = fx.analyse_ema(ema1=df['EMA1'].iloc[-1],ema2=df['EMA2'].iloc[-1])
  res_rsi = fx.analyse_rsi(rsi=df['RSI'].iloc[-1])
  res_stoch_rsi = fx.analyse_stoch_rsi(blue=df['STOCH_RSI_K'].iloc[-1],orange=df['STOCH_RSI_D'].iloc[-1])

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

  # Bot actions execution
  fx.trade_action(client,bench_mode,pairSymbol,fiatAmount,cryptoAmount,df,buyReady,sellReady,minToken,tradeAmount,myTruncate,protection,res_ema,res_rsi,res_stoch_rsi)

  if bench_mode == True :
    fx.backtest_strategy(df)
