import datetime
import logging
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

import indicators as indic
import trade as trade
import influx_utils as idb

# Configuration de la journalisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("backtest.log"),
        logging.StreamHandler()
    ]
)

# influx_utils.test_write()

def backtest_strategy(fiatAmount, cryptoAmount, values):
    logging.info("Début du backtest.")
    bt_df = values.copy()
    bt_dt = pd.DataFrame(columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])

    # Initialisation des variables
    bt_usdt = fiatAmount
    bt_initial_wallet = bt_usdt
    bt_coin = cryptoAmount
    bt_wallet = fiatAmount
    bt_previous_row = bt_df.iloc[0]
    bt_last_ath = 0.0
    bt_maker_fee = 0.0003
    bt_taker_fee = 0.0007
    bt_buy_ready = True
    bt_sell_ready = True

    logging.info(f"Solde initial : {bt_usdt} USD, Cryptomonnaie initiale : {bt_coin} coins")

    for bt_index, bt_row in bt_df.iterrows():
        bt_res_ema = indic.analyse_ema([
            bt_row['ema7'], bt_row['ema30'], bt_row['ema50'],
            bt_row['ema100'], bt_row['ema150'], bt_row['ema200']
        ])
        bt_res_rsi = indic.analyse_rsi(rsi=bt_row['rsi'], prev_rsi=bt_previous_row.get('rsi', 50))
        bt_res_stoch_rsi = indic.analyse_stoch_rsi(
            blue=bt_row['stochastic'], 
            orange=bt_row['stoch_signal'],
            prev_blue=bt_previous_row.get('stochastic', 0),
            prev_orange=bt_previous_row.get('stoch_signal', 0)
        )

        # Condition d'achat
        if trade.buy_condition(bt_row, bt_previous_row) and bt_usdt > 0 and bt_buy_ready:
            bt_buy_price = bt_row['close']
            bt_stop_loss = bt_buy_price - 0.02 * bt_buy_price
            bt_take_profit = bt_buy_price + 0.1 * bt_buy_price
            bt_coin = bt_usdt / bt_buy_price
            bt_fee = bt_taker_fee * bt_coin
            bt_coin -= bt_fee
            bt_usdt = 0.0
            bt_wallet = bt_coin * bt_row['close']
            bt_last_ath = max(bt_wallet, bt_last_ath)

            logging.info(f"Achat exécuté le {bt_index} à {bt_buy_price} USD, Solde après frais : {bt_wallet} USD")

            bt_myrow = pd.DataFrame([[
                bt_index, "Buy", "Buy Market", bt_buy_price,
                bt_fee * bt_row['close'], bt_usdt, bt_coin, bt_wallet,
                (bt_wallet - bt_last_ath) / bt_last_ath if bt_last_ath != 0 else 0
            ]], columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])

            bt_dt = pd.concat([bt_dt, bt_myrow], ignore_index=True)

            # Écrire dans InfluxDB après l'achat
            idb.write_to_influx(
                measurement="trades",
                tags={"type": "buy"},
                fields={
                    "price": float(bt_buy_price),
                    "wallet": float(bt_wallet),
                    "fiat_amount": float(bt_usdt),
                    "crypto_amount": float(bt_coin),
                    "close": float(bt_row['close'])
                },
                timestamp=pd.to_datetime(bt_index).timestamp() * 1e9
                # timestamp=int(datetime.datetime.now().timestamp() * 1e9)
            )

        # Vente de marché
        elif trade.sell_condition(bt_row, bt_previous_row):
            if bt_coin > 0 and bt_sell_ready:
                bt_sell_price = bt_row['close']
                bt_usdt = bt_coin * bt_sell_price
                bt_fee = bt_taker_fee * bt_usdt
                bt_usdt -= bt_fee
                bt_coin = 0.0
                bt_wallet = bt_usdt
                bt_last_ath = max(bt_wallet, bt_last_ath)

                logging.info(f"Vente exécutée le {bt_index} à {bt_sell_price} USD, Solde après frais : {bt_wallet} USD")

                bt_myrow = pd.DataFrame([[
                    bt_index, "Sell", "Sell Market", bt_sell_price,
                    bt_fee, bt_usdt, bt_coin, bt_wallet,
                    (bt_wallet - bt_last_ath) / bt_last_ath if bt_last_ath != 0 else 0
                ]], columns=['date', 'position', 'reason', 'price', 'frais', 'fiat', 'coins', 'wallet', 'drawBack'])
                bt_dt = pd.concat([bt_dt, bt_myrow], ignore_index=True)
                bt_buy_ready = True
                bt_sell_ready = False

                # Écrire dans InfluxDB après la vente
                idb.write_to_influx(
                    measurement="trades",
                    tags={"type": "sell"},
                    fields={
                        "price": float(bt_sell_price),
                        "wallet": float(bt_wallet),
                        "fiat_amount": float(bt_usdt),
                        "crypto_amount": float(bt_coin),
                        "close": float(bt_row['close'])
                    },
                    timestamp=pd.to_datetime(bt_index).timestamp() * 1e9
                    # timestamp=int(datetime.datetime.now().timestamp() * 1e9)
                )

        bt_previous_row = bt_row

    # Résumé du backtest
    logging.info("Résumé du backtest.")
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
    logging.info(f"#############################################################")
    return bt_dt

if __name__ == "__main__":
    # Exemple fictif de DataFrame
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'close': np.random.random(100) * 100,
        'high': np.random.random(100) * 100,
        'low': np.random.random(100) * 100,
        'ema7': np.random.random(100) * 100,
        'ema30': np.random.random(100) * 100,
        'ema50': np.random.random(100) * 100,
        'ema100': np.random.random(100) * 100,
        'ema150': np.random.random(100) * 100,
        'ema200': np.random.random(100) * 100,
        'rsi': np.random.random(100) * 100,
        'stochastic': np.random.random(100),
        'stoch_signal': np.random.random(100)
    }, index=dates)

    # Calcul des indicateurs supplémentaires si nécessaire
    data['chop'] = indic.get_chop(data['high'], data['low'], data['close'])

    # Exécution du backtest
    backtest_result = backtest_strategy(10000, 0, data)