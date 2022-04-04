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

# /!\ Calculate PNL to manage to modify the risk_level
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

def analyse_stoch_rsi(blue, orange):
  pc_blue = float(blue) * 100
  pc_orange = float(orange) * 100

  if pc_blue <= 20 and pc_orange <= 20 :
    status = "oversell"
  elif pc_blue >= 80 and pc_orange >= 80 :
    status = "overbuy"
  elif pc_blue > pc_orange :
    status = "ok"
  else :
      # /!\ si tendance 0,5 vers 0,8 => bull. Si tendance 0,5 vers 0,2 => bear
    status = "bad"
  
  return status

def analyse_rsi(rsi):
  if rsi <= 30 :
    status = "oversell"
  elif rsi >= 70 :
    status = "overbuy"
  else :
    # /!\ si tendance 0,5 vers 0,8 => bull. Si tendance 0,5 vers 0,2 => bear
    status = "ok"
  return status




# Buy Algorithm
def buyCondition(fiatAmount, values):
  if float(fiatAmount) > 5 and values['EMA1'].iloc[-2] > values['EMA2'].iloc[-2] and values['STOCH_RSI'].iloc[-2] < 0.8:
    return True
  else:
    return False

# Sell Algorithm
def sellCondition(cryptoAmount, values):
  if float(cryptoAmount) > 0.001 and values['EMA1'].iloc[-2] < values['EMA2'].iloc[-2] and values['STOCH_RSI'].iloc[-2] > 0.2:
    return True
  else:
    return False

# Trade function
def trade_action(client,bench_mode,pairSymbol,fiatAmount,cryptoAmount,values,buyReady,sellReady,minToken,tradeAmount,myTruncate,protection):
  if buyCondition(fiatAmount,values) == True :
    if float(fiatAmount) > 5 and buyReady == True :
      #You can define here at what price you buy
      buyPrice = values['close'].iloc[-1]

      # Prepare trades variables
      quantityBuy = truncate(tradeAmount, myTruncate)
      sl_level = protection["sl_level"]
      tp1_level = protection["tp1_level"]
      tp2_level = protection["tp2_level"]
      tp3_level = protection["tp3_level"]
      sl_amount = protection["sl_amount"]
      tp1_amount = protection["tp1_amount"]
      tp2_amount = protection["tp2_amount"]
      tp3_amount = protection["tp3_amount"]

      # Define the price of you SL and TP or comment it if you don't want a SL or TP
      stopLoss = buyPrice - sl_level * buyPrice
      takeProfit_1 = buyPrice + tp1_level * buyPrice
      takeProfit_2 = buyPrice + tp2_level * buyPrice
      takeProfit_3 = buyPrice + tp3_level * buyPrice
      sl_quantity = sl_amount * float(quantityBuy)
      tp1_quantity = tp1_amount * float(quantityBuy)
      tp2_quantity = tp2_amount * float(quantityBuy)
      tp3_quantity = tp3_amount * float(quantityBuy)
      possible_gain = (takeProfit_1 - buyPrice) * float(quantityBuy)
      possible_loss = (buyPrice - stopLoss) * float(quantityBuy)
      R = possible_gain / possible_loss

      # Request orders
      if bench_mode == True :
        buyOrder = "Buy Order placed for that quantity : " + quantityBuy
        sellOrder_SL = "SL Order placed at price : " + str(stopLoss) + " And for this quantity : " + str(sl_quantity)
        sellOrder_TP1 = "TP1 Order placed at price : " + str(takeProfit_1) + " And for this quantity : " + str(tp1_quantity)
        sellOrder_TP2 = "TP2 Order placed at price : " + str(takeProfit_2) + " And for this quantity : " + str(tp2_quantity)
        sellOrder_TP3 = "TP3 Order placed at price : " + str(takeProfit_3) + " And for this quantity : " + str(tp3_quantity)

      elif bench_mode == False :
        # Define buy order
        buyOrder = client.place_order(
            market=pairSymbol,
            side="buy",
            price=buyPrice,
            size=quantityBuy,
            type='limit')
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
      print('Buy price :',buyPrice, 'Stop loss :',stopLoss,'TP1 :', takeProfit_1,'TP2 :', takeProfit_2,'TP3 :', takeProfit_3)
      print('Possible gain :',possible_gain,'Possible loss :',possible_loss, 'R :',R)
      print(buyOrder)
      print(sellOrder_SL)
      print(sellOrder_TP1)
      print(sellOrder_TP2)
      print(sellOrder_TP3)

  elif sellCondition(cryptoAmount, values) == True :
    if float(cryptoAmount) > minToken and sellReady == True:
      quantitySell = truncate(cryptoAmount, myTruncate)

      # Request orders
      if bench_mode == True :
        sellOrder = "Sell Order placed for that quantity :" + quantitySell

      elif bench_mode == False :
        # Define sell order
        sellOrder = client.place_order(
            market=pairSymbol,
            side="sell",
            price=None,
            size=quantitySell,
            type='market')

      buyReady = True
      sellReady = False
      print(sellOrder)
  else :
    print("No opportunity to take")