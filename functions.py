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

def define_risk(risk_level):
    if risk_level == "Low":
      risk = 0.01
    elif risk_level == "Mid":
      risk = 0.02
    elif risk_level == "Max":
      risk = 0.03
    return risk

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



# Trade function
def trade_action(client,bench_mode,pairSymbol,fiatAmount,cryptoAmount,values,buyReady,sellReady,minToken,tradeAmount,myTruncate):
  if buyCondition(fiatAmount,values) == True :
    if float(fiatAmount) > 5 and buyReady == True :
      #You can define here at what price you buy
      buyPrice = values['close'].iloc[-1]

      # Prepare trades variables
      quantityBuy = truncate(tradeAmount, myTruncate)
      sl_level = 0.02
      tp1_level = 0.1
      tp2_level = 0.15
      tp3_level = 0.2
      sl_amount = 1
      tp1_amount = 0.5
      tp2_amount = 0.3
      tp3_amount = 0.2

      # Define the price of you SL and TP or comment it if you don't want a SL or TP
      stopLoss = buyPrice - sl_level * buyPrice
      takeProfit_1 = buyPrice + tp1_level * buyPrice
      takeProfit_2 = buyPrice + tp2_level * buyPrice
      takeProfit_3 = buyPrice + tp3_level * buyPrice
      sl_quantity = sl_amount * float(quantityBuy)
      tp1_quantity = tp1_amount * float(quantityBuy)
      tp2_quantity = tp2_amount * float(quantityBuy)
      tp3_quantity = tp3_amount * float(quantityBuy)

      # Request orders
      if bench_mode == True :
        buyOrder = "Buy Order placed for that quantity : " + quantityBuy
        sellOrder_SL = "SL Order placed at price : " + str(stopLoss) + " And for this quantity : " + str(quantityBuy)
        sellOrder_TP1 = "TP1 Order placed at price : " + str(takeProfit_1) + " And for this quantity : " + str(tp1_quantity)
        sellOrder_TP2 = "TP2 Order placed at price : " + str(takeProfit_2) + " And for this quantity : " + str(tp2_quantity)
        sellOrder_TP3 = "TP3 Order placed at price : " + str(takeProfit_3) + " And for this quantity : " + str(tp3_quantity)

      elif bench_mode == False :
        # Define buy order
        buyOrder = client.place_order(
            market=pairSymbol,
            side="buy",
            price=None,
            size=quantityBuy,
            type='market')
        # Define stoploss and takeprofit order
        sellOrder_SL = client.place_order(
            market=pairSymbol,
            side="sell",
            price=stopLoss,
            size=quantityBuy,
            type='limit')
        sellOrder_TP1 = client.place_order(
            market=pairSymbol,
            side="sell",
            price=takeProfit_1,
            size=tp1_quantity,
            type='limit')
        sellOrder_TP2 = client.place_order(
            market=pairSymbol,
            side="sell",
            price=takeProfit_2,
            size=tp2_quantity,
            type='limit')
        sellOrder_TP3 = client.place_order(
            market=pairSymbol,
            side="sell",
            price=takeProfit_3,
            size=tp3_quantity,
            type='limit')
      
      buyReady = False
      sellReady = True
      print(buyOrder)
      print(sellOrder_SL)
      print(sellOrder_TP1)
      print(sellOrder_TP2)
      print(sellOrder_TP3)
      print(buyPrice)
      print(stopLoss)
      print(takeProfit_1)
      print(takeProfit_2)
      print(takeProfit_3)

  elif sellCondition(cryptoAmount, values) == True :
    if float(cryptoAmount) > minToken and sellReady == True:
      quantitySell = truncate(cryptoAmount, myTruncate)
      # Define sell order
      # sellOrder = client.place_order(
      #     market=pairSymbol,
      #     side="sell",
      #     price=None,
      #     size=quantitySell,
      #     type='market')
      sellOrder = "Sell Order placed for that quantity :" + quantitySell

      buyReady = True
      sellReady = False
      print(sellOrder)
  else :
    print("No opportunity to take")