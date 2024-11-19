import logging
import matplotlib.pyplot as plt
import pandas as pd
import ta
import requests

from binance.client import Client
from math import floor
from bs4 import BeautifulSoup

import indicators as indic

def get_bitcoin_fear_and_greed_index():
    url = "https://alternative.me/crypto/fear-and-greed-index/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Trouver la section qui contient l'indice
    index_value = soup.find("div", class_="fng-circle").text.strip()
    return index_value

def prepare_data(df):
    """
    Prépare les données en calculant les indicateurs techniques.

    Args:
        df (pd.DataFrame): DataFrame contenant les données de trading.

    Returns:
        pd.DataFrame: DataFrame enrichi avec les indicateurs techniques.
    """
    logging.info("Traitement des données récupérées.")
    try:
        # Calcul des indicateurs techniques
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()

        # Assurez-vous que les colonnes nécessaires existent ('low', 'high', 'close')
        df['stoch_rsi'] = ta.momentum.stochrsi(close=df['close'], window=14, smooth1=3, smooth2=3)

        # Optionnellement, calculez les lignes de signal pour une meilleure interprétation
        df['stoch_rsi_k'] = ta.momentum.stochrsi_k(close=df['close'], window=14, smooth1=3, smooth2=3)
        df['stoch_rsi_d'] = ta.momentum.stochrsi_d(close=df['close'], window=14, smooth1=3, smooth2=3)
        
        stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
        df['stochastic'] = stoch.stoch()
        df['stoch_signal'] = stoch.stoch_signal()

        macd = ta.trend.MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histo'] = macd.macd_diff()

        df['awesome_oscillador'] = ta.momentum.AwesomeOscillatorIndicator(high=df['high'], low=df['low'], window1=5, window2=34).awesome_oscillator()

        # Moyennes mobiles exponentielles
        # for window in [7, 30, 50, 100, 150, 200]:
        for window in [5, 10, 20, 50]:
            df[f'ema{window}'] = ta.trend.EMAIndicator(close=df['close'], window=window).ema_indicator()

        for window in [50, 200]:
            df[f'sma{window}'] = ta.trend.SMAIndicator(close=df['close'], window=window).sma_indicator()

        # Bandes de Bollinger
        bollinger = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bol_high'] = bollinger.bollinger_hband()
        df['bol_low'] = bollinger.bollinger_lband()
        df['bol_medium'] = bollinger.bollinger_mavg()
        df['bol_gap'] = bollinger.bollinger_wband()
        df['bol_higher'] = bollinger.bollinger_hband_indicator()
        df['bol_lower'] = bollinger.bollinger_lband_indicator()

        # Indicateur Choppiness
        df['chop'] = indic.get_chop(high=df['high'], low=df['low'], close=df['close'], window=14)

        # Indicateur ADI
        df['adi'] = ta.volume.acc_dist_index(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'])

        period = 20  # Zones sur 20 périodes, ajustez selon besoin
    
        # Calculer les niveaux de résistance et de support
        df['Resistance'] = df['close'].rolling(window=period).max().shift(1)  # Plus haut des 20 périodes précédentes
        df['Support'] = df['close'].rolling(window=period).min().shift(1)  # Plus bas des 20 périodes précédentes    

        logging.info("Indicateurs techniques calculés avec succès.")
        return df
    except Exception as e:
        logging.error(f"Erreur lors de la préparation des données : {e}")
        return df

def define_risk(risk_level):
    risques = {"Low": 0.01, "Mid": 0.02, "Max": 0.03}
    risk_value = risques.get(risk_level, 0.01)
    logging.info(f"Niveau de risque défini pour {risk_level}: {risk_value}")
    return risk_value

def get_balance(client, coin):
    try:
        json_balance = client.get_balances()
        if not json_balance:
            logging.warning(f"Aucune donnée de solde disponible pour {coin}.")
            return 0.0
        df_balance = pd.DataFrame(json_balance)
        logging.debug(f"Balance DataFrame:\n{df_balance}")
        balance = df_balance.loc[df_balance['coin'] == coin, 'total']
        balance_value = float(balance.values[0]) if not balance.empty else 0.0
        logging.info(f"Solde pour {coin}: {balance_value}")
        return balance_value
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du solde pour {coin}: {e}")
        return 0.0

def truncate(n, decimals=0):
    truncated_value = floor(float(n) * 10**decimals) / 10**decimals
    logging.debug(f"Valeur tronquée: {truncated_value}")
    return truncated_value

def func_diff(r, PV, C, FV, n_months):
    if r <= 0:
        return float('inf')
    try:
        future_value = PV * (1 + r)**n_months + C * (((1 + r)**n_months - 1) / r)
        return future_value - FV
    except OverflowError:
        return float('inf')

def find_rate(PV, C, FV, n_months, low, high, tolerance=1e-6):
    while (high - low) > tolerance:
        mid = (low + high) / 2
        if func_diff(mid, PV, C, FV, n_months) < 0:
            low = mid
        else:
            high = mid
    logging.debug(f"Taux trouvé : {(low + high) / 2}")
    return (low + high) / 2

def calculate_rendement(capital, cible, temps, dca):
    PV = capital
    FV = cible
    n = temps
    C = dca

    r_yearly = (FV / PV)**(1 / n) - 1
    r_monthly = (1 + r_yearly)**(1 / 12) - 1
    r_daily = (1 + r_yearly)**(1 / 365) - 1
    
    year_percentage = r_yearly * 100
    monthly_percentage = r_monthly * 100
    daily_percentage = r_daily * 100

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

    initial_low = 0.0001
    initial_high = 0.10

    r_needed = find_rate(PV, C, FV, n_months, initial_low, initial_high)

    if r_needed > 0:
        ca_percentage = r_needed * 100
    else:
        ca_percentage = "negatif"

    logging.info(f"#############################################################")
    logging.info(f"Le capital de départ {capital:.2f}€")
    logging.info(f"Le capital cible {cible:.2f}%")
    logging.info(f"L'horizon de placement {temps:.2f} an(s)")
    logging.info(f"Le montant d'investiment mensuel {dca:.2f}€")
    logging.info(f"#############################################################")
    logging.info(f"Rendement calculé : Annuel {year_percentage}%, Mensuel {monthly_percentage}%, Journalier {daily_percentage}%")
    logging.info(f"Rendement avec DCA : Annuel {year_percentage_dca}%, Mensuel {monthly_percentage_dca}%, Journalier {daily_percentage_dca}%")
    logging.info(f"Croissance annuelle nécessaire pour atteindre {FV}: {ca_percentage}%")
    logging.info(f"La valeur future de l'investissement avec des contributions mensuelles est d'environ {dca_value}€")

    result = {}
    result['year_percentage'] = year_percentage
    result['monthly_percentage'] = monthly_percentage
    result['daily_percentage'] = daily_percentage
    result['dca_value'] = dca_value
    result['year_percentage_dca'] = year_percentage_dca
    result['monthly_percentage_dca'] = monthly_percentage_dca
    result['daily_percentage_dca'] = daily_percentage_dca
    result['ca_percentage'] = ca_percentage

    return result

