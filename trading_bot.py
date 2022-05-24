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
  protection["sl_amount"] = 1
  protection["tp1_amount"] = 1

  buyReady = True
  sellReady = True
  bench_mode = True
  risk_level = "Mid"

  risk= fx.define_risk(risk_level)

  if bench_mode == True :
    client = Client()
    #klinesT = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 january 2017")
    klinesT = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "01 january 2022")
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
  # # Heiki Ashi Bar
  # def heikinashi_df(df):
  #     df['ha_close'] = (df.open + df.high + df.low + df.close)/4
  #     ha_open = [(df.open[0] + df.close[0]) / 2]
  #     [ha_open.append((ha_open[i] + df.ha_close.values[i]) / 2)
  #      for i in range(0, len(df)-1)]
  #     df['ha_open'] = ha_open
  #     df['ha_high'] = df[['ha_open', 'ha_close', 'high']].max(axis=1)
  #     df['ha_low'] = df[['ha_open', 'ha_close', 'low']].min(axis=1)
  #     return df
  
  # df = heikinashi_df(df)


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

  # # VMC
  # #Class pour nos indicateurs
  # class VMC():
  #     """ VuManChu Cipher B + Divergences 
  #         Args:
  #             high(pandas.Series): dataset 'High' column.
  #             low(pandas.Series): dataset 'Low' column.
  #             close(pandas.Series): dataset 'Close' column.
  #             wtChannelLen(int): n period.
  #             wtAverageLen(int): n period.
  #             wtMALen(int): n period.
  #             rsiMFIperiod(int): n period.
  #             rsiMFIMultiplier(int): n period.
  #             rsiMFIPosY(int): n period.
  #     """
  #     def __init__(
  #         self: pd.Series,
  #         high: pd.Series,
  #         low: pd.Series,
  #         close: pd.Series,
  #         open: pd.Series,
  #         wtChannelLen: int = 9,
  #         wtAverageLen: int = 12,
  #         wtMALen: int = 3,
  #         rsiMFIperiod: int = 60,
  #         rsiMFIMultiplier: int = 150,
  #         rsiMFIPosY: int = 2.5
  #     ) -> None:
  #         self._high = high
  #         self._low = low
  #         self._close = close
  #         self._open = open
  #         self._wtChannelLen = wtChannelLen
  #         self._wtAverageLen = wtAverageLen
  #         self._wtMALen = wtMALen
  #         self._rsiMFIperiod = rsiMFIperiod
  #         self._rsiMFIMultiplier = rsiMFIMultiplier
  #         self._rsiMFIPosY = rsiMFIPosY
  #         self._run()
  #         self.wave_1()

  #     def _run(self) -> None:
  #         try:
  #             self._esa = ta.trend.ema_indicator(
  #                 close=self._close, window=self._wtChannelLen)
  #         except Exception as e:
  #             print(e)
  #             raise

  #         self._esa = ta.trend.ema_indicator(
  #             close=self._close, window=self._wtChannelLen)
  #         self._de = ta.trend.ema_indicator(
  #             close=abs(self._close - self._esa), window=self._wtChannelLen)
  #         self._rsi = ta.trend.sma_indicator(self._close, self._rsiMFIperiod)
  #         self._ci = (self._close - self._esa) / (0.015 * self._de)

  #     def wave_1(self) -> pd.Series:
  #         """VMC Wave 1 
  #         Returns:
  #             pandas.Series: New feature generated.
  #         """
  #         wt1 = ta.trend.ema_indicator(self._ci, self._wtAverageLen)
  #         return pd.Series(wt1, name="wt1")

  #     def wave_2(self) -> pd.Series:
  #         """VMC Wave 2
  #         Returns:
  #             pandas.Series: New feature generated.
  #         """
  #         wt2 = ta.trend.sma_indicator(self.wave_1(), self._wtMALen)
  #         return pd.Series(wt2, name="wt2")

  #     def money_flow(self) -> pd.Series:
  #         """VMC Money Flow
  #             Returns:
  #             pandas.Series: New feature generated.
  #         """
  #         mfi = ((self._close - self._open) /
  #                 (self._high - self._low)) * self._rsiMFIMultiplier
  #         rsi = ta.trend.sma_indicator(mfi, self._rsiMFIperiod)
  #         money_flow = rsi - self._rsiMFIPosY
  #         return pd.Series(money_flow, name="money_flow")

  # # Récupération des données
  # df['hlc3'] = (df['high'] +df['close'] + df['low'])/3
  # vmc = VMC(high =df['high'],low = df['low'],close=df['hlc3'],open=df['open'])
  # df['vmc_wave1'] = vmc.wave_1()
  # df['vmc_wave2'] = vmc.wave_2()
  # vmc = VMC(high=df['high'], low=df['low'], close=df['close'], open=df['open'])
  # df['money_flow'] = vmc.money_flow()

  # # WilliamsR
  # df['max_21'] = df['high'].rolling(21).max()
  # df['min_21'] = df['low'].rolling(21).min()
  # df['william_r'] = (df['close'] - df['max_21']) / (df['max_21'] - df['min_21']) * 100
  # df['emaw'] = ta.trend.ema_indicator(close=df['william_r'], window=13)

  # # CCI
  # df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3 
  # df['sma_cci'] = df['hlc3'].rolling(40).mean()
  # df['mad'] = df['hlc3'].rolling(40).apply(lambda x: pd.Series(x).mad())
  # df['cci'] = (df['hlc3'] - df['sma_cci']) / (0.015 * df['mad']) 

  # # PPO
  # df['ppo'] = ta.momentum.ppo(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
  # df['ppo_signal'] = ta.momentum.ppo_signal(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
  # df['ppo_histo'] = ta.momentum.ppo_hist(close=df['close'], window_slow=26, window_fast=12, window_sign=9)

  # # PVO
  # df['pvo'] = ta.momentum.pvo(volume = df['volume'], window_slow=26, window_fast=12, window_sign=9)
  # df['pvo_signal'] = ta.momentum.pvo_signal(volume = df['volume'], window_slow=26, window_fast=12, window_sign=9)
  # df['pvo_histo'] = ta.momentum.pvo_hist(volume = df['volume'], window_slow=26, window_fast=12, window_sign=9)

  # # Aroon
  # df['aroon_up'] = ta.trend.aroon_up(close=df['close'], window=25)
  # df['aroon_dow'] = ta.trend.aroon_down(close=df['close'], window=25)


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

  # # ADX
  # df['adx'] =ta.trend.adx(high=df['high'], low=df['low'], close = df['close'], window = 14)

  # # Super Trend
  # # Determine des tendances sur la volatilité
  # # Si vert, confirme la hausse
  # # Si rouge, confirme la baisse

  # # Classe de définition
  # class SuperTrend():
  #     def __init__(
  #         self,
  #         high,
  #         low,
  #         close,
  #         atr_window=10,
  #         atr_multi=3
  #     ):
  #         self.high = high
  #         self.low = low
  #         self.close = close
  #         self.atr_window = atr_window
  #         self.atr_multi = atr_multi
  #         self._run()
          
  #     def _run(self):
  #         # calculate ATR
  #         price_diffs = [self.high - self.low, 
  #                     self.high - self.close.shift(), 
  #                     self.close.shift() - self.low]
  #         true_range = pd.concat(price_diffs, axis=1)
  #         true_range = true_range.abs().max(axis=1)
  #         # default ATR calculation in supertrend indicator
  #         atr = true_range.ewm(alpha=1/self.atr_window,min_periods=self.atr_window).mean() 
  #         # atr = ta.volatility.average_true_range(high, low, close, atr_period)
  #         # df['atr'] = df['tr'].rolling(atr_period).mean()
          
  #         # HL2 is simply the average of high and low prices
  #         hl2 = (self.high + self.low) / 2
  #         # upperband and lowerband calculation
  #         # notice that final bands are set to be equal to the respective bands
  #         final_upperband = upperband = hl2 + (self.atr_multi * atr)
  #         final_lowerband = lowerband = hl2 - (self.atr_multi * atr)
          
  #         # initialize Supertrend column to True
  #         supertrend = [True] * len(self.close)
          
  #         for i in range(1, len(self.close)):
  #             curr, prev = i, i-1
              
  #             # if current close price crosses above upperband
  #             if self.close[curr] > final_upperband[prev]:
  #                 supertrend[curr] = True
  #             # if current close price crosses below lowerband
  #             elif self.close[curr] < final_lowerband[prev]:
  #                 supertrend[curr] = False
  #             # else, the trend continues
  #             else:
  #                 supertrend[curr] = supertrend[prev]
                  
  #                 # adjustment to the final bands
  #                 if supertrend[curr] == True and final_lowerband[curr] < final_lowerband[prev]:
  #                     final_lowerband[curr] = final_lowerband[prev]
  #                 if supertrend[curr] == False and final_upperband[curr] > final_upperband[prev]:
  #                     final_upperband[curr] = final_upperband[prev]

  #             # to remove bands according to the trend direction
  #             if supertrend[curr] == True:
  #                 final_upperband[curr] = np.nan
  #             else:
  #                 final_lowerband[curr] = np.nan
                  
  #         self.st = pd.DataFrame({
  #             'Supertrend': supertrend,
  #             'Final Lowerband': final_lowerband,
  #             'Final Upperband': final_upperband
  #         })
          
  #     def super_trend_upper(self):
  #         return self.st['Final Upperband']
          
  #     def super_trend_lower(self):
  #         return self.st['Final Lowerband']
          
  #     def super_trend_direction(self):
  #         return self.st['Supertrend']

  # # Récupération des valeurs
  # st_atr_window = 20
  # st_atr_multiplier = 3

  # super_trend = SuperTrend(df['high'], df['low'], df['close'], st_atr_window, st_atr_multiplier)
  # df['super_trend_direction'] = super_trend.super_trend_direction() # True if bullish, False if bearish
  # df['super_trend_upper'] = super_trend.super_trend_upper()
  # df['super_trend_lower'] = super_trend.super_trend_lower()

  # Exponential Moving Average
  df['ema7']=ta.trend.ema_indicator(close=df['close'], window=7)
  df['ema30']=ta.trend.ema_indicator(close=df['close'], window=30)
  df['ema50']=ta.trend.ema_indicator(close=df['close'], window=50)
  df['ema100']=ta.trend.ema_indicator(close=df['close'], window=100)
  df['ema150']=ta.trend.ema_indicator(close=df['close'], window=150)
  df['ema200']=ta.trend.ema_indicator(close=df['close'], window=200)

  # # Ichimoku
  # df['kijun'] = ta.trend.ichimoku_base_line(df['high'], df['low'])
  # df['tenkan'] = ta.trend.ichimoku_conversion_line(df['high'], df['low'])
  # df['ssa'] = ta.trend.ichimoku_a(df['high'], df['low'])
  # df['ssb'] = ta.trend.ichimoku_b(df['high'], df['low'])
  # df['ssa25'] = ta.trend.ichimoku_a(df['high'], df['low']).shift(25)
  # df['ssb25'] = ta.trend.ichimoku_b(df['high'], df['low']).shift(25)
  # df['ssa52'] = ta.trend.ichimoku_a(df['high'], df['low']).shift(50)
  # df['ssb52'] = ta.trend.ichimoku_b(df['high'], df['low']).shift(50)
  # df['close25'] = df['close'].shift(25)
  # df['close1'] = df['close'].shift(1)

  # # Simple Moving Average
  # df['sma7']=ta.trend.sma_indicator(close=df['close'], window=7)

  # # Trix Indicator
  # #Classe de féinition
  # class Trix():
  #     """ Trix indicator

  #         Args:
  #             close(pd.Series): dataframe 'close' columns,
  #             trixLength(int): the window length for each mooving average of the trix,
  #             trixSignal(int): the window length for the signal line
  #     """

  #     def __init__(
  #         self,
  #         close: pd.Series,
  #         trixLength: int = 9,
  #         trixSignal: int = 21
  #     ):
  #         self.close = close
  #         self.trixLength = trixLength
  #         self.trixSignal = trixSignal
  #         self._run()

  #     def _run(self):
  #         self.trixLine = ta.trend.ema_indicator(
  #             ta.trend.ema_indicator(
  #                 ta.trend.ema_indicator(
  #                     close=self.close, window=self.trixLength),
  #                 window=self.trixLength), window=self.trixLength)
  #         self.trixPctLine = self.trixLine.pct_change()*100
  #         self.trixSignalLine = ta.trend.sma_indicator(
  #             close=self.trixPctLine, window=self.trixSignal)
  #         self.trixHisto = self.trixPctLine - self.trixSignalLine

  #     def trix_line(self) -> pd.Series:
  #         """ trix line

  #             Returns:
  #                 pd.Series: trix line
  #         """
  #         return pd.Series(self.trixLine, name="TRIX_LINE")

  #     def trix_pct_line(self) -> pd.Series:
  #         """ trix percentage line

  #             Returns:
  #                 pd.Series: trix percentage line
  #         """
  #         return pd.Series(self.trixPctLine, name="TRIX_PCT_LINE")

  #     def trix_signal_line(self) -> pd.Series:
  #         """ trix signal line

  #             Returns:
  #                 pd.Series: trix siganl line
  #         """
  #         return pd.Series(self.trixSignal, name="TRIX_SIGNAL_LINE")

  #     def trix_histo(self) -> pd.Series:
  #         """ trix histogram

  #             Returns:
  #                 pd.Series: trix histogram
  #         """
  #         return pd.Series(self.trixHisto, name="TRIX_HISTO")

  # # Récupération des valeurs
  # trix_length = 9
  # trix_signal = 21
  # trix = Trix(df["close"], trix_length, trix_signal)
  # df['trix_pct_line'] = trix.trix_pct_line()
  # df['trix_signal_line'] = trix.trix_signal_line()
  # df['trix_histo'] = trix.trix_histo()

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

  # # Le canal de Donchian
  # df["don_high"] = ta.volatility.donchian_channel_hband(df['high'], df['low'], df['close'], window=20, offset=0)
  # df["don_low"] = ta.volatility.donchian_channel_lband(df['high'], df['low'], df['close'], window=20, offset=0)
  # df["don_medium"] = ta.volatility.donchian_channel_mband(df['high'], df['low'], df['close'], window=20, offset=0)

  # # Le canal de Keltner 
  # df["kel_high"] = ta.volatility.keltner_channel_hband(df['high'], df['low'], df['close'], window=20, window_atr=10)
  # df["kel_low"] = ta.volatility.keltner_channel_lband(df['high'], df['low'], df['close'], window=20, window_atr=10)
  # df["kel_medium"] = ta.volatility.keltner_channel_mband(df['high'], df['low'], df['close'], window=20 ,window_atr=10)
  # # Return binaire 0 ou 1 
  # df["kel_higher"] = ta.volatility.keltner_channel_hband_indicator(df['high'], df['low'], df['close'], window=20, window_atr=10)
  # df["kel_lower"] = ta.volatility.keltner_channel_lband_indicator(df['high'], df['low'], df['close'], window=20, window_atr=10)

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

  # # ADI Indicator
  # df["adi"] = ta.volume.acc_dist_index(high=df['high'], low=df['low'], close=df['close'], volume = df['volume'])

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
  res_rsi = fx.analyse_rsi(rsi=df['rsi'].iloc[-1])
  res_stoch_rsi = fx.analyse_stoch_rsi(blue=df['stochastic'].iloc[-1],orange=df['stoch_signal'].iloc[-1])
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

  # Bot actions execution
  #fx.trade_action(client,bench_mode,pairSymbol,fiatAmount,cryptoAmount,df,buyReady,sellReady,minToken,tradeAmount,myTruncate,protection,res_ema,res_rsi,res_stoch_rsi)

  if bench_mode == True :
    fx.backtest_strategy(df)
