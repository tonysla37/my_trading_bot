import ftx
import pandas as pd
import pandas_ta as pda
import matplotlib.pyplot as plt
import numpy as np
import ta
import time
import json
import matplotlib.pyplot as plt
from math import *
from binance.client import Client
from termcolor import colored


def getBalance(myclient, coin):
    jsonBalance = myclient.get_balances()
    if jsonBalance == []:
        return 0
    pandaBalance = pd.DataFrame(jsonBalance)
    print(pandaBalance)
    if pandaBalance.loc[pandaBalance['coin'] == coin].empty:
        return 0
    else:
        return float(pandaBalance.loc[pandaBalance['coin'] == coin]['total'])

def truncate(n, decimals=0):
    r = floor(float(n)*10**decimals)/10**decimals
    return str(r)

def buyCondition(fiatAmount, values):
  if float(fiatAmount) > 5 and df['EMA1'].iloc[-2] > df['EMA2'].iloc[-2] and df['STOCH_RSI'].iloc[-2] < 0.8:
    return True
  else:
    return False

def sellCondition(cryptoAmount, values):
  if float(cryptoAmount) > 0.001 and df['EMA1'].iloc[-2] < df['EMA2'].iloc[-2] and df['STOCH_RSI'].iloc[-2] > 0.2:
    return True
  else:
    return False

def get_chop(high, low, close, window):
    tr1 = pd.DataFrame(high - low).rename(columns = {0:'tr1'})
    tr2 = pd.DataFrame(abs(high - close.shift(1))).rename(columns = {0:'tr2'})
    tr3 = pd.DataFrame(abs(low - close.shift(1))).rename(columns = {0:'tr3'})
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis = 1, join = 'inner').dropna().max(axis = 1)
    atr = tr.rolling(1).mean()
    highh = high.rolling(window).max()
    lowl = low.rolling(window).min()
    ci = 100 * np.log10((atr.rolling(window).sum()) / (highh - lowl)) / np.log10(window)
    return ci

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
df['CHOP'] = get_chop(high=df['high'], low=df['low'], close=df['close'], window=14)  

print(df)

actualPrice = df['close'].iloc[-1]
# fiatAmount = getBalance(client, fiatSymbol)
# cryptoAmount = getBalance(client, cryptoSymbol)
fiatAmount = 1000
cryptoAmount = 0.5
tradeAmount = float(fiatAmount)*risk/actualPrice
print('coin price :',actualPrice, 'usd balance', fiatAmount, 'coin balance :',cryptoAmount)

minToken = 5/actualPrice


if buyCondition(fiatAmount,df) == True :
  if float(fiatAmount) > 5 and buyReady == True :
    quantityBuy = truncate(tradeAmount, myTruncate)

    #You can define here at what price you buy
    buyPrice = df['close']
    #Define the price of you SL and TP or comment it if you don't want a SL or TP
    stopLoss = buyPrice - 0.02 * buyPrice
    takeProfit = buyPrice + 0.1 * buyPrice

    # Define stoploss and takeprofit order !

    # buyOrder = client.place_order(
    #     market=pairSymbol,
    #     side="buy",
    #     price=None,
    #     size=quantityBuy,
    #     type='market')
    buyOrder = "Buy Order placed for that quantity :" + quantityBuy
    buyReady = False
    sellReady = True
    print(buyOrder)
elif sellCondition(cryptoAmount, df) == True :
  if float(cryptoAmount) > minToken and sellReady == True:
    quantitySell = truncate(tradeAmount, myTruncate)
    # buyOrder = client.place_order(
    #     market=pairSymbol,
    #     side="sell",
    #     price=None,
    #     size=truncate(cryptoAmount, myTruncate),
    #     type='market')
    buyOrder = "Sell Order placed for that quantity :" + quantitySell
    buyReady = True
    sellReady = False
    print(buyOrder)
else :
  print("No opportunity to take")

