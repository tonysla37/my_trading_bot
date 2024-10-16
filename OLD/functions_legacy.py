from datetime import date
import pandas as pd
import pandas_ta as pda
import matplotlib.pyplot as plt
import numpy as np
import ta
import time
import json
import krakenex
from pykrakenapi import KrakenAPI
from math import *
from termcolor import colored

import requests
import datetime
from discord import Webhook, RequestsWebhookAdapter

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
    ''' Choppiness indicator
    '''
    tr1 = pd.DataFrame(high - low).rename(columns={0: 'tr1'})
    tr2 = pd.DataFrame(abs(high - close.shift(1))
                       ).rename(columns={0: 'tr2'})
    tr3 = pd.DataFrame(abs(low - close.shift(1))
                       ).rename(columns={0: 'tr3'})
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').dropna().max(axis=1)
    atr = tr.rolling(1).mean()
    highh = high.rolling(window).max()
    lowl = low.rolling(window).min()
    chop_serie = 100 * np.log10((atr.rolling(window).sum()) /
                          (highh - lowl)) / np.log10(window)
    return pd.Series(chop_serie, name="CHOP")

def analyse_macd(macd,signal,histogram):
  #€ Stratégie 1
  # histogram : différence entre les deux lignes MACD
  # if histogram > 0 :
  #   trend = "buy"
  # elif histogram < 0 :
  #   trend = "sell"

  ## Stratégie 2
  # Ligne de signal
  # achat quand la ligne de signal est négative et quand elle sort de l'histogramme en négatif
  # vente quand la ligne de signal est positive et quand elle sort de l'histogramme en positif
  if signal < 0 and  signal < histogram :
    trend = "bearish"
  elif signal > 0 and  signal > histogram :
    trend = "bullish"

  ## Stratégie 3
  # Chercher les divergences
  return trend

def analyse_stoch_rsi(blue, orange,prev_blue,prev_orange):
  result = {}
  # pc_blue = float(blue) * 100
  # pc_orange = float(orange) * 100
  # pc_prev_blue = float(prev_blue) * 100
  # pc_prev_orange = float(prev_orange) * 100

  if blue <= 20 or orange <= 20 :
    trend = "oversell"
  elif blue >= 80 or orange >= 80 :
    trend = "overbuy"
  else :
      # /!\ si tendance 0,5 vers 0,8 => bull. Si tendance 0,5 vers 0,2 => bear  
    if blue > orange and blue > prev_blue and orange > prev_orange:
      trend = "bullish"
    elif blue < orange and blue < prev_blue and orange < prev_orange :
      trend = "bearish"
  
  result["trend"] = trend
  result["blue"] = blue
  result["orange"] = orange
  result["prev_blue"] = prev_blue
  result["prev_orange"] = prev_orange

  return result

def analyse_rsi(rsi,prev_rsi):
  result = {}
  if rsi <= 30 :
    trend = "oversell"
  elif rsi >= 70 :
    trend = "overbuy"
  else :
    # /!\ si tendance 0,5 vers 0,8 => bull. Si tendance 0,5 vers 0,2 => bear
    if rsi > 50 :
      if rsi > prev_rsi :
        trend = "bullish"
      elif rsi < prev_rsi :
        trend = "bearish divergence"
      else : 
        trend = "neutral"
    elif rsi < 50 : 
      if rsi < prev_rsi :
        trend = "bearish"
      elif rsi > prev_rsi :
        trend = "bullish divergence"
      else : 
        trend = "neutral"
  
  result["trend"] = trend
  result["rsi"] = rsi
  result["prev_rsi"] = prev_rsi

  status = "Trend : "+ trend + ", RSI : " + str(rsi) + ", RSI-3 : " + str(prev_rsi)

  return result

def analyse_ema(ema1,ema2,ema3,ema4,ema5,ema6):
  if ema1 > ema2 and ema2 > ema3 and ema3 > ema4 and ema4 > ema5 and ema5 > ema6 :
    trend = "bullish"
  elif ema6 > ema1 :
    trend = "bearish"
  else :
    trend = "neutral"
  return trend

def analyse_bollinger(high,low,average,close):
  # long = 20
  # std_dev = 2 # Ecart type

  # Quand les bornes haute et basse sont rapprochés alors risque de moment explosif
  # Attendre la confirmation du mouvement
  # 95% du temps la cloture se fait dans les bandes
  # Sinon anomalie => retour à la normale (scalping -> momentum) ou engendre une tendance
  
  result = {}

  # volatilité
  spread_band = high - low
  spread_price = close - average

  volatility_pc = spread_band / close * 100

  if volatility_pc > 20 :
    volatility = "high"
  else :
    volatility = "low"
  
  if close > high :
    trend = "overbuy"
  if close < low :
    trend = "oversell"
  else:
      if close > average :
        trend = "over_sma"
      if close < average :
        trend = "under_sma"
  
  result["trend"] = trend
  result["spread_band"] = spread_band
  result["spread_price"] = spread_price
  result["volatility"] = volatility
  result["volatility_pc"] = volatility_pc

  status = "Trend : " + trend + ", Band spread : " + str(spread_band) + ", Price spread : " + str(spread_price) + ", Volatility : " + str(volatility) + ", Volatility (%) : " + str(volatility_pc)

  return result

def analyse_adi(adi, prev_adi):
    if adi > prev_adi:
        return "bullish"
    elif adi < prev_adi:
        return "bearish"
    else:
        return "neutral"

# # Buy Algorithm
# def buyCondition(ema, rsi, stoch_rsi):
#   #if ema == "good" and rsi == "oversell" and stoch_rsi == "oversell":
#   if ema == "good" :
#     return True
#   else:
#     return False

# # Sell Algorithm
# def sellCondition(ema, rsi, stoch_rsi):
#   #if ema == "bad" and rsi == "overbuy" and stoch_rsi == "overbuy":
#   if ema == "bad" :
#     return True
#   else:
#     return False

def buyCondition(row, previousRow):
  if row['ema7'] > row['ema30'] and row['ema30'] > row['ema50'] and row['ema50'] > row['ema100'] and row['ema100'] > row['ema150'] and row['ema150'] > row['ema200'] and row['stoch_rsi'] < 0.82:
    return True
  else:
    return False

def sellCondition(row, previousRow):
  if row['ema200'] > row['ema7'] and row['stoch_rsi'] > 0.2:
    return True
  else:
    return False

def enterintrade(res_ema,res_rsi,res_stoch_rsi,res_bollinger,res_macd) :
  if res_ema == "bullish" and res_rsi["trend"] == "bullish" and res_stoch_rsi["trend"] == "bullish" :
    trade = True
  return trade


# Code généré par l'IA #
def place_buy_order(pair, volume):
    try:
        order = api.query_private('AddOrder', {
            'pair': pair,
            'type': 'buy',
            'ordertype': 'limit',
            'volume': volume
        })
        print("Buy order placed:", order)
    except Exception as e:
        print("An error occurred", e)

def place_sell_order(pair, volume):
    try:
        order = api.query_private('AddOrder', {
            'pair': pair,
            'type': 'sell',
            'ordertype': 'limit',
            'volume': volume
        })
        print("Sell order placed:", order)
    except Exception as e:
        print("An error occurred", e)
# Code généré par l'IA #


# Trade function
def trade_action(client,bench_mode,pairSymbol,fiatAmount,cryptoAmount,values,buyReady,sellReady,minToken,tradeAmount,myTruncate,protection,res_ema,res_rsi,res_stoch_rsi,res_bollinger,res_macd):
  webhook = Webhook.from_url("https://discord.com/api/webhooks/984026868552433674/yw6FcEhCZYPzgFdKJG6aAo7m52xGRIHLs9g0OocEQzYSofCGqCjsagtUMcTh26ewpOJs", adapter=RequestsWebhookAdapter())
  webhook.send('################## TRADING ADVISOR '+ str(datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')) + ' ##################')
  webhook.send('ema => ' + res_ema)
  webhook.send('rsi => ' + res_rsi["trend"])
  webhook.send('stoch_rsi => ' + res_stoch_rsi["trend"])
  webhook.send('bollinger => ' + res_bollinger["trend"])
  webhook.send('macd => ' + res_macd)
  
  if buyCondition(values.iloc[-2],values.iloc[-3]) == True :
    if float(fiatAmount) > 5 and buyReady == True :
      #You can define here at what price you buy
      buyPrice = values['close'].iloc[-1]

      # Prepare trades variables
      quantityBuy = truncate(tradeAmount, myTruncate)
      sl_level = protection["sl_level"]
      tp1_level = protection["tp1_level"]
      sl_amount = protection["sl_amount"]
      tp1_amount = protection["tp1_amount"]

      # Define the price of you SL and TP or comment it if you don't want a SL or TP
      stopLoss = buyPrice - sl_level * buyPrice
      takeProfit_1 = buyPrice + tp1_level * buyPrice
      sl_quantity = sl_amount * float(quantityBuy)
      tp1_quantity = tp1_amount * float(quantityBuy)
      possible_gain = (takeProfit_1 - buyPrice) * float(quantityBuy)
      possible_loss = (buyPrice - stopLoss) * float(quantityBuy)
      R = possible_gain / possible_loss

      # Request orders
      if bench_mode == True :
        buyOrder = "Buy Order placed for that quantity : " + quantityBuy
        sellOrder_SL = "SL Order placed at price : " + str(stopLoss) + " And for this quantity : " + str(sl_quantity)
        sellOrder_TP1 = "TP1 Order placed at price : " + str(takeProfit_1) + " And for this quantity : " + str(tp1_quantity)

      elif bench_mode == False :
        # # Define buy order
        # buyOrder = client.place_order(
        #     market=pairSymbol,
        #     side="buy",
        #     price=buyPrice,
        #     size=quantityBuy,
        #     type='limit')
        # # Define stoploss and takeprofit order
        # sellOrder_SL = client.place_order(
        #     market=pairSymbol,
        #     side="sell",
        #     price=stopLoss,
        #     size=quantityBuy,
        #     type='limit')
        # sellOrder_TP1 = client.place_order(
        #     market=pairSymbol,
        #     side="sell",
        #     price=takeProfit_1,
        #     size=tp1_quantity,
        #     type='limit')

# /!\ a finaliser
        buyOrder = client.place_buy_order(
            pair=pairSymbol,
            price=buyPrice,
            size=quantityBuy)
        # Define stoploss and takeprofit order
        sellOrder_SL = client.place_sell_order(
            market=pairSymbol,
            side="sell",
            price=stopLoss,
            size=quantityBuy,
            type='limit')
        sellOrder_TP1 = client.place_sell_order(
            market=pairSymbol,
            side="sell",
            price=takeProfit_1,
            size=tp1_quantity,
            type='limit')
# /!\ a finaliser
      
      buyReady = False
      sellReady = True
      print('Buy price :',buyPrice, 'Stop loss :',stopLoss,'TP1 :', takeProfit_1)
      print('Possible gain :',possible_gain,'Possible loss :',possible_loss, 'R :',R)
      print(buyOrder)
      print(sellOrder_SL)
      print(sellOrder_TP1)
      webhook.send('Buy price : ' + str(buyPrice))
      webhook.send('Stop loss : ' + str(stopLoss))
      webhook.send('TP1 : ' + str(takeProfit_1))
      webhook.send('Possible gain : ' + str(possible_gain))
      webhook.send('Possible loss : ' + str(possible_loss))
      webhook.send('R : ' + str(R))
      webhook.send(buyOrder)
      webhook.send(sellOrder_SL)
      webhook.send(sellOrder_TP1)

  elif sellCondition(values.iloc[-2],values.iloc[-3]) == True :
    if float(cryptoAmount) > minToken and sellReady == True:
      quantitySell = truncate(cryptoAmount, myTruncate)

      # Request orders
      if bench_mode == True :
        sellOrder = "Sell Order placed for that quantity :" + quantitySell

      elif bench_mode == False :
        # Define sell order
        # sellOrder = client.place_order(
        #     market=pairSymbol,
        #     side="sell",
        #     price=None,
        #     size=quantitySell,
        #     type='market')

        # /!\ a finaliser
        buyOrder = client.place_buy_order(
            market=pairSymbol,
            side="buy",
            price=buyPrice,
            size=quantityBuy,
            type='limit')
        # Define stoploss and takeprofit order
        sellOrder_SL = client.place_sell_order(
            market=pairSymbol,
            side="sell",
            price=stopLoss,
            size=quantityBuy,
            type='limit')
        sellOrder_TP1 = client.place_sell_order(
            market=pairSymbol,
            side="sell",
            price=takeProfit_1,
            size=tp1_quantity,
            type='limit')
        # /!\ a finaliser

      buyReady = True
      sellReady = False
      print(sellOrder)
      webhook.send(sellOrder)

  else :
    print("No opportunity to take")
    webhook.send("No opportunity to take")

  webhook.send('################## TRADING ADVISOR END ##################')


def backtest_strategy(values):

  bt_df = values.copy()
  bt_dt = None
  bt_dt = pd.DataFrame(columns = ['date','position', 'reason', 'price', 'frais' ,'fiat', 'coins', 'wallet', 'drawBack'])

  # DATA
  bt_usdt = 1000
  bt_initalWallet = bt_usdt
  bt_coin = 0
  bt_wallet = 1000
  bt_lastAth = 0
  bt_previousRow = bt_df.iloc[0]
  bt_makerFee = 0.0003
  bt_takerFee = 0.0007
  bt_stopLoss = 0
  bt_takeProfit = 500000
  bt_buyReady = True
  bt_sellReady = True

  for bt_index, bt_row in bt_df.iterrows():
    bt_res_ema = analyse_ema(ema1=bt_row['ema7'],ema2=bt_row['ema30'],ema3=bt_row['ema50'],ema4=bt_row['ema100'],ema5=bt_row['ema150'],ema6=bt_row['ema200'])
    bt_res_rsi = analyse_rsi(rsi=bt_row['rsi'])
    bt_res_stoch_rsi = analyse_stoch_rsi(blue=bt_row['stochastic'],orange=bt_row['stoch_signal'])

    #Buy market order
    if buyCondition(bt_row,bt_previousRow) == True and bt_usdt > 0 and bt_buyReady == True:
      #You can define here at what price you buy
      bt_buyPrice = bt_row['close']
      #Define the price of you SL and TP or comment it if you don't want a SL or TP
      bt_stopLoss = bt_buyPrice - 0.02 * bt_buyPrice
      bt_takeProfit = bt_buyPrice + 0.1 * bt_buyPrice
      bt_coin = bt_usdt / bt_buyPrice
      bt_fee = bt_takerFee * bt_coin
      bt_coin = bt_coin - bt_fee
      bt_usdt = 0
      bt_wallet = bt_coin * bt_row['close']
      if bt_wallet > bt_lastAth:
        bt_lastAth = bt_wallet

      # print("Buy COIN at",buyPrice,'$ the', index)
      #bt_myrow = {'date': bt_index,'position': "Buy", 'reason': 'Buy Market','price': bt_buyPrice,'frais': bt_fee*bt_row['close'],'fiat': bt_usdt,'coins': bt_coin,'wallet': bt_wallet,'drawBack':(bt_wallet-bt_lastAth)/bt_lastAth}
      bt_myrow = pd.DataFrame([[bt_index,"Buy",'Buy Market',bt_buyPrice,bt_fee*bt_row['close'],bt_usdt,bt_coin,bt_wallet,(bt_wallet-bt_lastAth)/bt_lastAth]], columns = ['date','position', 'reason', 'price', 'frais' ,'fiat', 'coins', 'wallet', 'drawBack'])
      bt_dt = pd.concat([bt_dt,bt_myrow], ignore_index=True)

    #Stop Loss
    elif bt_row['low'] < bt_stopLoss and bt_coin > 0:
      bt_sellPrice = bt_stopLoss
      bt_usdt = bt_coin * bt_sellPrice
      bt_fee = bt_makerFee * bt_usdt
      bt_usdt = bt_usdt - bt_fee
      bt_coin = 0
      bt_buyReady = False
      bt_wallet = bt_usdt
      if bt_wallet > bt_lastAth:
        bt_lastAth = bt_wallet
      # print("Sell COIN at Stop Loss",sellPrice,'$ the', index)
      #bt_myrow = {'date': bt_index,'position': "Sell", 'reason': 'Sell Stop Loss', 'price': bt_sellPrice, 'frais': bt_fee, 'fiat': bt_usdt, 'coins': bt_coin, 'wallet': bt_wallet, 'drawBack':(bt_wallet-bt_lastAth)/bt_lastAth}
      bt_myrow = pd.DataFrame([[bt_index,"Sell",'Sell Stop Loss',bt_sellPrice,bt_fee,bt_usdt,bt_coin,bt_wallet,(bt_wallet-bt_lastAth)/bt_lastAth]], columns = ['date','position', 'reason', 'price', 'frais' ,'fiat', 'coins', 'wallet', 'drawBack'])
      bt_dt = pd.concat([bt_dt,bt_myrow], ignore_index=True)

    #Take Profit
    elif bt_row['high'] > bt_takeProfit and bt_coin > 0:
      bt_sellPrice = bt_takeProfit
      bt_usdt = bt_coin * bt_sellPrice
      bt_fee = bt_makerFee * bt_usdt
      bt_usdt = bt_usdt - bt_fee
      bt_coin = 0
      bt_buyReady = False
      bt_wallet = bt_usdt
      if bt_wallet > bt_lastAth:
        bt_lastAth = bt_wallet
      # print("Sell COIN at Take Profit Loss",sellPrice,'$ the', index)
      #bt_myrow = {'date': bt_index,'position': "Sell", 'reason': 'Sell Take Profit', 'price': bt_sellPrice, 'frais': bt_fee, 'fiat': bt_usdt, 'coins': bt_coin, 'wallet': bt_wallet, 'drawBack':(bt_wallet-bt_lastAth)/bt_lastAth}
      bt_myrow = pd.DataFrame([[bt_index,"Sell",'Sell Take Profit',bt_sellPrice,bt_fee,bt_usdt,bt_coin,bt_wallet,(bt_wallet-bt_lastAth)/bt_lastAth]], columns = ['date','position', 'reason', 'price', 'frais' ,'fiat', 'coins', 'wallet', 'drawBack'])
      bt_dt = pd.concat([bt_dt,bt_myrow], ignore_index=True)

      # Sell Market
    elif sellCondition(bt_row,bt_previousRow) == True:
      bt_buyReady = True
      if bt_coin > 0 and bt_sellReady == True:
        bt_sellPrice = bt_row['close']
        bt_usdt = bt_coin * bt_sellPrice
        bt_frais = bt_takerFee * bt_usdt
        bt_usdt = bt_usdt - bt_frais
        bt_coin = 0
        bt_wallet = bt_usdt
        if bt_wallet > bt_lastAth:
          bt_lastAth = bt_wallet
        # print("Sell COIN at",sellPrice,'$ the', index)
        #bt_myrow = {'date': bt_index,'position': "Sell", 'reason': 'Sell Market', 'price': bt_sellPrice, 'frais': bt_frais, 'fiat': bt_usdt, 'coins': bt_coin, 'wallet': bt_wallet, 'drawBack':(bt_wallet-bt_lastAth)/bt_lastAth}
        bt_myrow = pd.DataFrame([[bt_index,"Sell",'Sell Market',bt_sellPrice,bt_frais,bt_usdt,bt_coin,bt_wallet,(bt_wallet-bt_lastAth)/bt_lastAth]], columns = ['date','position', 'reason', 'price', 'frais' ,'fiat', 'coins', 'wallet', 'drawBack'])
        pd.concat([bt_dt,bt_myrow], ignore_index=True)
    
    bt_previousRow = bt_row

  #///////////////////////////////////////
  print("Period : [" + str(bt_df.index[0]) + "] -> [" +str(bt_df.index[len(bt_df)-1]) + "]")
  bt_dt = bt_dt.set_index(bt_dt['date'])
  bt_dt.index = pd.to_datetime(bt_dt.index)
  bt_dt['resultat'] = bt_dt['wallet'].diff()
  bt_dt['resultat%'] = bt_dt['wallet'].pct_change()*100
  bt_dt.loc[bt_dt['position']=='Buy','resultat'] = None
  bt_dt.loc[bt_dt['position']=='Buy','resultat%'] = None

  bt_dt['tradeIs'] = ''
  bt_dt.loc[bt_dt['resultat']>0,'tradeIs'] = 'Good'
  bt_dt.loc[bt_dt['resultat']<=0,'tradeIs'] = 'Bad'

  bt_iniClose = bt_df.iloc[0]['close']
  bt_lastClose = bt_df.iloc[len(bt_df)-1]['close']
  bt_holdPorcentage = ((bt_lastClose - bt_iniClose)/bt_iniClose) * 100
  bt_algoPorcentage = ((bt_wallet - bt_initalWallet)/bt_initalWallet) * 100
  bt_vsHoldPorcentage = ((bt_algoPorcentage - bt_holdPorcentage)/bt_holdPorcentage) * 100

  print(bt_dt['tradeIs'])

  print("Starting balance : 1000 $")
  print("Final balance :",round(bt_wallet,2),"$")
  print("Performance vs US Dollar :",round(bt_algoPorcentage,2),"%")
  print("Buy and Hold Performance :",round(bt_holdPorcentage,2),"%")
  print("Performance vs Buy and Hold :",round(bt_vsHoldPorcentage,2),"%")
  print("Number of negative trades : ",bt_dt.groupby('tradeIs')['date'].nunique()['Bad'])
  print("Number of positive trades : ",bt_dt.groupby('tradeIs')['date'].nunique()['Good'])
  print("Average Positive Trades : ",round(bt_dt.loc[bt_dt['tradeIs'] == 'Good', 'resultat%'].sum()/bt_dt.loc[bt_dt['tradeIs'] == 'Good', 'resultat%'].count(),2),"%")
  print("Average Negative Trades : ",round(bt_dt.loc[bt_dt['tradeIs'] == 'Bad', 'resultat%'].sum()/bt_dt.loc[bt_dt['tradeIs'] == 'Bad', 'resultat%'].count(),2),"%")
  bt_idbest = bt_dt.loc[bt_dt['tradeIs'] == 'Good', 'resultat%'].idxmax()
  bt_idworst = bt_dt.loc[bt_dt['tradeIs'] == 'Bad', 'resultat%'].idxmin()
  print("Best trade +"+str(round(bt_dt.loc[bt_dt['tradeIs'] == 'Good', 'resultat%'].max(),2)),"%, the ",bt_dt['date'][bt_idbest])
  print("Worst trade",round(bt_dt.loc[bt_dt['tradeIs'] == 'Bad', 'resultat%'].min(),2),"%, the ",bt_dt['date'][bt_idworst])
  print("Worst drawBack", str(100*round(bt_dt['drawBack'].min(),2)),"%")
  print("Total fee : ",round(bt_dt['frais'].sum(),2),"$")
  bt_reasons = bt_dt['reason'].unique()
  for r in bt_reasons:
    print(r+" number :",bt_dt.groupby('reason')['date'].nunique()[r])

  bt_dt[['wallet','price']].plot(subplots=True, figsize=(20,10))
  print('END')
  bt_dt