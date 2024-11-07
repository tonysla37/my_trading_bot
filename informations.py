import logging
import matplotlib.pyplot as plt
import pandas as pd
import ta

from binance.client import Client
from math import floor

import indicators as indic

def prepare_data(df):
    """
    Prépare les données en calculant les indicateurs techniques.

    Args:
        df (pd.DataFrame): DataFrame contenant les données de trading.

    Returns:
        pd.DataFrame: DataFrame enrichi avec les indicateurs techniques.
    """
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
        for window in [7, 30, 50, 100, 150, 200]:
            df[f'ema{window}'] = ta.trend.EMAIndicator(close=df['close'], window=window).ema_indicator()

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

        logging.info("Indicateurs techniques calculés avec succès")
        return df
    except Exception as e:
        logging.error(f"Erreur lors de la préparation des données : {e}")
        return df

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

# Fonction pour calculer la différence entre la valeur future attendue et la valeur calculée
def func_diff(r, PV, C, FV, n_months):
    if r <= 0:
        return float('inf')  # Renvoie l'infini pour éviter des calculs avec r <= 0
    try:
        future_value = PV * (1 + r)**n_months + C * (((1 + r)**n_months - 1) / r)
        return future_value - FV
    except OverflowError:
        return float('inf')  # En cas de débordement, renvoyer l'infini

# Recherche binaire pour trouver le r
def find_rate(PV, C, FV, n_months, low, high, tolerance=1e-6):
    while (high - low) > tolerance:
        mid = (low + high) / 2
        if func_diff(mid, PV, C, FV, n_months) < 0:
            low = mid
        else:
            high = mid
    return (low + high) / 2

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

    # Initial bounds for r
    initial_low = 0.0001  # 0.01% par mois
    initial_high = 0.10    # 10% par mois

    # Trouver r qui satisfait la condition
    r_needed = find_rate(PV, C, FV, n_months, initial_low, initial_high)

    # Affichage du taux de croissance nécessaire
    if r_needed > 0:
        ca_percentage = r_needed * 100
    else:
        ca_percentage = "negatif"

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