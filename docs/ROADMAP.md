# CryptoTrader Bot — Roadmap & Plan d'Actions

---

## Vue d'ensemble de la migration

```
Phase 0:  Préparation                           [Semaines 1-2]
Phase 1:  Refactoring Backend                    [Semaines 2-5]
Phase 2:  Système de Bots & Profils de risque    [Semaines 5-7]
Phase 2b: Bots Spécialistes & Régime de Marché   [Semaines 7-9]
Phase 3:  API FastAPI                            [Semaines 9-11]
Phase 4:  Bot Discord v2                         [Semaines 11-12]
Phase 5:  Application React Native               [Semaines 12-16]
Phase 6:  Backtesting Avancé                     [Semaines 16-18]
Phase 7:  Déploiement & Production               [Semaines 18-20]
Phase 8:  Améliorations Continues                [En continu]
```

---

## Phase 0 — Préparation

### Actions

- [ ] **0.1** Créer la branche `legacy/v1-python-flask` pour archiver le code actuel
- [ ] **0.2** Mettre en place la structure de dossiers cible (voir `TARGET_ARCHITECTURE.md`)
- [ ] **0.3** Configurer l'environnement de développement
  - [ ] Python virtual env + requirements.txt initial
  - [ ] Node.js / Expo pour le mobile
  - [ ] Docker Compose pour les services (PostgreSQL, Redis, InfluxDB)
- [ ] **0.4** Configurer le CI/CD (GitHub Actions)
  - [ ] Workflow test Python (pytest + ruff + mypy)
  - [ ] Workflow test TypeScript (eslint + jest)
  - [ ] Workflow build Docker
- [ ] **0.5** Créer le fichier `.env.example` avec toutes les variables nécessaires
- [ ] **0.6** Mettre en place les pre-commit hooks (black, isort, ruff)

---

## Phase 1 — Refactoring Backend

### 1.1 Modèle de données

- [ ] **1.1.1** Installer et configurer SQLAlchemy + Alembic (migrations)
- [ ] **1.1.2** Créer les modèles : `Bot`, `Trade`, `TradingPair`, `Reallocation`, `OHLCVData`
- [ ] **1.1.3** Configurer TimescaleDB pour les données OHLCV (hypertable)
- [ ] **1.1.4** Écrire la migration initiale
- [ ] **1.1.5** Tests unitaires des modèles

### 1.2 Moteur d'indicateurs (Indicator Engine)

- [ ] **1.2.1** Créer la classe abstraite `BaseIndicator` avec l'interface standard
- [ ] **1.2.2** Migrer chaque indicateur existant vers une classe indépendante :
  - [ ] RSI
  - [ ] MACD
  - [ ] Bollinger Bands
  - [ ] EMA (multi-périodes)
  - [ ] SMA
  - [ ] Stochastic RSI
  - [ ] ADI
  - [ ] Volume
  - [ ] Fibonacci
  - [ ] Support/Résistance
  - [ ] Fear & Greed Index
  - [ ] Choppiness Index
  - [ ] Google Trends
- [ ] **1.2.3** Créer le `IndicatorEngine` avec le système de plugins
- [ ] **1.2.4** Implémenter le support multi-timeframe
- [ ] **1.2.5** Ajouter les poids configurables par indicateur
- [ ] **1.2.6** Tests unitaires pour chaque indicateur (données de test connues)

### 1.3 Moteur de décision (Decision Engine)

- [ ] **1.3.1** Créer la classe abstraite `BaseStrategy`
- [ ] **1.3.2** Implémenter les **profils de risque** (orthogonaux aux stratégies de marché) :
  - [ ] `ConservativeStrategy` — seuils élevés (70%+), 5+ indicateurs, position 1%
  - [ ] `AggressiveStrategy` — seuils bas (40%+), 3+ indicateurs, position 3%
- [ ] **1.3.3** Créer le `DecisionEngine` avec score pondéré
- [ ] **1.3.4** Ajouter le `MarketContext` (Fear & Greed, volume, volatilité, régime)
- [ ] **1.3.5** Tests unitaires avec scénarios de marché

### 1.4 Moteur d'ordres (Order Engine)

- [ ] **1.4.1** Créer la classe abstraite `BaseExchange`
- [ ] **1.4.2** Migrer le connecteur Binance
- [ ] **1.4.3** Migrer le connecteur Kraken
- [ ] **1.4.4** Créer le `OrderEngine` avec validation et protection
- [ ] **1.4.5** Implémenter les ordres groupés (entry + SL + TP atomiques)
- [ ] **1.4.6** Ajouter le mode simulation (bench_mode) proprement isolé
- [ ] **1.4.7** Tests unitaires avec mock exchange

### 1.5 Gestion des risques (Risk Management)

- [ ] **1.5.1** Créer le `RiskManager` centralisé
- [ ] **1.5.2** Implémenter le `RiskReducer` (réduction dynamique)
  - [ ] Détection des pertes consécutives (≥3 → ÷2, ≥5 → pause)
  - [ ] Restauration progressive (2 gains → risque +)
- [ ] **1.5.3** Position sizing avancé (Kelly Criterion en option)
- [ ] **1.5.4** Maximum drawdown protection (arrêt si DD > seuil)
- [ ] **1.5.5** Tests unitaires avec historiques de trades simulés

---

## Phase 2 — Système de Bots Dual

### Actions

- [ ] **2.1** Créer la classe `TradingBot` encapsulant un moteur complet
  - [ ] Configuration propre (stratégie, risque, capital, paire)
  - [ ] Cycle de vie : start / stop / pause / resume
  - [ ] État persisté en BDD
- [ ] **2.2** Créer le `PortfolioManager`
  - [ ] Gestion de 2+ bots simultanés
  - [ ] Allocation initiale du capital (70/30 configurable)
  - [ ] Tracking P&L par bot
- [ ] **2.3** Implémenter la réallocation automatique
  - [ ] Ratio configurable (10% → 50% des gains)
  - [ ] Déclenchement après chaque trade gagnant du bot agressif
  - [ ] Historique des réallocations en BDD
- [ ] **2.4** Implémenter la réduction de risque inter-bots
  - [ ] Si les deux bots perdent → réduction globale
  - [ ] Dashboard de suivi des ajustements
- [ ] **2.5** Tests d'intégration du système dual

---

## Phase 2b — Bots Spécialistes par Régime de Marché

### 2b.1 Market Regime Detector (Détecteur de régime)

- [ ] **2b.1.1** Créer la classe `MarketRegimeDetector`
- [ ] **2b.1.2** Implémenter la détection des 4 régimes :
  - [ ] **BULL** : ADX > 25 + EMA20 > EMA50 + MACD positif + Higher Highs/Higher Lows
  - [ ] **BEAR** : ADX > 25 + EMA20 < EMA50 + MACD négatif + Lower Highs/Lower Lows
  - [ ] **RANGING** : ADX < 25 OU Choppiness > 61.8 + prix oscille dans un range S/R
  - [ ] **TRANSITION** : signaux contradictoires, régime précédent en train de changer
- [ ] **2b.1.3** Implémenter le score de confiance du régime (0.0 - 1.0)
- [ ] **2b.1.4** Ajouter le compteur de durée du régime (nombre de bougies)
- [ ] **2b.1.5** Implémenter la confirmation (N bougies consécutives avant changement)
- [ ] **2b.1.6** Ajouter l'indicateur **ADX** (Average Directional Index) s'il n'est pas déjà présent
- [ ] **2b.1.7** Tests unitaires avec données historiques connues (bull run 2021, bear 2022, range Q1 2023)

### 2b.2 Bot spécialiste Bull Market

- [ ] **2b.2.1** Implémenter `BullMarketStrategy`
  - [ ] Achat sur pullbacks : rebond sur EMA20/EMA50
  - [ ] Achat sur retracements Fibonacci (38.2%, 50%, 61.8%)
  - [ ] Achat sur support dynamique (support/résistance)
  - [ ] Vente aux résistances identifiées
  - [ ] Trailing Stop-Loss (suit le prix à la hausse)
- [ ] **2b.2.2** Indicateurs prioritaires : EMA, Fibonacci, Support/Résistance, MACD, Volume
- [ ] **2b.2.3** Position sizing : 100% du sizing normal (confiance élevée en tendance)
- [ ] **2b.2.4** Tests avec données de bull market (ex: BTC oct 2020 → avr 2021)

### 2b.3 Bot spécialiste Bear Market

- [ ] **2b.3.1** Implémenter `BearMarketStrategy`
  - [ ] Achat uniquement sur survente extrême (RSI < 20, Extreme Fear)
  - [ ] Take-profit rapide (3-5%, pas d'optimisme en bear)
  - [ ] Stop-loss serré (1-1.5%)
  - [ ] Position sizing réduit à 50% (environnement hostile)
  - [ ] Optionnel : support du short selling via futures
- [ ] **2b.3.2** Indicateurs prioritaires : RSI, Bollinger Bands, Volume (capitulation), Fear & Greed
- [ ] **2b.3.3** Mode défensif : minimum 4 indicateurs de survente extrême avant d'acheter
- [ ] **2b.3.4** Tests avec données de bear market (ex: BTC nov 2021 → juin 2022)

### 2b.4 Bot spécialiste Range / Latéralisation

- [ ] **2b.4.1** Implémenter `RangeStrategy`
  - [ ] Détection automatique du range (support/résistance horizontaux)
  - [ ] Achat quand le prix touche le bas du range + RSI/StochRSI en survente
  - [ ] Vente quand le prix touche le haut du range + RSI/StochRSI en surachat
  - [ ] Stop-loss juste sous le range bas (-2%)
  - [ ] Take-profit au haut du range
  - [ ] Buffer de 2% aux bornes (ne pas acheter/vendre pile sur la borne)
- [ ] **2b.4.2** Implémenter `detect_range()` : identification automatique des bornes
- [ ] **2b.4.3** Indicateurs prioritaires : Bollinger, RSI, Stochastic RSI, Support/Résistance, Choppiness
- [ ] **2b.4.4** Gestion du breakout : si le prix sort du range → alerte + arrêt du Range Bot
- [ ] **2b.4.5** Tests avec données de range (ex: BTC juil-sept 2023)

### 2b.5 Orchestration & Transitions

- [ ] **2b.5.1** Intégrer le `MarketRegimeDetector` dans le `PortfolioManager`
- [ ] **2b.5.2** Implémenter la logique de transition entre régimes :
  - [ ] BULL → BEAR : Bull Bot ferme progressivement → période tampon → Bear Bot s'active
  - [ ] BULL → RANGING : Bull Bot ferme → Range Bot détecte les bornes → s'active
  - [ ] RANGING → BULL : Range Bot ferme → Bull Bot s'active
  - [ ] Tout → TRANSITION : mode prudent, positions réduites 50%, pas de nouveaux trades
- [ ] **2b.5.3** Implémenter le mode "exit only" pour les bots en cours de désactivation
- [ ] **2b.5.4** Notifications Discord de changement de régime (avec détails)
- [ ] **2b.5.5** Stocker l'historique des régimes en BDD (`market_regimes` table)
- [ ] **2b.5.6** Tests d'intégration : simulation de changements de régime sur données réelles

---

## Phase 3 — API FastAPI

### Actions

- [ ] **3.1** Initialiser FastAPI avec la structure de routes
- [ ] **3.2** Implémenter l'authentification JWT
  - [ ] Login / Register / Refresh
  - [ ] Middleware d'authentification
  - [ ] Gestion des permissions
- [ ] **3.3** Routes Bots : CRUD + start/stop/pause
- [ ] **3.4** Routes Trades : historique, positions ouvertes, détails
- [ ] **3.5** Routes Backtest : lancement, résultats, comparaison
- [ ] **3.6** Routes Config : lecture/écriture de la configuration
- [ ] **3.7** WebSocket endpoints
  - [ ] `/ws/trades` : trades temps réel
  - [ ] `/ws/indicators` : indicateurs temps réel
  - [ ] `/ws/portfolio` : état du portefeuille
- [ ] **3.8** Rate limiting (Redis)
- [ ] **3.9** CORS configuré
- [ ] **3.10** Documentation OpenAPI automatique
- [ ] **3.11** Tests d'intégration API

---

## Phase 4 — Bot Discord v2

### Actions

- [ ] **4.1** Migrer du simple webhook vers un vrai bot Discord (`discord.py`)
- [ ] **4.2** Implémenter les commandes slash
  - [ ] `/status` — résumé des bots
  - [ ] `/trades` — derniers trades
  - [ ] `/risk` — niveaux de risque
  - [ ] `/pause [bot]` — pause d'un bot
  - [ ] `/resume [bot]` — reprise d'un bot
  - [ ] `/backtest [pair]` — backtest rapide
  - [ ] `/balance` — balances des bots
  - [ ] `/config` — configuration
- [ ] **4.3** Embeds riches pour les notifications
  - [ ] Notification d'achat (avec tous les détails : SL, TP, risque, R/R)
  - [ ] Notification de vente (P&L, durée, réallocation)
  - [ ] Alerte de risque réduit
  - [ ] Résumé quotidien
- [ ] **4.4** Communication via Redis Streams (écoute des events)
- [ ] **4.5** Tests du bot Discord

---

## Phase 5 — Application React Native

### Actions

- [ ] **5.1** Initialiser le projet Expo avec TypeScript
- [ ] **5.2** Configurer Expo Router (navigation par fichiers)
- [ ] **5.3** Configurer Zustand (state management)
- [ ] **5.4** Implémenter les services API (axios/fetch)
- [ ] **5.5** Implémenter le client WebSocket
- [ ] **5.6** Écran Dashboard
  - [ ] Résumé portefeuille (capital total, P&L)
  - [ ] Cartes des bots (sécuritaire/agressif)
  - [ ] Derniers trades
  - [ ] Indicateurs clés en temps réel
- [ ] **5.7** Écran Bots
  - [ ] Liste des bots avec status
  - [ ] Start/Stop/Pause par bot
  - [ ] Détail d'un bot (performance, trades, config)
- [ ] **5.8** Écran Backtest
  - [ ] Formulaire de backtest (paire, période, stratégie)
  - [ ] Résultats avec graphiques (equity curve)
  - [ ] Comparaison de stratégies
- [ ] **5.9** Écran Settings
  - [ ] Configuration des API keys
  - [ ] Gestion des paires de trading
  - [ ] Paramètres de notification
  - [ ] Thème clair/sombre
- [ ] **5.10** Composants Charts
  - [ ] Courbe d'equity (react-native-chart-kit ou Victory Native)
  - [ ] Graphique chandelier (CandlestickChart)
  - [ ] Indicateurs visuels
- [ ] **5.11** Push notifications
- [ ] **5.12** Tests (Jest + React Native Testing Library)

---

## Phase 6 — Backtesting Avancé

### Actions

- [ ] **6.1** Refactoriser le moteur de backtest existant
- [ ] **6.2** Ajouter la prise en compte des frais et du slippage
- [ ] **6.3** Calculer les métriques avancées
  - [ ] Sharpe Ratio
  - [ ] Max Drawdown
  - [ ] Profit Factor
  - [ ] Win Rate
  - [ ] Average Win / Average Loss
- [ ] **6.4** Générer la courbe d'equity
- [ ] **6.5** Comparaison de stratégies (côte à côte)
- [ ] **6.6** Walk-forward analysis (optimisation sur période passée, test sur période suivante)
- [ ] **6.7** Monte Carlo simulation (robustesse de la stratégie)
- [ ] **6.8** Export des résultats (CSV, JSON)
- [ ] **6.9** Tests avec jeux de données historiques connus

---

## Phase 7 — Déploiement & Production

### Actions

- [ ] **7.1** Finaliser les Dockerfiles (multi-stage builds)
- [ ] **7.2** Docker Compose de production
  - [ ] Variables d'environnement production
  - [ ] Volumes persistants
  - [ ] Healthchecks
  - [ ] Restart policies
- [ ] **7.3** Configurer HTTPS (Let's Encrypt / Caddy reverse proxy)
- [ ] **7.4** Configurer Grafana dashboards
  - [ ] Dashboard Performance (P&L, trades, drawdown)
  - [ ] Dashboard Système (CPU, RAM, latence)
  - [ ] Dashboard Indicateurs (valeurs temps réel)
- [ ] **7.5** Alerting (Grafana → Discord pour les alertes système)
- [ ] **7.6** Backup automatique PostgreSQL
- [ ] **7.7** Documentation de déploiement
- [ ] **7.8** Build et publier l'app mobile (Expo EAS Build)

---

## Phase 8 — Améliorations continues

### Suggestions d'amélioration (par priorité)

#### Priorité Haute

| # | Amélioration | Description | Impact |
|---|-------------|-------------|--------|
| 1 | **Multi-paires** | Supporter plusieurs paires simultanément (BTC, ETH, SOL, etc.) | Diversification du risque |
| 2 | **Trailing Stop-Loss** | SL qui suit le prix à la hausse pour sécuriser les gains | +P&L significatif |
| 3 | **DCA automatique** | Dollar-Cost Averaging intégré dans les bots | Lissage du prix d'entrée |
| 4 | **Alertes de prix** | Alertes Discord/Push quand un prix atteint un seuil | UX |
| 5 | **Persistance d'état** | État complet sauvegardé (reprise après crash) | Fiabilité |

#### Priorité Moyenne

| # | Amélioration | Description | Impact |
|---|-------------|-------------|--------|
| 6 | **Machine Learning** | Modèle ML pour pondérer les indicateurs dynamiquement | Précision des signaux |
| 7 | **Sentiment Analysis** | Analyse Twitter/Reddit pour le sentiment de marché | Signal complémentaire |
| 8 | **Ordres OCO** | One-Cancels-Other natif sur l'exchange | Fiabilité des protections |
| 9 | **Paper Trading** | Mode simulation avancé avec données temps réel | Test sans risque |
| 10 | **Multi-exchange** | Trading simultané sur Binance + Kraken + Bybit | Arbitrage possible |

#### Priorité Basse

| # | Amélioration | Description | Impact |
|---|-------------|-------------|--------|
| 11 | **Copy Trading** | Permettre à d'autres utilisateurs de copier les trades | Monétisation |
| 12 | **Marketplace de stratégies** | Partager/vendre des stratégies | Communauté |
| 13 | **Grid Trading** | Stratégie de grille automatique | Nouvelle stratégie |
| 14 | **Futures/Leverage** | Support du trading à levier | Rendements amplifiés |
| 15 | **Widget mobile** | Widget iOS/Android avec résumé en temps réel | UX |

---

## Suggestions techniques

### Architecture

| Suggestion | Détails |
|-----------|---------|
| **Event Sourcing** | Stocker chaque événement (signal, ordre, réallocation) pour un audit trail complet. Permet de "rejouer" l'historique |
| **Circuit Breaker** | Pattern de protection contre les pannes d'exchange. Si Binance est down, basculer automatiquement sur Kraken |
| **Retry avec backoff** | Toutes les connexions externes (API exchange, Discord) avec retry exponentiel |
| **Feature Flags** | Activer/désactiver des fonctionnalités en production sans redéployer |
| **Health Checks** | Endpoint `/health` avec vérification de tous les services (DB, Redis, Exchange) |

### Performance

| Suggestion | Détails |
|-----------|---------|
| **Async partout** | Utiliser `asyncio` pour toutes les I/O (échanges, DB, Redis) |
| **Cache des indicateurs** | Redis cache pour les indicateurs déjà calculés (même timeframe) |
| **Batch processing** | Grouper les écritures en BDD par lots |
| **WebSocket streaming** | Données exchange en temps réel via WebSocket (au lieu de polling) |
| **Connection pooling** | Pool de connexions pour PostgreSQL et Redis |

### Sécurité

| Suggestion | Détails |
|-----------|---------|
| **Chiffrement API keys** | Fernet (AES-128) pour les clés stockées en BDD |
| **2FA** | Double authentification pour l'interface de pilotage |
| **IP Whitelisting** | Restreindre les API keys exchange aux IPs du serveur |
| **Audit log** | Logger toute action sensible (création d'ordre, modification de config) |
| **Rate limiting par user** | Prévenir les abus sur l'API |
| **Désactiver les retraits** | API keys exchange en mode "trade only", pas de retrait |

### Observabilité

| Suggestion | Détails |
|-----------|---------|
| **Structured logging** | JSON logging avec correlation IDs |
| **Distributed tracing** | OpenTelemetry pour tracer les requêtes à travers les services |
| **Métriques Prometheus** | Exposition de métriques pour Grafana |
| **Alerting multi-canal** | Discord + Email + Push pour les alertes critiques |

---

## Indicateurs de succès (KPIs)

### Technique
- [ ] 90%+ de couverture de tests
- [ ] < 200ms latence API (p95)
- [ ] 99.5%+ uptime
- [ ] 0 crash non géré par mois

### Trading
- [ ] Sharpe Ratio > 1.5 en backtest
- [ ] Win Rate > 55%
- [ ] Max Drawdown < 15%
- [ ] Profit Factor > 1.5
- [ ] Réallocation fonctionnelle et traçable

### UX
- [ ] App mobile fonctionnelle (iOS + Android)
- [ ] Latence WebSocket < 1s
- [ ] Notifications Discord < 5s après un trade
- [ ] Interface responsive et accessible

---

## Résumé des priorités

```
🔴 CRITIQUE (faire en premier)
├── Refactoring en classes indépendantes (indicateurs, stratégies)
├── Market Regime Detector (détection bull/bear/range)
├── 3 bots spécialistes (Bull Bot, Bear Bot, Range Bot)
├── 2 profils de risque (Safe + Aggressive) × 3 spécialistes
├── Réallocation automatique des gains (aggro → safe)
├── Orchestration des transitions de régime
├── Persistance d'état (PostgreSQL)
└── Réduction dynamique du risque

🟡 IMPORTANT (faire ensuite)
├── API FastAPI complète
├── Bot Discord v2 (commandes slash + alertes de régime)
├── Application React Native
├── Backtesting avancé (frais, metrics, par régime)
└── Tests complets (dont tests par régime avec données historiques)

🟢 NICE TO HAVE (améliorations futures)
├── Multi-paires simultanées
├── Machine Learning (pondération dynamique des indicateurs)
├── Trailing Stop-Loss (déjà intégré dans Bull Bot)
├── Sentiment Analysis
├── Backtesting comparatif des bots spécialistes par régime
└── Multi-exchange arbitrage
```
