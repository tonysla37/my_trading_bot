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
  if float(fiatAmount) > 5 and values['EMA1'].iloc[-2] > values['EMA2'].iloc[-2] and values['STOCH_RSI'].iloc[-2] < 0.8:
    return True
  else:
    return False

def sellCondition(cryptoAmount, values):
  if float(cryptoAmount) > 0.001 and values['EMA1'].iloc[-2] < values['EMA2'].iloc[-2] and values['STOCH_RSI'].iloc[-2] > 0.2:
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

def define_quantity_to_trade(tradeAmount,myTruncate):
    quantity_to_trade = truncate(tradeAmount, myTruncate)
    return quantity_to_trade

def trade_action(fiatAmount,cryptoAmount,values,buyReady,sellReady,minToken,quantity_to_trade):
  if buyCondition(fiatAmount,values) == True :
    if float(fiatAmount) > 5 and buyReady == True :
      quantityBuy = quantity_to_trade

      #You can define here at what price you buy
      buyPrice = values['close']
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
  elif sellCondition(cryptoAmount, values) == True :
    if float(cryptoAmount) > minToken and sellReady == True:
      quantitySell = quantity_to_trade
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