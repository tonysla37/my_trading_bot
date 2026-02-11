# CryptoTrader Bot — Documentation de l'existant (v1)

## Vue d'ensemble

Le projet est un bot de trading crypto développé en **Python** avec une interface web **Flask**. Il supporte le trading multi-timeframe sur Binance/Kraken avec 15+ indicateurs techniques, un moteur de backtesting, des notifications Discord, et un stockage métriques InfluxDB.

---

## Stack technique actuelle

| Composant | Technologie |
|-----------|------------|
| Langage | Python 3.x |
| Interface web | Flask + Bootstrap 4 |
| Exchange principal | Binance (`python-binance`) |
| Exchange secondaire | Kraken (`pykrakenapi`) |
| Indicateurs | `ta`, `pandas_ta`, `numpy`, `scipy` |
| Base de données | InfluxDB (`influxdb-client`) |
| Notifications | Discord Webhooks (`aiohttp`) |
| Configuration | YAML (`pyyaml`) |
| Containerisation | Docker |
| Données | Pandas DataFrames |

---

## Architecture actuelle

```
┌─────────────────────────────────────────────────────────────┐
│                     Interface Flask (app.py)                 │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐  │
│  │Dashboard │ │ Config   │ │   Logs    │ │Yield Calc    │  │
│  │   /      │ │ /config  │ │  /logs    │ │/calc_yield   │  │
│  └──────────┘ └──────────┘ └───────────┘ └──────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │ subprocess
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               Trading Bot (trading_bot.py)                   │
│                  Boucle principale (60s)                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              5 Stratégies Temporelles               │    │
│  │  Monthly │ Weekly │ Daily │ Intraday │ Scalping     │    │
│  │  (1M)    │ (1W)   │ (1D)  │ (1H)     │ (15min)     │    │
│  └─────────────────────────────────────────────────────┘    │
│                         │                                    │
│           ┌─────────────┼─────────────┐                     │
│           ▼             ▼             ▼                     │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐           │
│  │ indicators.py│ │ trade.py │ │informations.py│           │
│  │ 15+ indic.   │ │ Ordres   │ │ Données      │           │
│  └──────────────┘ └──────────┘ └──────────────┘           │
└──────────┬──────────────┬──────────────┬────────────────────┘
           │              │              │
    ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
    │  InfluxDB   │ │ Binance  │ │  Discord    │
    │  (métriques)│ │ / Kraken │ │  (alertes)  │
    └─────────────┘ └──────────┘ └─────────────┘
```

---

## Structure des fichiers

```
my_trading_bot/
├── app.py                    # Application Flask (interface web)
├── config.yaml               # Configuration principale
├── requirements.txt          # Dépendances Python
├── Dockerfile                # Configuration Docker
├── start_bot.sh              # Script de démarrage
├── README.md                 # Documentation basique
├── .gitignore                # Exclusions Git
├── .env                      # Variables d'environnement (non versionné)
├── trading/
│   ├── __init__.py           # Init du package
│   ├── trading_bot.py        # Boucle principale du bot
│   ├── trade.py              # Logique d'exécution des ordres
│   ├── indicators.py         # Calcul des indicateurs techniques
│   ├── informations.py       # Préparation des données & utilitaires
│   ├── backtest.py           # Moteur de backtesting
│   └── influx_utils.py       # Intégration InfluxDB
├── templates/
│   ├── index.html            # Dashboard principal
│   ├── config.html           # Éditeur de configuration
│   ├── logs.html             # Visualiseur de logs
│   └── calculate_yield.html  # Calculateur de rendement
├── static/
│   └── styles.css            # Styles CSS
└── tests/
    └── test_trading.py       # Tests unitaires (basiques)
```

---

## Indicateurs implémentés

| # | Indicateur | Description | Signaux |
|---|-----------|-------------|---------|
| 1 | **ADI** | Accumulation/Distribution Index | Bullish/Bearish + force |
| 2 | **Bollinger Bands** | Bandes de volatilité | Surachat/Survente + extrêmes |
| 3 | **EMA** | Moyennes mobiles exponentielles (5/10/20/50) | Tendance par ordonnancement |
| 4 | **Fear & Greed** | Indice de sentiment Bitcoin | 5 niveaux (0-100) |
| 5 | **MACD** | Convergence/Divergence MM | Crossovers + divergences |
| 6 | **RSI** | Relative Strength Index | Surachat/Survente + force |
| 7 | **SMA** | Moyennes mobiles simples (50/200) | Golden/Death Cross |
| 8 | **Stochastic RSI** | RSI stochastique | Surachat/Survente + divergence |
| 9 | **Support/Résistance** | Niveaux dynamiques | Prix vs niveaux |
| 10 | **Volume** | Analyse volumétrique | Tendance + activité baleines |
| 11 | **Fibonacci** | Retracements de Fibonacci | Niveaux clés + extensions |
| 12 | **Google Trends** | Tendance Google Bitcoin | Croissant/Décroissant |
| 13 | **CHOP** | Choppiness Index | Consolidation/Tendance |

---

## Gestion des risques (existant)

### Position Sizing
```
Taille position = Capital × Ratio risque ÷ Niveau Stop-Loss
```

### Niveaux de risque
| Niveau | Ratio | Description |
|--------|-------|-------------|
| Low | 1% du capital | Conservateur |
| Mid | 2% du capital | Modéré |
| Max | 3% du capital | Agressif |

### Protections
- **Stop-Loss** : 2% sous le prix d'entrée (configurable)
- **Take-Profit** : 10% au-dessus du prix d'entrée (configurable)
- **Ratio R/R** : Calculé pour chaque trade (Gain potentiel / Perte potentielle)
- **Solde minimum** : $5 requis pour trader

---

## Configuration (`config.yaml`)

```yaml
trading:
  backtest: true           # Mode backtesting
  bench_mode: true         # Mode simulation (pas d'ordres réels)
  buy_ready: true          # Autoriser les achats
  sell_ready: true         # Autoriser les ventes
  capital: 1000            # Capital initial ($)
  cible: 200000            # Objectif de capital ($)
  crypto_symbol: BTC       # Crypto tradée
  fiat_symbol: USD         # Devise de base
  pair_symbol: BTCUSDT     # Paire de trading
  risk_level: Max          # Niveau de risque
  dca: 100                 # Montant DCA ($)
  my_truncate: 5           # Précision décimale
  temps: 5                 # Période (années)
  protection:
    sl_amount: 1           # Ratio quantité SL
    sl_level: 0.02         # Pourcentage SL (2%)
    tp1_amount: 1          # Ratio quantité TP
    tp1_level: 0.1         # Pourcentage TP (10%)
```

---

## Flux de données actuel

```
Binance API ──► gather_datas() ──► OHLCV DataFrame
                                        │
                    ┌───────────────────┘
                    ▼
              prepare_data()          ──► DataFrame enrichi (15+ colonnes)
                    │
                    ▼
              run_analysis()          ──► Dictionnaire d'analyses
                    │                     {indicateur: {trend, signal, force...}}
                    ▼
              trade_action()          ──► Décision Buy/Sell/Hold
                    │
            ┌───────┼───────┐
            ▼       ▼       ▼
         InfluxDB Discord  Exchange
         (logs)  (alertes) (ordres)
```

---

## Points forts de l'existant

1. **Multi-timeframe** : 5 temporalités simultanées
2. **Indicateurs riches** : 15+ indicateurs techniques
3. **Backtesting** : Simulation complète sur données historiques
4. **Multi-exchange** : Binance + Kraken supportés
5. **Monitoring** : InfluxDB + Discord + Logs
6. **Interface web** : Dashboard de contrôle Flask
7. **Configuration dynamique** : YAML + UI de configuration
8. **Docker** : Prêt pour le déploiement conteneurisé

---

## Limitations identifiées

| # | Limitation | Impact | Priorité |
|---|-----------|--------|----------|
| 1 | Architecture monolithique | Difficile à maintenir/étendre | Haute |
| 2 | Pas de séparation bot sécuritaire/agressif | Impossible de moduler le risque par stratégie | Haute |
| 3 | Pas de réallocation automatique des gains | Pas de gestion de portefeuille globale | Haute |
| 4 | Webhook Discord hardcodé | Sécurité faible | Moyenne |
| 5 | Pas de persistance d'état | Perte d'état au redémarrage | Haute |
| 6 | Un seul pair à la fois | Diversification impossible | Moyenne |
| 7 | Tests unitaires minimaux | Fiabilité non garantie | Haute |
| 8 | Pas de gestion des frais/slippage en backtest | Résultats de backtest optimistes | Moyenne |
| 9 | Pas d'authentification sur l'interface web | Sécurité faible | Haute |
| 10 | Variables globales pour l'état des trades | Race conditions possibles | Haute |
| 11 | Error handling limité | Crashes silencieux possibles | Moyenne |
| 12 | Interface Flask basique (pas mobile-friendly) | UX limitée | Moyenne |
