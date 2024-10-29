import os
import aiohttp
import asyncio

import time
import json
import logging
import requests
import datetime
from math import floor

import pandas as pd
import numpy
import pandas_ta as pta
import matplotlib.pyplot as plt
import ta
import krakenex
from pykrakenapi import KrakenAPI
from termcolor import colored
# from discord import Webhook
# from discord import RequestsWebhookAdapter

# Configuration de la journalisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)

# Configuration des clés API et des URLs (à sécuriser via des variables d'environnement)
API_KEY = os.getenv('KRAKEN_API_KEY')
API_SECRET = os.getenv('KRAKEN_API_SECRET')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Initialisation de l'API Kraken
api = krakenex.API(key=API_KEY, secret=API_SECRET)
kraken_api = KrakenAPI(api)


async def send_webhook_message(webhook_url, content):
    async with aiohttp.ClientSession() as session:
        data = {
            'content': content
        }
        async with session.post(webhook_url, json=data) as response:
            if response.status == 204:
                print("Message sent successfully!")
            else:
                print(f"Failed to send message: {response.status} - {await response.text()}")


# Fonction pour définir le niveau de risque
def define_risk(risk_level):
    risques = {"Low": 0.01, "Mid": 0.02, "Max": 0.03}
    return risques.get(risk_level, 0.01)  # Valeur par défaut : 0.01

# Fonction pour obtenir le solde d'une crypto
def get_balance(client, coin):
    try:
        json_balance = client.get_balances()
        if not json_balance:
            return 0.0
        df_balance = pd.DataFrame(json_balance)
        logging.debug(f"Balance DataFrame:\n{df_balance}")
        balance = df_balance.loc[df_balance['coin'] == coin, 'total']
        return float(balance.values[0]) if not balance.empty else 0.0
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du solde pour {coin}: {e}")
        return 0.0

# Fonction pour tronquer un nombre à un certain nombre de décimales
def truncate(n, decimals=0):
    return floor(float(n) * 10**decimals) / 10**decimals

# Indicateur Choppiness
# def get_chop(high, low, close, window=14):
#     tr = ta.volatility.TrueRange(high, low, close)
#     atr = tr.rolling(window).mean()
#     high_high = high.rolling(window).max()
#     low_low = low.rolling(window).min()
#     chop = 100 * numpy.log10((atr.rolling(window).sum()) / (high_high - low_low)) / numpy.log10(window)
#     return chop.rename("CHOP")

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
    chop_serie = 100 * numpy.log10((atr.rolling(window).sum()) /
                          (highh - lowl)) / numpy.log10(window)
    return pd.Series(chop_serie, name="CHOP")

# Analyse des indicateurs techniques
def analyse_macd(macd, signal, histogram):
    if signal < 0 and histogram < 0:
        return "bearish"
    elif signal > 0 and histogram > 0:
        return "bullish"
    else:
        return "neutral"

def analyse_stoch_rsi(blue, orange, prev_blue, prev_orange):
    srsi_trend = "undefined"
    if blue <= 20 or orange <= 20:
        srsi_trend = "oversell"
    elif blue >= 80 or orange >= 80:
        srsi_trend = "overbuy"
    else:
        if blue > orange and blue > prev_blue and orange > prev_orange:
            srsi_trend = "bullish"
        elif blue < orange and blue < prev_blue and orange < prev_orange:
            srsi_trend = "bearish"
        else:
            srsi_trend = "neutral"
    return {"trend": srsi_trend, "blue": blue, "orange": orange, "prev_blue": prev_blue, "prev_orange": prev_orange}

def analyse_rsi(rsi, prev_rsi):
    rsi_trend = "undefined"
    if rsi <= 30:
        rsi_trend = "oversell"
    elif rsi >= 70:
        rsi_trend = "overbuy"
    else:
        if rsi > 50:
            if rsi > prev_rsi:
                rsi_trend = "bullish"
            elif rsi < prev_rsi:
                rsi_trend = "bearish divergence"
            else:
                rsi_trend = "neutral"
        elif rsi < 50:
            if rsi < prev_rsi:
                rsi_trend = "bearish"
            elif rsi > prev_rsi:
                rsi_trend = "bullish divergence"
            else:
                rsi_trend = "neutral"
    return {"trend": rsi_trend, "rsi": rsi, "prev_rsi": prev_rsi}

def analyse_ema(emas):
    if all(emas[i] > emas[i+1] for i in range(len(emas)-1)):
        return "bullish"
    elif emas[-1] > emas[0]:
        return "bearish"
    else:
        return "neutral"

def analyse_bollinger(high, low, average, close):
    spread_band = high - low
    spread_price = close - average
    volatility_pc = (spread_band / close) * 100
    volatility = "high" if volatility_pc > 20 else "low"

    if close > high:
        bol_trend = "overbuy"
    elif close < low:
        bol_trend = "oversell"
    else:
        bol_trend = "over_sma" if close > average else "under_sma"

    return {
        "trend": bol_trend,
        "spread_band": spread_band,
        "spread_price": spread_price,
        "volatility": volatility,
        "volatility_pc": volatility_pc
    }

def analyse_adi(adi, prev_adi):
    if adi > prev_adi:
        return "bullish"
    elif adi < prev_adi:
        return "bearish"
    else:
        return "neutral"

# Conditions d'achat et de vente
def buy_condition(row, previous_row):
    # print("Clés disponibles : ", list(row.index))
    # print("stoch_rsi : ", row.stoch_rsi)

    return (
        row['ema7'] > row['ema30'] > row['ema50'] > row['ema100'] > row['ema150'] > row['ema200']
        and row['stoch_rsi'] < 0.82
    )

def sell_condition(row, previous_row):
    return (
        row['ema200'] > row['ema7']
        and row['stoch_rsi'] > 0.2
    )

def enter_in_trade(res_ema, res_rsi, res_stoch_rsi, res_bollinger, res_macd):
    return (
        res_ema == "bullish"
        and res_rsi["trend"] == "bullish"
        and res_stoch_rsi["trend"] == "bullish"
    )

# Fonctions pour placer les ordres
def place_order(order_type, pair, volume, price=None):
    try:
        if order_type == 'buy':
            order = api.query_private('AddOrder', {
                'pair': pair,
                'type': 'buy',
                'ordertype': 'limit' if price else 'market',
                'price': price if price else '',
                'volume': volume
            })
        elif order_type == 'sell':
            order = api.query_private('AddOrder', {
                'pair': pair,
                'type': 'sell',
                'ordertype': 'limit' if price else 'market',
                'price': price if price else '',
                'volume': volume
            })
        logging.info(f"Ordre {order_type} placé : {order}")
        return order
    except Exception as e:
        logging.error(f"Erreur lors de la placement de l'ordre {order_type} : {e}")
        return None

# Fonction principale de trading
def trade_action(client, bench_mode, pair_symbol, fiat_amount, crypto_amount, values, buy_ready, sell_ready, min_token, trade_amount, my_truncate, protection, res_ema, res_rsi, res_stoch_rsi, res_bollinger, res_macd):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # webhook = Webhook.from_url(DISCORD_WEBHOOK_URL, adapter=RequestsWebhookAdapter())
    # webhook.send(f'################## TRADING ADVISOR {now} ##################')
    # webhook.send(f'ema => {res_ema}')
    # webhook.send(f'rsi => {res_rsi["trend"]}')
    # webhook.send(f'stoch_rsi => {res_stoch_rsi["trend"]}')
    # webhook.send(f'bollinger => {res_bollinger["trend"]}')
    # webhook.send(f'macd => {res_macd}')

    # Exécuter la fonction asynchrone
    asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'################## TRADING ADVISOR {now} ##################'))
    asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'ema => {res_ema}'))
    asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'rsi => {res_rsi["trend"]}'))
    asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'stoch_rsi => {res_stoch_rsi["trend"]}'))
    asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'bollinger => {res_bollinger["trend"]}'))
    asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f'macd => {res_macd}'))

    # Condition d'achat
    if buy_condition(values.iloc[-2], values.iloc[-3]):
        if float(fiat_amount) > 5 and buy_ready:
            buy_price = values['close'].iloc[-1]
            quantity_buy = truncate(trade_amount, my_truncate)
            sl_level = protection["sl_level"]
            tp1_level = protection["tp1_level"]
            sl_amount = protection["sl_amount"]
            tp1_amount = protection["tp1_amount"]

            stop_loss = buy_price - sl_level * buy_price
            take_profit_1 = buy_price + tp1_level * buy_price
            sl_quantity = sl_amount * float(quantity_buy)
            tp1_quantity = tp1_amount * float(quantity_buy)
            possible_gain = (take_profit_1 - buy_price) * float(quantity_buy)
            possible_loss = (buy_price - stop_loss) * float(quantity_buy)
            R = possible_gain / possible_loss if possible_loss != 0 else 0

            if bench_mode:
                buy_order = f"Buy Order placé pour la quantité : {quantity_buy}"
                sell_order_sl = f"SL Order placé à {stop_loss} pour la quantité : {sl_quantity}"
                sell_order_tp1 = f"TP1 Order placé à {take_profit_1} pour la quantité : {tp1_quantity}"
            else:
                buy_order = place_order('buy', pair_symbol, quantity_buy, buy_price)
                sell_order_sl = place_order('sell', pair_symbol, sl_quantity, stop_loss)
                sell_order_tp1 = place_order('sell', pair_symbol, tp1_quantity, take_profit_1)

            buy_ready = False
            sell_ready = True

            logging.info(f"Achat à {buy_price}, Stop loss à {stop_loss}, TP1 à {take_profit_1}")
            # webhook.send(f"Achat à {buy_price}")
            # webhook.send(f"Stop loss à {stop_loss}")
            # webhook.send(f"TP1 à {take_profit_1}")
            # webhook.send(f"Gain possible : {possible_gain}, Perte possible : {possible_loss}, Ratio R : {R}")
            # webhook.send(buy_order)
            # webhook.send(sell_order_sl)
            # webhook.send(sell_order_tp1)
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Achat à {buy_price}"))
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Stop loss à {stop_loss}"))
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"TP1 à {take_profit_1}"))
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Gain possible : {possible_gain}, Perte possible : {possible_loss}, Ratio R : {R}"))
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, buy_order))
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, sell_order_sl))
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, sell_order_tp1))


    # Condition de vente
    elif sell_condition(values.iloc[-2], values.iloc[-3]):
        if float(crypto_amount) > min_token and sell_ready:
            quantity_sell = truncate(crypto_amount, my_truncate)

            if bench_mode:
                sell_order = f"Sell Order placé pour la quantité : {quantity_sell}"
            else:
                sell_order = place_order('sell', pair_symbol, quantity_sell)
            
            buy_ready = True
            sell_ready = False

            logging.info(f"Vente de {quantity_sell}")
            # webhook.send(f"Vente de {quantity_sell}")
            asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, f"Vente de {quantity_sell}"))
            if sell_order:
                # webhook.send(str(sell_order))
                asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, str(sell_order)))
    else:
        logging.info("Aucune opportunité de trade")
        # webhook.send("Aucune opportunité de trade")
        asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, "Aucune opportunité de trade"))

    # webhook.send('################## FIN DU TRADING ADVISOR ##################')
    asyncio.run(send_webhook_message(DISCORD_WEBHOOK_URL, '################## FIN DU TRADING ADVISOR ##################'))

# Fonction de backtesting
def backtest_strategy(fiatAmount, cryptoAmount, values):
    bt_df = values.copy()
    bt_dt = pd.DataFrame(columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])

    # Initialisation des variables
    bt_usdt = fiatAmount
    bt_initial_wallet = bt_usdt
    bt_coin = cryptoAmount
    bt_wallet = fiatAmount
    bt_last_ath = 0.0
    bt_previous_row = bt_df.iloc[0]
    bt_maker_fee = 0.0003
    bt_taker_fee = 0.0007
    bt_stop_loss = 0.0
    bt_take_profit = 500000.0
    bt_buy_ready = True
    bt_sell_ready = True

    for bt_index, bt_row in bt_df.iterrows():
        bt_res_ema = analyse_ema([
            bt_row['ema7'], bt_row['ema30'], bt_row['ema50'],
            bt_row['ema100'], bt_row['ema150'], bt_row['ema200']
        ])
        bt_res_rsi = analyse_rsi(rsi=bt_row['rsi'], prev_rsi=bt_previous_row.get('rsi', 50))
        bt_res_stoch_rsi = analyse_stoch_rsi(
            blue=bt_row['stochastic'], 
            orange=bt_row['stoch_signal'],
            prev_blue=bt_previous_row.get('stochastic', 0),
            prev_orange=bt_previous_row.get('stoch_signal', 0)
        )

        # Condition d'achat
        if buy_condition(bt_row, bt_previous_row) and bt_usdt > 0 and bt_buy_ready:
            bt_buy_price = bt_row['close']
            bt_stop_loss = bt_buy_price - 0.02 * bt_buy_price
            bt_take_profit = bt_buy_price + 0.1 * bt_buy_price
            bt_coin = bt_usdt / bt_buy_price
            bt_fee = bt_taker_fee * bt_coin
            bt_coin -= bt_fee
            bt_usdt = 0.0
            bt_wallet = bt_coin * bt_row['close']
            bt_last_ath = max(bt_wallet, bt_last_ath)

            bt_myrow = pd.DataFrame([[
                bt_index, "Buy", "Buy Market", bt_buy_price,
                bt_fee * bt_row['close'], bt_usdt, bt_coin, bt_wallet,
                (bt_wallet - bt_last_ath) / bt_last_ath if bt_last_ath != 0 else 0
            ]], columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])

            # Si bt_myrow n'est pas vide ou totalement rempli de NA, concaténez-le
            if not bt_myrow.isna().all(axis=None):
                bt_dt = pd.concat([bt_dt, bt_myrow], ignore_index=True)
            else:
                logging.warning("bt_myrow est vide ou totalement rempli de NA, non concaténé.")

        # Stop Loss
        elif bt_row['low'] < bt_stop_loss and bt_coin > 0:
            bt_sell_price = bt_stop_loss
            bt_usdt = bt_coin * bt_sell_price
            bt_fee = bt_maker_fee * bt_usdt
            bt_usdt -= bt_fee
            bt_coin = 0.0
            bt_buy_ready = False
            bt_wallet = bt_usdt
            bt_last_ath = max(bt_wallet, bt_last_ath)

            bt_myrow = pd.DataFrame([[
                bt_index, "Sell", "Sell Stop Loss", bt_sell_price,
                bt_fee, bt_usdt, bt_coin, bt_wallet,
                (bt_wallet - bt_last_ath) / bt_last_ath if bt_last_ath != 0 else 0
            ]], columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])
            bt_dt = pd.concat([bt_dt, bt_myrow], ignore_index=True)

        # Take Profit
        elif bt_row['high'] > bt_take_profit and bt_coin > 0:
            bt_sell_price = bt_take_profit
            bt_usdt = bt_coin * bt_sell_price
            bt_fee = bt_maker_fee * bt_usdt
            bt_usdt -= bt_fee
            bt_coin = 0.0
            bt_buy_ready = False
            bt_wallet = bt_usdt
            bt_last_ath = max(bt_wallet, bt_last_ath)

            bt_myrow = pd.DataFrame([[
                bt_index, "Sell", "Sell Take Profit", bt_sell_price,
                bt_fee, bt_usdt, bt_coin, bt_wallet,
                (bt_wallet - bt_last_ath) / bt_last_ath if bt_last_ath != 0 else 0
            ]], columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])
            bt_dt = pd.concat([bt_dt, bt_myrow], ignore_index=True)

        # Vente de marché
        elif sell_condition(bt_row, bt_previous_row):
            if bt_coin > 0 and bt_sell_ready:
                bt_sell_price = bt_row['close']
                bt_usdt = bt_coin * bt_sell_price
                bt_fee = bt_taker_fee * bt_usdt
                bt_usdt -= bt_fee
                bt_coin = 0.0
                bt_wallet = bt_usdt
                bt_last_ath = max(bt_wallet, bt_last_ath)

                bt_myrow = pd.DataFrame([[
                    bt_index, "Sell", "Sell Market", bt_sell_price,
                    bt_fee, bt_usdt, bt_coin, bt_wallet,
                    (bt_wallet - bt_last_ath) / bt_last_ath if bt_last_ath != 0 else 0
                ]], columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])
                bt_dt = pd.concat([bt_dt, bt_myrow], ignore_index=True)
                bt_buy_ready = True
                bt_sell_ready = False

        bt_previous_row = bt_row

    # Résumé du backtest
    logging.info(f"Période : [{bt_df.index[0]}] -> [{bt_df.index[-1]}]")
    bt_dt.set_index('date', inplace=True)
    bt_dt.index = pd.to_datetime(bt_dt.index)
    bt_dt['resultat'] = bt_dt['wallet'].diff()
    bt_dt['resultat%'] = bt_dt['wallet'].pct_change() * 100
    bt_dt.loc[bt_dt['position'] == 'Buy', ['resultat', 'resultat%']] = None

    bt_dt['tradeIs'] = bt_dt['resultat%'].apply(lambda x: 'Good' if x > 0 else ('Bad' if x <= 0 else ''))
    
    bt_initial_close = bt_df.iloc[0]['close']
    bt_last_close = bt_df.iloc[-1]['close']
    bt_hold_percentage = ((bt_last_close - bt_initial_close) / bt_initial_close) * 100
    bt_algo_percentage = ((bt_wallet - bt_initial_wallet) / bt_initial_wallet) * 100
    bt_vs_hold_percentage = ((bt_algo_percentage - bt_hold_percentage) / bt_hold_percentage) * 100 if bt_hold_percentage != 0 else 0

    logging.info(f"Solde initial : {str(fiatAmount)}$")
    logging.info(f"Solde final : {round(bt_wallet, 2)}$")
    logging.info(f"Performance vs US Dollar : {round(bt_algo_percentage, 2)}%")
    logging.info(f"Performance Buy and Hold : {round(bt_hold_percentage, 2)}%")
    logging.info(f"Performance vs Buy and Hold : {round(bt_vs_hold_percentage, 2)}%")
    logging.info(f"Nombre de trades négatifs : {bt_dt['tradeIs'].value_counts().get('Bad', 0)}")
    logging.info(f"Nombre de trades positifs : {bt_dt['tradeIs'].value_counts().get('Good', 0)}")
    logging.info(f"Trades positifs moyens : {round(bt_dt.loc[bt_dt['tradeIs'] == 'Good', 'resultat%'].mean(), 2)}%")
    logging.info(f"Trades négatifs moyens : {round(bt_dt.loc[bt_dt['tradeIs'] == 'Bad', 'resultat%'].mean(), 2)}%")

    # Modifiez ces lignes dans votre fonction de backtesting
    # Vérifiez que la date est récupérée depuis l'index
    if not bt_dt.loc[bt_dt['tradeIs'] == 'Good', 'resultat%'].empty:
        bt_id_best = bt_dt.loc[bt_dt['tradeIs'] == 'Good', 'resultat%'].idxmax()
        logging.info(f"Meilleur trade : +{round(bt_dt.loc[bt_id_best, 'resultat%'], 2)}% le {bt_id_best}")

    if not bt_dt.loc[bt_dt['tradeIs'] == 'Bad', 'resultat%'].empty:
        bt_id_worst = bt_dt.loc[bt_dt['tradeIs'] == 'Bad', 'resultat%'].idxmin()
        logging.info(f"Pire trade : {round(bt_dt.loc[bt_id_worst, 'resultat%'], 2)}% le {bt_id_worst}")

    logging.info(f"Pire drawBack : {round(bt_dt['drawBack'].min() * 100, 2)}%")
    logging.info(f"Total des frais : {round(bt_dt['frais'].sum(), 2)}$")
    
    bt_reasons = bt_dt['reason'].unique()
    for r in bt_reasons:
        count = bt_dt['reason'].value_counts().get(r, 0)
        logging.info(f"Nombre de '{r}' : {count}")
    
    bt_dt[['wallet', 'price']].plot(subplots=True, figsize=(20, 10))
    plt.show()
    logging.info('Backtest terminé')
    return bt_dt

# Exemple d'utilisation (à adapter selon vos besoins)
if __name__ == "__main__":
    # Charger les données de trading (par exemple depuis un fichier CSV)
    # data = pd.read_csv('path_to_your_data.csv', parse_dates=['date'], index_col='date')

    # Exemple fictif de DataFrame
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'close': numpy.random.random(100) * 100,
        'high': numpy.random.random(100) * 100,
        'low': numpy.random.random(100) * 100,
        'ema7': numpy.random.random(100) * 100,
        'ema30': numpy.random.random(100) * 100,
        'ema50': numpy.random.random(100) * 100,
        'ema100': numpy.random.random(100) * 100,
        'ema150': numpy.random.random(100) * 100,
        'ema200': numpy.random.random(100) * 100,
        'rsi': numpy.random.random(100) * 100,
        'stochastic': numpy.random.random(100),
        'stoch_signal': numpy.random.random(100)
    }, index=dates)

    # Calcul des indicateurs supplémentaires si nécessaire
    data['chop'] = get_chop(data['high'], data['low'], data['close'])

    # Exécution du backtest
    backtest_result = backtest_strategy(data)

def calculate_rendement(capital, cible, temps, dca):
    PV = capital
    FV = cible
    n = temps
    C = dca

    r_yearly = (FV / PV)**(1 / n) - 1
    r_monthly = (1 + r_yearly)**(1 / 12) - 1
    # r_daily = (FV / PV)**(1 / (n * 365)) - 1
    r_daily = (1 + r_yearly)**(1 / 365) - 1
    
    year_percentage = r_yearly * 100
    monthly_percentage = r_monthly * 100
    daily_percentage = r_daily * 100


    # Calcul de la valeur future
    n_months = n * 12
    dca_value = PV * (1 + r_monthly)**n_months + C * (((1 + r_monthly)**n_months - 1) / r_monthly)
    dca_year = dca * 12
    dca_total = dca_year * n
    capital_total = PV + dca_total

    r_yearly_dca = (capital_total / PV)**(1 / n) - 1
    r_monthly_dca = (1 + r_yearly_dca)**(1 / 12) - 1
    r_daily_dca = (1 + r_yearly_dca)**(1 / 365) - 1
    
    year_percentage_dca = r_yearly_dca * 100
    monthly_percentage_dca = r_monthly_dca * 100
    daily_percentage_dca = r_daily_dca * 100

    result = {}
    result['year_percentage'] = year_percentage
    result['monthly_percentage'] = monthly_percentage
    result['daily_percentage'] = daily_percentage
    result['dca_value'] = dca_value
    result['year_percentage_dca'] = year_percentage_dca
    result['monthly_percentage_dca'] = monthly_percentage_dca
    result['daily_percentage_dca'] = daily_percentage_dca

    return result