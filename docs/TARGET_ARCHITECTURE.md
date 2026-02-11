# CryptoTrader Bot — Architecture Cible (v2)

## Vision

Transformer le bot monolithique Python/Flask actuel en une **plateforme modulaire de trading crypto** avec :
- Un **backend Python** performant (moteurs de trading)
- Une **application mobile/web React Native** (pilotage)
- Deux bots distincts (sécuritaire + agressif) avec **réallocation automatique des gains**
- Un **bot Discord** riche pour les alertes
- Une architecture **extensible et testable**

---

## Choix technologiques

| Composant | Technologie | Justification |
|-----------|------------|---------------|
| **Backend API** | Python + FastAPI | Performance async, typing natif, écosystème data science |
| **Frontend mobile/web** | React Native (Expo) | Multi-plateforme (iOS, Android, Web) d'une seule codebase |
| **Base de données** | PostgreSQL + TimescaleDB | Séries temporelles optimisées pour les données OHLCV |
| **Cache** | Redis | État des trades en temps réel, pub/sub pour événements |
| **Message Queue** | Redis Streams (ou RabbitMQ) | Communication découplée entre moteurs |
| **Bot Discord** | discord.py / interactions.py | Commandes slash + embeds riches |
| **Monitoring** | InfluxDB + Grafana | Conservation de l'existant + dashboards visuels |
| **Tests** | pytest + hypothesis | Tests unitaires, intégration, property-based |
| **CI/CD** | GitHub Actions | Automatisation tests + déploiement |
| **Container** | Docker + Docker Compose | Orchestration multi-services |

### Pourquoi React Native plutôt que Flask ?

| Critère | Flask (actuel) | React Native (cible) |
|---------|---------------|---------------------|
| Mobile | Non natif | iOS + Android natifs |
| UX | Basique (Bootstrap) | Composants natifs, animations |
| Temps réel | Polling AJAX | WebSockets natifs |
| Offline | Non | Support offline |
| Notifications | Non | Push notifications natives |
| Performance | Rendu serveur | Rendu natif optimisé |

### Suggestion : Backend API séparé du moteur de trading

Le backend Flask actuel mélange interface et logique métier. L'architecture cible sépare :
- **FastAPI** : API REST + WebSocket pour le frontend
- **Moteurs Python** : Processus indépendants communiquant via Redis

---

## Architecture globale cible

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                       │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  React Native    │  │  Bot Discord     │  │  Grafana         │  │
│  │  Mobile / Web    │  │  Alertes & Cmd   │  │  Dashboards      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
└───────────┼──────────────────────┼──────────────────────┼────────────┘
            │ REST/WS              │ Events               │ Metrics
            ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (FastAPI)                         │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Auth     │ │ Trading  │ │ Config   │ │ WebSocket│              │
│  │ /auth/*  │ │ /api/*   │ │ /config/*│ │ /ws      │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MESSAGE BUS (Redis Streams)                      │
│                                                                      │
│  Channels: orders │ signals │ indicators │ alerts │ rebalance       │
└──────┬────────────────┬────────────────┬────────────────┬───────────┘
       │                │                │                │
       ▼                ▼                ▼                ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│  INDICATOR  │ │  DECISION   │ │   ORDER     │ │  PORTFOLIO      │
│  ENGINE     │ │  ENGINE     │ │   ENGINE    │ │  MANAGER        │
│             │ │             │ │             │ │                  │
│ - RSI       │ │ - Scoring   │ │ - Buy/Sell  │ │ - Bot Safe      │
│ - MACD      │ │ - Stratégie │ │ - SL/TP     │ │ - Bot Agressif  │
│ - Bollinger │ │ - Tendance  │ │ - Exchange  │ │ - Réallocation  │
│ - EMA/SMA   │ │ - Signaux   │ │   API       │ │ - Risk Control  │
│ - Volume    │ │             │ │             │ │                  │
│ - Fibonacci │ │             │ │             │ │                  │
│ - 10+ autres│ │             │ │             │ │                  │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └────────┬────────┘
       │                │                │                 │
       └────────────────┴────────────────┴─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            ┌─────────────┐ ┌────────┐ ┌──────────┐
            │ PostgreSQL  │ │ Redis  │ │ InfluxDB │
            │ + Timescale │ │ Cache  │ │ Metrics  │
            └─────────────┘ └────────┘ └──────────┘
```

---

## Composants détaillés

### 1. Indicator Engine (Moteur d'indicateurs)

**Rôle** : Calculer les indicateurs techniques à partir de données OHLCV multi-temporalité.

```python
# Structure cible
class IndicatorEngine:
    """Moteur de calcul d'indicateurs techniques."""

    def __init__(self, config: IndicatorConfig):
        self.indicators: list[BaseIndicator] = []
        self.timeframes: list[Timeframe] = []

    def register_indicator(self, indicator: BaseIndicator) -> None:
        """Enregistre un indicateur (pattern Plugin)."""

    def compute(self, data: pd.DataFrame, timeframe: Timeframe) -> IndicatorResult:
        """Calcule tous les indicateurs sur un jeu de données."""

    def compute_multi_timeframe(self, datasets: dict[Timeframe, pd.DataFrame]) -> dict:
        """Calcul multi-temporalité."""

class BaseIndicator(ABC):
    """Classe abstraite pour tous les indicateurs."""

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> IndicatorSignal:
        """Calcule l'indicateur et retourne un signal."""

    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def get_weight(self) -> float: ...
```

**Caractéristiques** :
- Pattern **Plugin** : chaque indicateur est une classe indépendante
- Support multi-timeframe natif
- Poids configurable par indicateur
- Résultats typés avec `dataclass` / Pydantic

---

### 2. Decision Engine (Moteur de décision)

**Rôle** : Transformer les signaux d'indicateurs en décisions de trading.

```python
class DecisionEngine:
    """Moteur de prise de décision générique."""

    def __init__(self, strategy: BaseStrategy):
        self.strategy = strategy

    def evaluate(self, indicators: IndicatorResult) -> TradingSignal:
        """Évalue les indicateurs et produit un signal."""

    def get_confidence(self) -> float:
        """Retourne le niveau de confiance (0.0 - 1.0)."""

class BaseStrategy(ABC):
    """Stratégie de décision abstraite."""

    @abstractmethod
    def score(self, indicators: IndicatorResult) -> float: ...

    @abstractmethod
    def should_buy(self, score: float, context: MarketContext) -> bool: ...

    @abstractmethod
    def should_sell(self, score: float, context: MarketContext) -> bool: ...

class ConservativeStrategy(BaseStrategy):
    """Stratégie sécuritaire — seuils de confiance élevés."""

class AggressiveStrategy(BaseStrategy):
    """Stratégie agressive — plus réactive, seuils bas."""
```

**Caractéristiques** :
- Pattern **Strategy** : stratégies interchangeables
- Niveau de confiance pour moduler la taille des positions
- Contexte de marché (Fear & Greed, volume, volatilité)

---

### 3. Order Engine (Moteur de passage d'ordres)

**Rôle** : Exécuter les ordres sur les exchanges de manière sécurisée.

```python
class OrderEngine:
    """Moteur d'exécution d'ordres."""

    def __init__(self, exchange: BaseExchange, risk_manager: RiskManager):
        self.exchange = exchange
        self.risk_manager = risk_manager

    async def place_order(self, order: Order) -> OrderResult:
        """Place un ordre après validation par le risk manager."""

    async def place_order_with_protection(self, order: Order) -> ProtectedPosition:
        """Place un ordre + SL + TP atomiquement."""

class BaseExchange(ABC):
    """Interface abstraite pour les exchanges."""

    @abstractmethod
    async def buy(self, pair: str, amount: Decimal, price: Optional[Decimal]) -> OrderResult: ...

    @abstractmethod
    async def sell(self, pair: str, amount: Decimal, price: Optional[Decimal]) -> OrderResult: ...

    @abstractmethod
    async def get_balance(self, asset: str) -> Decimal: ...

class BinanceExchange(BaseExchange): ...
class KrakenExchange(BaseExchange): ...
```

---

### 4. Backtest Engine (Moteur de benchmark)

**Rôle** : Simuler des stratégies sur des données historiques avec réalisme.

```python
class BacktestEngine:
    """Moteur de backtesting avancé."""

    def __init__(self, config: BacktestConfig):
        self.fees: Decimal = Decimal("0.001")     # 0.1% par défaut
        self.slippage: Decimal = Decimal("0.0005") # 0.05% par défaut

    def run(
        self,
        data: pd.DataFrame,
        strategy: BaseStrategy,
        initial_capital: Decimal,
        timeframe: Timeframe
    ) -> BacktestResult:
        """Exécute un backtest complet."""

    def run_multi_timeframe(self, datasets: dict) -> BacktestResult:
        """Backtest multi-temporalité."""

    def compare_strategies(
        self,
        strategies: list[BaseStrategy],
        data: pd.DataFrame
    ) -> ComparisonReport:
        """Compare plusieurs stratégies sur le même jeu de données."""

@dataclass
class BacktestResult:
    total_return: Decimal
    max_drawdown: Decimal
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: float
    trades: list[SimulatedTrade]
    equity_curve: pd.Series
```

**Améliorations vs existant** :
- Prise en compte des **frais** et du **slippage**
- Calcul du **Sharpe Ratio**, **Max Drawdown**, **Profit Factor**
- **Comparaison de stratégies** côte à côte
- Courbe d'**equity** pour visualisation

---

### 5. Portfolio Manager (Gestionnaire de portefeuille)

**Rôle** : Gérer les deux bots (sécuritaire + agressif) et la réallocation des gains.

```python
class PortfolioManager:
    """Gestionnaire de portefeuille multi-bots."""

    def __init__(self, config: PortfolioConfig):
        self.safe_bot: TradingBot       # Bot sécuritaire
        self.aggressive_bot: TradingBot # Bot agressif
        self.reallocation_ratio: float  # % des gains réalloués (ex: 0.3 = 30%)
        self.risk_reducer: RiskReducer

    async def rebalance(self) -> RebalanceResult:
        """Réallocation automatique : gains agressif → capital sécuritaire."""

    def adjust_risk(self) -> None:
        """Réduit l'exposition si trop de pertes consécutives."""

class RiskReducer:
    """Réduction dynamique du risque basée sur les performances."""

    def __init__(self, config: RiskConfig):
        self.max_consecutive_losses: int = 3
        self.risk_reduction_factor: float = 0.5
        self.recovery_threshold: int = 2  # wins pour restaurer

    def evaluate(self, trade_history: list[Trade]) -> RiskAdjustment:
        """Évalue si le risque doit être réduit."""
```

**Mécanique de réallocation** :
```
┌─────────────────┐         ┌─────────────────┐
│  Bot Agressif   │         │ Bot Sécuritaire  │
│                 │         │                  │
│  Capital: 300$  │  gains  │  Capital: 700$   │
│  Risk: Max      │────────►│  Risk: Low       │
│  Trades: +50$   │  30%    │  Reçoit: +15$    │
│                 │ réalloc │                  │
└─────────────────┘         └─────────────────┘

Ratio configurable : 10% → 50% des gains
Fréquence : après chaque trade gagnant du bot agressif
```

**Mécanique de réduction de risque** :
```
Pertes consécutives ≥ 3 → Risque ÷ 2
Pertes consécutives ≥ 5 → Risque ÷ 4 (ou pause trading)
2 gains consécutifs     → Restauration progressive du risque
```

---

### 6. React Native App (Interface de pilotage)

**Structure du projet React Native (Expo)** :

```
mobile/
├── app/                          # Expo Router (file-based routing)
│   ├── (tabs)/
│   │   ├── _layout.tsx           # Tab navigation layout
│   │   ├── index.tsx             # Dashboard principal
│   │   ├── bots.tsx              # Gestion des bots
│   │   ├── backtest.tsx          # Backtesting
│   │   └── settings.tsx          # Configuration
│   ├── bot/
│   │   └── [id].tsx              # Détail d'un bot
│   └── _layout.tsx               # Root layout
├── components/
│   ├── charts/
│   │   ├── EquityCurve.tsx       # Courbe d'equity
│   │   ├── CandlestickChart.tsx  # Graphique chandelier
│   │   └── IndicatorChart.tsx    # Graphiques d'indicateurs
│   ├── dashboard/
│   │   ├── PortfolioSummary.tsx  # Résumé portefeuille
│   │   ├── BotCard.tsx           # Carte d'un bot
│   │   └── RecentTrades.tsx      # Trades récents
│   └── common/
│       ├── RiskBadge.tsx         # Badge niveau de risque
│       └── SignalIndicator.tsx   # Indicateur de signal
├── hooks/
│   ├── useWebSocket.ts          # Connexion WebSocket temps réel
│   ├── useTrading.ts            # Actions trading
│   └── usePortfolio.ts          # Données portefeuille
├── services/
│   ├── api.ts                   # Client API FastAPI
│   └── websocket.ts             # Client WebSocket
├── store/
│   └── tradingStore.ts          # État global (Zustand)
└── types/
    └── trading.ts               # Types TypeScript
```

**Écrans principaux** :

| Écran | Fonctionnalités |
|-------|----------------|
| **Dashboard** | Résumé portefeuille, P&L global, derniers trades, indicateurs clés |
| **Bots** | Liste des bots, status, start/stop, config rapide |
| **Bot Detail** | Performances, trades, indicateurs actifs, réglages risque |
| **Backtest** | Lancer des backtests, comparer stratégies, visualiser résultats |
| **Settings** | Configuration API keys, paires, notifications, thème |

---

### 7. Bot Discord

**Fonctionnalités** :

```
Commandes Slash:
  /status           → Résumé des bots (capital, P&L, positions ouvertes)
  /trades           → Derniers trades avec détails
  /risk             → Niveaux de risque actuels
  /pause [bot]      → Met un bot en pause
  /resume [bot]     → Reprend un bot
  /backtest [pair]  → Lance un backtest rapide

Alertes automatiques (Embeds riches):
  🟢 ACHAT  — BTC/USDT @ 67,450$
  ├── Bot: Agressif
  ├── Quantité: 0.0045 BTC
  ├── Stop-Loss: 66,101$ (-2.0%)
  ├── Take-Profit: 74,195$ (+10.0%)
  ├── Risque: 30.00$
  ├── Gain potentiel: 150.00$
  ├── Ratio R/R: 5.0
  ├── Confiance: 78%
  └── Indicateurs: RSI ✅ MACD ✅ BB ✅ Vol ⚠️

  🔴 VENTE — BTC/USDT @ 74,195$ (+10.0%)
  ├── Bot: Agressif
  ├── P&L: +150.00$ (+10.0%)
  ├── Réallocation: 45.00$ → Bot Sécuritaire
  └── Durée: 3j 14h

  ⚠️ RISQUE RÉDUIT — Bot Agressif
  ├── Raison: 3 pertes consécutives
  ├── Ancien risque: 3.0%
  └── Nouveau risque: 1.5%
```

---

## Modèle de données

### Entités principales

```sql
-- Paires de trading
CREATE TABLE trading_pairs (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,          -- ex: BTCUSDT
    base_asset VARCHAR(10) NOT NULL,      -- ex: BTC
    quote_asset VARCHAR(10) NOT NULL,     -- ex: USDT
    exchange VARCHAR(20) NOT NULL,        -- ex: binance
    is_active BOOLEAN DEFAULT true
);

-- Bots de trading
CREATE TABLE bots (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,            -- ex: "Safe Bot", "Aggressive Bot"
    type VARCHAR(20) NOT NULL,            -- safe / aggressive
    status VARCHAR(20) DEFAULT 'stopped', -- running / stopped / paused
    capital DECIMAL(20,8) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,      -- Low / Mid / Max
    current_risk_ratio DECIMAL(5,4),      -- Ratio dynamique après ajustements
    strategy_config JSONB,                -- Configuration de la stratégie
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trades exécutés
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER REFERENCES bots(id),
    pair_id INTEGER REFERENCES trading_pairs(id),
    side VARCHAR(4) NOT NULL,             -- buy / sell
    entry_price DECIMAL(20,8),
    exit_price DECIMAL(20,8),
    quantity DECIMAL(20,8),
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    pnl DECIMAL(20,8),
    pnl_percent DECIMAL(8,4),
    risk_reward_ratio DECIMAL(8,4),
    confidence DECIMAL(5,4),
    status VARCHAR(20),                   -- open / closed / cancelled
    indicators_snapshot JSONB,            -- État des indicateurs au moment du trade
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Réallocations
CREATE TABLE reallocations (
    id SERIAL PRIMARY KEY,
    from_bot_id INTEGER REFERENCES bots(id),
    to_bot_id INTEGER REFERENCES bots(id),
    amount DECIMAL(20,8) NOT NULL,
    trigger_trade_id INTEGER REFERENCES trades(id),
    ratio_applied DECIMAL(5,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Données OHLCV (TimescaleDB hypertable)
CREATE TABLE ohlcv_data (
    time TIMESTAMPTZ NOT NULL,
    pair_id INTEGER REFERENCES trading_pairs(id),
    timeframe VARCHAR(10) NOT NULL,       -- 1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M
    open DECIMAL(20,8),
    high DECIMAL(20,8),
    low DECIMAL(20,8),
    close DECIMAL(20,8),
    volume DECIMAL(20,8)
);
-- SELECT create_hypertable('ohlcv_data', 'time');
```

---

## Communication inter-services

```
┌──────────────┐     Redis Streams      ┌──────────────┐
│  Indicator   │ ──── indicators ──────► │  Decision    │
│  Engine      │                         │  Engine      │
└──────────────┘                         └──────┬───────┘
                                                │
                                         signals│
                                                ▼
┌──────────────┐     Redis Streams      ┌──────────────┐
│  Portfolio   │ ◄──── orders ────────── │   Order      │
│  Manager     │                         │   Engine     │
└──────┬───────┘                         └──────────────┘
       │
       │ rebalance
       ▼
┌──────────────┐     Redis Streams      ┌──────────────┐
│  FastAPI     │ ◄──── alerts ────────── │   Discord    │
│  (WebSocket) │                         │   Bot        │
└──────────────┘                         └──────────────┘
```

### Format des messages (JSON)

```json
// Channel: indicators
{
  "timestamp": "2026-02-11T14:30:00Z",
  "pair": "BTCUSDT",
  "timeframe": "1h",
  "indicators": {
    "rsi": {"value": 35.2, "signal": "oversold", "strength": "strong"},
    "macd": {"value": 125.5, "signal": "bullish", "histogram": "rising"},
    "bollinger": {"signal": "neutral", "position": "middle"}
  }
}

// Channel: signals
{
  "timestamp": "2026-02-11T14:30:01Z",
  "pair": "BTCUSDT",
  "action": "buy",
  "confidence": 0.78,
  "strategy": "aggressive",
  "target_bot": "aggressive_bot"
}

// Channel: orders
{
  "timestamp": "2026-02-11T14:30:02Z",
  "bot_id": 2,
  "pair": "BTCUSDT",
  "side": "buy",
  "quantity": "0.0045",
  "price": "67450.00",
  "stop_loss": "66101.00",
  "take_profit": "74195.00"
}

// Channel: alerts
{
  "type": "trade_executed",
  "bot": "Agressif",
  "pair": "BTCUSDT",
  "side": "buy",
  "price": "67450.00",
  "risk": "30.00",
  "potential_gain": "150.00",
  "rr_ratio": "5.0"
}
```

---

## Sécurité

| Mesure | Implémentation |
|--------|----------------|
| **Auth API** | JWT avec refresh tokens |
| **API Keys** | Chiffrées en BDD (Fernet/AES) |
| **Rate Limiting** | FastAPI middleware + Redis |
| **CORS** | Origines autorisées uniquement |
| **Secrets** | Variables d'environnement (.env) |
| **Webhook Discord** | Stocké en .env, jamais en code |
| **HTTPS** | Obligatoire en production |
| **Audit Log** | Toutes les actions tracées |

---

## Déploiement (Docker Compose)

```yaml
version: '3.8'

services:
  # API Backend
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/trading
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  # Trading Engines (processus long)
  trading-engine:
    build: ./backend
    command: python -m engines.main
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/trading
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  # Discord Bot
  discord-bot:
    build: ./discord-bot
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  # PostgreSQL + TimescaleDB
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      - POSTGRES_DB=trading
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # InfluxDB (monitoring)
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    volumes:
      - influxdata:/var/lib/influxdb2

  # Grafana (dashboards)
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on:
      - influxdb

volumes:
  pgdata:
  influxdata:
```

---

## Structure du projet cible

```
my_trading_bot/
├── backend/                          # Backend Python
│   ├── api/                          # FastAPI application
│   │   ├── main.py                   # Point d'entrée FastAPI
│   │   ├── routes/
│   │   │   ├── auth.py               # Authentification
│   │   │   ├── bots.py               # CRUD Bots
│   │   │   ├── trades.py             # Trades API
│   │   │   ├── backtest.py           # Backtesting API
│   │   │   ├── config.py             # Configuration API
│   │   │   └── websocket.py          # WebSocket endpoints
│   │   ├── middleware/
│   │   │   ├── auth.py               # JWT middleware
│   │   │   └── rate_limit.py         # Rate limiting
│   │   └── schemas/                  # Pydantic schemas
│   │       ├── bot.py
│   │       ├── trade.py
│   │       └── indicator.py
│   │
│   ├── engines/                      # Moteurs de trading
│   │   ├── main.py                   # Orchestrateur des moteurs
│   │   ├── indicator_engine.py       # Moteur d'indicateurs
│   │   ├── decision_engine.py        # Moteur de décision
│   │   ├── order_engine.py           # Moteur d'ordres
│   │   ├── backtest_engine.py        # Moteur de backtesting
│   │   └── portfolio_manager.py      # Gestionnaire de portefeuille
│   │
│   ├── indicators/                   # Indicateurs (plugins)
│   │   ├── base.py                   # BaseIndicator (ABC)
│   │   ├── rsi.py
│   │   ├── macd.py
│   │   ├── bollinger.py
│   │   ├── ema.py
│   │   ├── sma.py
│   │   ├── stochastic_rsi.py
│   │   ├── volume.py
│   │   ├── fibonacci.py
│   │   ├── adi.py
│   │   ├── support_resistance.py
│   │   ├── fear_greed.py
│   │   ├── choppiness.py
│   │   └── google_trends.py
│   │
│   ├── strategies/                   # Stratégies de décision
│   │   ├── base.py                   # BaseStrategy (ABC)
│   │   ├── conservative.py           # Stratégie sécuritaire
│   │   └── aggressive.py             # Stratégie agressive
│   │
│   ├── exchanges/                    # Connecteurs exchange
│   │   ├── base.py                   # BaseExchange (ABC)
│   │   ├── binance.py
│   │   └── kraken.py
│   │
│   ├── models/                       # SQLAlchemy models
│   │   ├── bot.py
│   │   ├── trade.py
│   │   ├── ohlcv.py
│   │   └── reallocation.py
│   │
│   ├── risk/                         # Gestion des risques
│   │   ├── risk_manager.py           # Gestionnaire de risque
│   │   └── risk_reducer.py           # Réduction dynamique
│   │
│   ├── notifications/                # Notifications
│   │   ├── discord_bot.py            # Bot Discord
│   │   └── push.py                   # Push notifications (mobile)
│   │
│   ├── tests/                        # Tests
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   │
│   ├── alembic/                      # Migrations DB
│   ├── Dockerfile
│   └── requirements.txt
│
├── mobile/                           # React Native (Expo)
│   ├── app/                          # Expo Router pages
│   ├── components/                   # Composants UI
│   ├── hooks/                        # Custom hooks
│   ├── services/                     # API clients
│   ├── store/                        # State management
│   ├── types/                        # TypeScript types
│   ├── app.json                      # Expo config
│   ├── package.json
│   └── tsconfig.json
│
├── discord-bot/                      # Bot Discord standalone
│   ├── bot.py
│   ├── cogs/
│   │   ├── trading.py                # Commandes trading
│   │   └── monitoring.py             # Commandes monitoring
│   ├── Dockerfile
│   └── requirements.txt
│
├── docs/                             # Documentation
│   ├── CURRENT_STATE.md
│   ├── TARGET_ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── DIAGRAMS.md
│
├── docker-compose.yml                # Orchestration
├── .env.example                      # Template variables d'environnement
├── .github/
│   └── workflows/
│       ├── test.yml                  # CI tests
│       └── deploy.yml                # CD déploiement
├── instructions.md                   # Instructions du projet
└── README.md                         # Documentation principale
```
