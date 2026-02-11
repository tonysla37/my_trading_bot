# CryptoTrader Bot — Instructions du Projet

## Présentation

CryptoTrader Bot est une plateforme de trading automatisé de cryptomonnaies composée de :
- Un **backend Python** (FastAPI + moteurs de trading)
- Une **application mobile React Native** (Expo)
- Un **bot Discord** pour les alertes et le contrôle
- Deux bots de trading : **Sécuritaire** et **Agressif** avec réallocation automatique des gains

---

## Prérequis

### Système
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose
- Git

### Comptes & API Keys
- **Binance** : API Key + Secret (pour les données de marché et le trading)
- **Kraken** (optionnel) : API Key + Secret
- **Discord** : Bot Token + Webhook URL
- **InfluxDB** : Token (pour le monitoring)

---

## Installation rapide

### 1. Cloner le projet

```bash
git clone <repo-url> my_trading_bot
cd my_trading_bot
```

### 2. Configuration de l'environnement

```bash
cp .env.example .env
```

Remplir le fichier `.env` :

```env
# Exchange APIs
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_API_SECRET=your_kraken_api_secret

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/trading
REDIS_URL=redis://localhost:6379

# Discord
DISCORD_TOKEN=your_discord_bot_token
DISCORD_WEBHOOK_URL=your_webhook_url

# InfluxDB
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_URL=http://localhost:8086
INFLUXDB_ORG=trading
INFLUXDB_BUCKET=crypto

# Security
JWT_SECRET=your_jwt_secret_key
API_SECRET_KEY=your_api_secret_key

# Trading
DEFAULT_CAPITAL=1000
SAFE_BOT_ALLOCATION=0.7
AGGRESSIVE_BOT_ALLOCATION=0.3
REALLOCATION_RATIO=0.3
```

### 3. Démarrage avec Docker (recommandé)

```bash
# Lancer tous les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

### 4. Démarrage sans Docker (développement)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# Trading Engine (dans un autre terminal)
cd backend
source venv/bin/activate
python -m engines.main

# Discord Bot (dans un autre terminal)
cd discord-bot
source venv/bin/activate
python bot.py

# Mobile App
cd mobile
npm install
npx expo start
```

---

## Structure du projet

```
my_trading_bot/
├── backend/                # Backend Python (FastAPI + Moteurs)
│   ├── api/                # API REST + WebSocket
│   ├── engines/            # Moteurs de trading
│   ├── indicators/         # Indicateurs techniques (plugins)
│   ├── strategies/         # Stratégies de décision
│   ├── exchanges/          # Connecteurs exchange
│   ├── models/             # Modèles de données
│   ├── risk/               # Gestion des risques
│   └── tests/              # Tests
├── mobile/                 # Application React Native (Expo)
├── discord-bot/            # Bot Discord
├── docs/                   # Documentation complète
├── docker-compose.yml      # Orchestration Docker
└── instructions.md         # Ce fichier
```

> Voir `docs/TARGET_ARCHITECTURE.md` pour les détails complets.

---

## Concepts clés

### Moteur d'indicateurs

Le moteur calcule 15+ indicateurs techniques sur des données OHLCV multi-temporalité :

| Indicateur | Description |
|-----------|-------------|
| RSI | Force relative (surachat/survente) |
| MACD | Convergence/Divergence des MM |
| Bollinger Bands | Bandes de volatilité |
| EMA (5/10/20/50) | Moyennes mobiles exponentielles |
| SMA (50/200) | Moyennes mobiles simples (Golden Cross) |
| Stochastic RSI | RSI stochastique |
| ADI | Accumulation/Distribution |
| Volume | Analyse volumétrique + détection baleines |
| Fibonacci | Niveaux de retracement |
| Support/Résistance | Niveaux dynamiques |
| Fear & Greed | Indice de sentiment |
| Choppiness (CHOP) | Consolidation vs tendance |
| Google Trends | Tendance d'intérêt |

Chaque indicateur est un **plugin indépendant** qui hérite de `BaseIndicator`.

### Moteur de décision

Le moteur de décision transforme les signaux en actions (BUY/SELL/HOLD). Il utilise le pattern **Strategy** :

- **ConservativeStrategy** : seuils élevés, confirmation par 5+ indicateurs, risque 1%
- **AggressiveStrategy** : seuils bas, confirmation par 3+ indicateurs, risque 3%

### Deux bots de trading

| | Bot Sécuritaire | Bot Agressif |
|---|----------------|-------------|
| **Allocation** | 70% du capital | 30% du capital |
| **Risque** | Low (1% par trade) | Max (3% par trade) |
| **Stratégie** | Conservative | Aggressive |
| **Fréquence** | Moins de trades | Plus de trades |
| **Stop-Loss** | 1-2% | 2-3% |
| **Take-Profit** | 5-8% | 10-15% |

### Réallocation automatique

Quand le bot agressif réalise un gain :
1. Un **ratio configurable** (défaut 30%) du gain est transféré au bot sécuritaire
2. Le bot sécuritaire augmente son capital de base
3. Le bot agressif conserve le reste pour continuer à trader

### Réduction dynamique du risque

- **3 pertes consécutives** → risque divisé par 2
- **5 pertes consécutives** → mise en pause du bot
- **2 gains consécutifs** après réduction → restauration progressive du risque

---

## API Endpoints

### Authentification
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/login` | Connexion |
| POST | `/auth/register` | Inscription |
| POST | `/auth/refresh` | Rafraîchir le token |

### Bots
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/bots` | Lister les bots |
| GET | `/api/bots/:id` | Détails d'un bot |
| POST | `/api/bots/:id/start` | Démarrer un bot |
| POST | `/api/bots/:id/stop` | Arrêter un bot |
| PATCH | `/api/bots/:id/config` | Modifier la config |

### Trades
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/trades` | Historique des trades |
| GET | `/api/trades/:id` | Détails d'un trade |
| GET | `/api/trades/open` | Positions ouvertes |

### Backtesting
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/backtest/run` | Lancer un backtest |
| GET | `/api/backtest/results` | Résultats des backtests |
| POST | `/api/backtest/compare` | Comparer des stratégies |

### Configuration
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/config` | Configuration actuelle |
| PUT | `/api/config` | Modifier la configuration |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| `/ws/trades` | Trades en temps réel |
| `/ws/indicators` | Indicateurs en temps réel |
| `/ws/portfolio` | État du portefeuille |

---

## Commandes Discord

| Commande | Description |
|----------|-------------|
| `/status` | Résumé des bots (capital, P&L, positions) |
| `/trades` | Liste des derniers trades |
| `/risk` | Niveaux de risque actuels |
| `/pause [bot]` | Mettre un bot en pause |
| `/resume [bot]` | Reprendre un bot |
| `/backtest [pair] [period]` | Lancer un backtest rapide |
| `/config` | Voir la configuration actuelle |
| `/balance` | Voir les balances des bots |

---

## Tests

```bash
# Tous les tests
cd backend
pytest

# Tests unitaires uniquement
pytest tests/unit/

# Tests d'intégration
pytest tests/integration/

# Avec couverture
pytest --cov=. --cov-report=html

# Test d'un indicateur spécifique
pytest tests/unit/test_indicators.py -k "test_rsi"
```

---

## Conventions de code

### Python (Backend)
- **Style** : PEP 8 + Black formatter
- **Type hints** : obligatoires sur toutes les fonctions publiques
- **Docstrings** : Google style
- **Imports** : isort
- **Linting** : ruff
- **Tests** : pytest + hypothesis (property-based)

### TypeScript (Mobile)
- **Style** : ESLint + Prettier
- **Types** : strict mode
- **Components** : Functional + hooks
- **State** : Zustand
- **Navigation** : Expo Router

### Git
- **Branches** : `feature/`, `fix/`, `refactor/`
- **Commits** : Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`)
- **PR** : Review obligatoire, tests passants

---

## Monitoring

### Grafana Dashboards
- **Trading Performance** : P&L, win rate, drawdown par bot
- **Indicateurs** : Valeurs en temps réel des 15+ indicateurs
- **System** : CPU, mémoire, latence API exchange

### Logs
- **Trading Engine** : `/var/log/trading/engine.log`
- **API** : `/var/log/trading/api.log`
- **Discord Bot** : `/var/log/trading/discord.log`

---

## Sécurité

- Ne **jamais** commiter les API keys ou tokens
- Utiliser **uniquement** des variables d'environnement pour les secrets
- Les API keys exchange sont **chiffrées** en base de données
- L'API est protégée par **JWT** avec refresh tokens
- **Rate limiting** sur tous les endpoints
- **HTTPS** obligatoire en production
- Vérifier régulièrement les permissions des API keys exchange (désactiver le retrait)

---

## Troubleshooting

### Le bot ne trade pas
1. Vérifier que `bench_mode` est à `false` pour le trading réel
2. Vérifier les API keys Binance/Kraken
3. Vérifier que le capital minimum ($5) est disponible
4. Consulter les logs : `docker-compose logs trading-engine`

### Erreurs d'API Exchange
1. Vérifier les permissions de l'API key (trading spot activé)
2. Vérifier l'IP whitelist sur Binance
3. Vérifier les rate limits (429 errors)

### Le Discord bot ne répond pas
1. Vérifier le `DISCORD_TOKEN`
2. Vérifier que le bot est invité sur le serveur avec les bonnes permissions
3. Consulter les logs : `docker-compose logs discord-bot`

---

## Documentation complète

| Document | Description |
|----------|-------------|
| `docs/CURRENT_STATE.md` | Documentation de l'architecture actuelle (v1) |
| `docs/TARGET_ARCHITECTURE.md` | Architecture cible détaillée (v2) |
| `docs/DIAGRAMS.md` | Schémas Mermaid (architecture, flux, classes) |
| `docs/ROADMAP.md` | Plan d'actions et suggestions d'amélioration |
| `instructions.md` | Ce fichier — guide d'utilisation du projet |
