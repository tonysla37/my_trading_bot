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
    #klinesT = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 january 2022")
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

  # Define Price Action
  df['close'] = pd.to_numeric(df['close'])
  df['high'] = pd.to_numeric(df['high'])
  df['low'] = pd.to_numeric(df['low'])
  df['open'] = pd.to_numeric(df['open'])

  ### Indicators
  ## Momentum (good moment)
  # Relative Strength Index (RSI)
  # beaucoup augmenté ou baissé => pas le bon moment
  # Chercher les divergences
  df['RSI'] =ta.momentum.rsi(close=df['close'], window=14)
  # Stochastic RSI
  # Quand on est en hausse continue, pas le moment d'acheter
  df['STOCH_RSI'] = ta.momentum.stochrsi(close=df['close'], window=14, smooth1=3, smooth2=3) # Non moyenné 
  df['STOCH_RSI_D'] = ta.momentum.stochrsi_d(close=df['close'], window=14, smooth1=3, smooth2=3) # Orange sur TradingView
  df['STOCH_RSI_K'] =ta.momentum.stochrsi_k(close=df['close'], window=14, smooth1=3, smooth2=3) # Bleu sur TradingView
  # #Awesome Oscillator
  # df['AWESOME_OSCILLATOR'] = ta.momentum.awesome_oscillator(high=df['high'], low=df['low'], window1=5, window2=34)
  # # Kaufman’s Adaptive Moving Average (KAMA)
  # df['KAMA1'] = ta.momentum.kama(close=ta.momentum.kama(close=ta.momentum.kama(close=df['close'], window=11, pow1=2, pow2=30), window=11, pow1=2, pow2=30), window=11, pow1=2, pow2=30)
  # df['KAMA2'] = ta.momentum.kama(close=df['close'], window=15, pow1=2, pow2=30)
  
  ## Trend (neutal, bull, bear), late
  # MACD : Connaitre la force du marché
  # bleu au dessus orange = bull
  # orange au dessus de bleu = bear
  MACD = ta.trend.MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
  df['MACD'] = MACD.macd()
  df['MACD_SIGNAL'] = MACD.macd_signal()
  df['MACD_DIFF'] = MACD.macd_diff() # Histogramme MACD
  # # Super Trend
  # # Determine des tendances sur la volatilité
  # # Si vert, confirme la hausse
  # # Si rouge, confirme la baisse
  # ST_length = 10
  # ST_multiplier = 3.0
  # superTrend = pda.supertrend(high=df['high'], low=df['low'], close=df['close'], length=ST_length, multiplier=ST_multiplier)
  # df['SUPER_TREND'] = superTrend['SUPERT_'+str(ST_length)+"_"+str(ST_multiplier)] #Valeur de la super trend
  # df['SUPER_TREND_DIRECTION'] = superTrend['SUPERTd_'+str(ST_length)+"_"+str(ST_multiplier)] #Retourne 1 si vert et -1 si rouge
  # Exponential Moving Average
  df['EMA1']=ta.trend.ema_indicator(close=df['close'], window=7)
  df['EMA2']=ta.trend.ema_indicator(close=df['close'], window=30)
  df['EMA3']=ta.trend.ema_indicator(close=df['close'], window=50)
  df['EMA4']=ta.trend.ema_indicator(close=df['close'], window=100)
  df['EMA5']=ta.trend.ema_indicator(close=df['close'], window=121)
  df['EMA6']=ta.trend.ema_indicator(close=df['close'], window=200)
  # # Ichimoku
  # df['KIJUN'] = ta.trend.ichimoku_base_line(high=df['high'], low=df['low'], window1=9, window2=26)
  # df['TENKAN'] = ta.trend.ichimoku_conversion_line(high=df['high'], low=df['low'], window1=9, window2=26)
  # df['SSA'] = ta.trend.ichimoku_a(high=df['high'], low=df['low'], window1=9, window2=26)
  # df['SSB'] = ta.trend.ichimoku_b(high=df['high'], low=df['low'], window2=26, window3=52)
  # # Simple Moving Average
  # df['SMA']=ta.trend.sma_indicator(df['close'], window=12)
  # # Trix Indicator
  # trixLength = 7
  # trixSignal = 15
  # df['TRIX'] = ta.trend.ema_indicator(ta.trend.ema_indicator(ta.trend.ema_indicator(close=df['close'], window=trixLength), window=trixLength), window=trixLength)
  # df['TRIX_PCT'] = df["TRIX"].pct_change()*100
  # df['TRIX_SIGNAL'] = ta.trend.sma_indicator(df['TRIX_PCT'],trixSignal)
  # df['TRIX_HISTO'] = df['TRIX_PCT'] - df['TRIX_SIGNAL']

  ## Volatility
  # # Bollinger Bands
  # # peu de volatilité quand les bandes se resserent
  # # 
  BOL_BAND = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
  df['BOL_H_BAND'] = BOL_BAND.bollinger_hband() #Bande Supérieur
  df['BOL_L_BAND'] = BOL_BAND.bollinger_lband() #Bande inférieur
  df['BOL_MAVG_BAND'] = BOL_BAND.bollinger_mavg() #Bande moyenne
  # # Average True Range (ATR)
  # # très bas quand la volatilité est basse
  # # très haute quand la volatilité est haute
  # # Permet de définir les stop loss ou take profit
  # df['ATR'] = ta.volatility.average_true_range(high=df['high'], low=df['low'], close=df['close'], window=14)

  ## Volume
  ## Other

  # Choppiness index
  df['CHOP'] = fx.get_chop(high=df['high'], low=df['low'], close=df['close'], window=14)

  # Define indicators
  res_ema = fx.analyse_ema(ema1=df['EMA1'].iloc[-1],ema2=df['EMA2'].iloc[-1])
  res_rsi = fx.analyse_rsi(rsi=df['RSI'].iloc[-1])
  res_stoch_rsi = fx.analyse_stoch_rsi(blue=df['STOCH_RSI_K'].iloc[-1],orange=df['STOCH_RSI_D'].iloc[-1])
  res_bollinger = fx.analyse_bollinger(high=df['BOL_H_BAND'].iloc[-1],low=df['BOL_L_BAND'].iloc[-1],average=df['BOL_MAVG_BAND'].iloc[-1],close=df['close'].iloc[-1])
  res_macd = fx.analyse_macd(macd=df['MACD'].iloc[-1],signal=df['MACD_SIGNAL'].iloc[-1],histogram=df['MACD_DIFF'].iloc[-1])


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

  # Bot actions execution
  #fx.trade_action(client,bench_mode,pairSymbol,fiatAmount,cryptoAmount,df,buyReady,sellReady,minToken,tradeAmount,myTruncate,protection,res_ema,res_rsi,res_stoch_rsi)

  if bench_mode == True :
    fx.backtest_strategy(df)
