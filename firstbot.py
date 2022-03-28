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
  if float(fiatAmount) > 5 and df['EMA28'].iloc[-2] > df['EMA48'].iloc[-2] and df['STOCH_RSI'].iloc[-2] < 0.8:
    return True
  else:
    return False

def sellCondition(cryptoAmount, values):
  if float(cryptoAmount) > 0.001 and df['EMA28'].iloc[-2] < df['EMA48'].iloc[-2] and df['STOCH_RSI'].iloc[-2] > 0.2:
    return True
  else:
    return False

accountName = ''
pairSymbol = 'BTC/USD'
fiatSymbol = 'USD'
cryptoSymbol = 'BTC'
myTruncate = 3
risk = 0.03

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

df['EMA28']=ta.trend.ema_indicator(df['close'], 28)
df['EMA48']=ta.trend.ema_indicator(df['close'], 48)
df['STOCH_RSI']=ta.momentum.stochrsi(df['close'])

print(df)

actualPrice = df['close'].iloc[-1]
# fiatAmount = getBalance(client, fiatSymbol)
# cryptoAmount = getBalance(client, cryptoSymbol)
fiatAmount = 1000
cryptoAmount = 0.5
tradeAmount = float(fiatAmount)*risk/actualPrice
print('coin price :',actualPrice, 'usd balance', fiatAmount, 'coin balance :',cryptoAmount)



if buyCondition(fiatAmount,df) == True :
    quantityBuy = truncate(tradeAmount, myTruncate)
    # buyOrder = client.place_order(
    #     market=pairSymbol,
    #     side="buy",
    #     price=None,
    #     size=quantityBuy,
    #     type='market')
    buyOrder = "Buy Order placed for that quantity :" + quantityBuy
    print(buyOrder)
elif sellCondition(cryptoAmount, df) == True :
    quantitySell = truncate(tradeAmount, myTruncate)
    # buyOrder = client.place_order(
    #     market=pairSymbol,
    #     side="sell",
    #     price=None,
    #     size=truncate(cryptoAmount, myTruncate),
    #     type='market')
    buyOrder = "Sell Order placed for that quantity :" + quantitySell
    print(buyOrder)
else :
      print("No opportunity to take")

