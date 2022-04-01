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
  risk = 0.03
  buyReady = True
  sellReady = True

  #client = ftx.FtxClient(api_key='', api_secret='', subaccount_name=accountName)
  client = Client()

  #data = client.get_historical_data(
  #    market_name=pairSymbol,
  #    resolution=3600,
  #    limit=1000,
  #    start_time=float(
  #    round(time.time()))-100*3600,
  #    end_time=float(round(time.time())))
  #df = pd.DataFrame(data)

  klinesT = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 january 2021")

  df = pd.DataFrame(klinesT, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
  df['close'] = pd.to_numeric(df['close'])
  df['high'] = pd.to_numeric(df['high'])
  df['low'] = pd.to_numeric(df['low'])
  df['open'] = pd.to_numeric(df['open'])

  df = df.set_index(df['timestamp'])
  df.index = pd.to_datetime(df.index, unit='ms')
  del df['timestamp']

  # Exponential Moving Average
  df['EMA1']=ta.trend.ema_indicator(close=df['close'], window=13)
  df['EMA2']=ta.trend.ema_indicator(close=df['close'], window=38)
  # Relative Strength Index (RSI)
  df['RSI'] =ta.momentum.rsi(close=df['close'], window=14)
  # MACD
  MACD = ta.trend.MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
  df['MACD'] = MACD.macd()
  df['MACD_SIGNAL'] = MACD.macd_signal()
  df['MACD_DIFF'] = MACD.macd_diff() #Histogramme MACD
  # Stochastic RSI
  df['STOCH_RSI'] = ta.momentum.stochrsi(close=df['close'], window=14, smooth1=3, smooth2=3) #Non moyenné 
  df['STOCH_RSI_D'] = ta.momentum.stochrsi_d(close=df['close'], window=14, smooth1=3, smooth2=3) #Orange sur TradingView
  df['STOCH_RSI_K'] =ta.momentum.stochrsi_k(close=df['close'], window=14, smooth1=3, smooth2=3) #Bleu sur TradingView
  # Choppiness index
  df['CHOP'] = fx.get_chop(high=df['high'], low=df['low'], close=df['close'], window=14)  

  print(df)

  actualPrice = df['close'].iloc[-1]
  # fiatAmount = fx.getBalance(client, fiatSymbol)
  # cryptoAmount = fx.getBalance(client, cryptoSymbol)
  fiatAmount = 1000
  cryptoAmount = 0.5
  tradeAmount = float(fiatAmount)*risk/actualPrice
  print('coin price :',actualPrice, 'usd balance', fiatAmount, 'coin balance :',cryptoAmount)

  minToken = 5/actualPrice

  quantity_to_trade = fx.define_quantity_to_trade(tradeAmount,myTruncate)
  fx.trade_action(fiatAmount,cryptoAmount,df,buyReady,sellReady,minToken,quantity_to_trade)
