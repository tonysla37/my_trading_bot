# CryptoTrader Bot — Architecture Cible (v2)

## Vision

Transformer le bot monolithique Python/Flask actuel en une **plateforme modulaire de trading crypto** avec :
- Un **backend Python** performant (moteurs de trading)
- Une **application mobile/web React Native** (pilotage)
- Deux profils de risque (sécuritaire + agressif) avec **réallocation automatique des gains**
- Trois **bots spécialistes par condition de marché** (Bull / Bear / Range)
- Un **détecteur de régime de marché** qui orchestre l'activation des bots
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

### 2b. Market Regime Detector (Détecteur de régime de marché)

**Rôle** : Déterminer la condition actuelle du marché (haussier, baissier, latéralisation) pour activer le bot spécialiste le plus adapté.

```python
class MarketRegime(Enum):
    """Régimes de marché détectés."""
    BULL = "bull"           # Tendance haussière confirmée
    BEAR = "bear"           # Tendance baissière confirmée
    RANGING = "ranging"     # Latéralisation / consolidation
    TRANSITION = "transition"  # Phase de transition (incertain)

class MarketRegimeDetector:
    """Détecte le régime de marché actuel à partir des indicateurs."""

    def __init__(self, config: RegimeConfig):
        self.lookback_period: int = 50        # Bougies analysées
        self.confirmation_candles: int = 3    # Bougies de confirmation
        self.adx_threshold: float = 25.0      # ADX > 25 = tendance
        self.chop_threshold: float = 61.8     # CHOP > 61.8 = range

    def detect(self, data: pd.DataFrame, indicators: IndicatorResult) -> MarketRegime:
        """Détecte le régime courant via une combinaison d'indicateurs."""

    def get_regime_confidence(self) -> float:
        """Confiance dans le régime détecté (0.0 - 1.0)."""

    def get_regime_duration(self) -> int:
        """Nombre de bougies dans le régime actuel."""
```

**Critères de détection** :

| Régime | Conditions |
|--------|-----------|
| **BULL** | ADX > 25 + EMA20 > EMA50 + MACD positif + Higher Highs/Higher Lows |
| **BEAR** | ADX > 25 + EMA20 < EMA50 + MACD négatif + Lower Highs/Lower Lows |
| **RANGING** | ADX < 25 OU CHOP > 61.8 + prix oscille entre support/résistance |
| **TRANSITION** | Signaux contradictoires, régime précédent en train de changer |

---

### 2c. Bots spécialistes par condition de marché

**Rôle** : Trois stratégies spécialisées, chacune optimisée pour un régime de marché donné.

```python
class BullMarketStrategy(BaseStrategy):
    """Spécialiste marché haussier — Trend Following.

    Principe : Acheter sur les replis (supports, retracements Fibonacci)
    et vendre aux résistances / extensions.
    """

    def __init__(self):
        self.preferred_indicators = [
            "ema",              # Rebond sur EMA20/EMA50 = signal d'achat
            "fibonacci",        # Achat sur retracement 38.2% / 50% / 61.8%
            "support_resistance",  # Achat sur support dynamique
            "macd",             # Confirmation de momentum haussier
            "volume",           # Volume croissant = confirmation
        ]
        self.buy_on_pullback: bool = True       # Acheter les replis, pas les breakouts
        self.trailing_stop: bool = True         # Trailing SL pour suivre la hausse
        self.tp_at_resistance: bool = True      # TP aux résistances identifiées

    def should_buy(self, score: float, context: MarketContext) -> bool:
        """Achète quand le prix touche un support ou un retracement Fibonacci
        dans une tendance haussière confirmée."""

    def should_sell(self, score: float, context: MarketContext) -> bool:
        """Vend aux résistances ou quand le trailing stop est touché."""


class BearMarketStrategy(BaseStrategy):
    """Spécialiste marché baissier — Protection & Opportunisme.

    Principe : Réduire l'exposition, shorter si possible, ou acheter
    uniquement les rebonds techniques courts (dead cat bounce).
    Essentiellement défensif.
    """

    def __init__(self):
        self.preferred_indicators = [
            "rsi",              # RSI oversold = potentiel rebond technique
            "bollinger",        # Touche bande basse = survente extrême
            "volume",           # Capitulation volume = signal de rebond
            "fear_greed",       # Extreme Fear = potentiel contrarian buy
            "support_resistance",  # Supports historiques majeurs
        ]
        self.reduce_position_size: float = 0.5  # Taille de position ÷ 2
        self.quick_take_profit: bool = True      # TP rapide (3-5%)
        self.tight_stop_loss: bool = True        # SL serré (1-1.5%)
        self.short_enabled: bool = False         # Short selling (futures, optionnel)

    def should_buy(self, score: float, context: MarketContext) -> bool:
        """Achète uniquement sur survente extrême (RSI < 20, Extreme Fear)
        pour des rebonds techniques courts."""

    def should_sell(self, score: float, context: MarketContext) -> bool:
        """Vend rapidement dès qu'un petit gain est atteint (3-5%)."""


class RangeStrategy(BaseStrategy):
    """Spécialiste latéralisation — Range Trading / Mean Reversion.

    Principe : Identifier le range (support/résistance horizontaux),
    acheter en bas du range, vendre en haut du range.
    """

    def __init__(self):
        self.preferred_indicators = [
            "bollinger",        # Bandes = limites du range
            "rsi",              # Oscillation RSI 30-70 dans le range
            "stochastic_rsi",   # Surachat/survente dans le range
            "support_resistance",  # Bornes du range
            "choppiness",       # CHOP élevé = range confirmé
        ]
        self.range_high: Decimal = Decimal("0")   # Borne haute détectée
        self.range_low: Decimal = Decimal("0")     # Borne basse détectée
        self.range_buffer_pct: float = 0.02        # Marge de 2% aux bornes
        self.mean_reversion: bool = True           # Jouer le retour à la moyenne

    def detect_range(self, data: pd.DataFrame) -> tuple[Decimal, Decimal]:
        """Détecte les bornes du range via support/résistance horizontaux."""

    def should_buy(self, score: float, context: MarketContext) -> bool:
        """Achète quand le prix touche le bas du range (support)
        + RSI/StochRSI en survente."""

    def should_sell(self, score: float, context: MarketContext) -> bool:
        """Vend quand le prix touche le haut du range (résistance)
        + RSI/StochRSI en surachat."""
```

**Comparatif des 3 bots spécialistes** :

| | Bull Bot | Bear Bot | Range Bot |
|---|---------|----------|-----------|
| **Régime** | Marché haussier | Marché baissier | Latéralisation |
| **Principe** | Trend Following | Protection & Rebonds | Mean Reversion |
| **Achat** | Sur pullbacks / supports | Sur survente extrême | Bas du range |
| **Vente** | Aux résistances / trailing | Take-profit rapide | Haut du range |
| **Indicateurs clés** | EMA, Fibonacci, MACD | RSI, Bollinger, Fear&Greed | Bollinger, S/R, StochRSI |
| **Taille position** | 100% du sizing normal | 50% (réduit) | 75% |
| **Stop-Loss** | Trailing (suit le prix) | Serré (1-1.5%) | Sous le range (-2%) |
| **Take-Profit** | Résistance suivante | Rapide (3-5%) | Haut du range |
| **Fréquence** | Moyenne | Basse (sélectif) | Haute (rebonds fréquents) |

**Orchestration par le Market Regime Detector** :

```
MarketRegimeDetector
    │
    ├── detect() → BULL
    │   └── Active: BullMarketStrategy
    │       └── Pondération: 100% Bull Bot
    │
    ├── detect() → BEAR
    │   └── Active: BearMarketStrategy
    │       └── Pondération: 100% Bear Bot
    │
    ├── detect() → RANGING
    │   └── Active: RangeStrategy
    │       └── Pondération: 100% Range Bot
    │
    └── detect() → TRANSITION
        └── Mode prudent:
            ├── Réduire toutes les positions de 50%
            ├── Pas de nouveaux trades
            └── Attendre confirmation du nouveau régime
```

**Interaction avec les profils de risque (Safe/Aggressive)** :

La spécialisation par régime de marché est **orthogonale** au profil de risque :

```
                    ┌──────────────┬──────────────┐
                    │  Safe (1%)   │ Aggro (3%)   │
    ┌───────────────┼──────────────┼──────────────┤
    │ Bull Bot      │ Bull + Safe  │ Bull + Aggro │
    │ Bear Bot      │ Bear + Safe  │ Bear + Aggro │
    │ Range Bot     │ Range + Safe │ Range + Aggro│
    └───────────────┴──────────────┴──────────────┘

    → 6 combinaisons possibles
    → Le profil de risque module la TAILLE de la position
    → La stratégie de marché module la LOGIQUE d'entrée/sortie
```

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

**Rôle** : Gérer les profils de risque (sécuritaire + agressif), les bots spécialistes (bull, bear, range), la réallocation des gains et l'orchestration par régime de marché.

```python
class PortfolioManager:
    """Gestionnaire de portefeuille multi-bots avec orchestration par régime."""

    def __init__(self, config: PortfolioConfig):
        # Profils de risque
        self.risk_profiles: dict[str, RiskProfile] = {
            "safe": RiskProfile(ratio=0.01, allocation=0.7),
            "aggressive": RiskProfile(ratio=0.03, allocation=0.3),
        }

        # Bots spécialistes (1 par régime × profil de risque)
        self.specialist_bots: dict[tuple[MarketRegime, str], TradingBot] = {}
        self.regime_detector: MarketRegimeDetector
        self.reallocation_ratio: float   # % des gains réalloués (ex: 0.3 = 30%)
        self.risk_reducer: RiskReducer

    async def orchestrate(self, market_data: pd.DataFrame) -> None:
        """Boucle principale : détecte le régime et active les bons bots."""
        regime = self.regime_detector.detect(market_data, indicators)
        self._activate_bots_for_regime(regime)
        self._deactivate_bots_for_other_regimes(regime)

    def _activate_bots_for_regime(self, regime: MarketRegime) -> None:
        """Active les bots spécialistes du régime détecté."""

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

**Architecture complète des bots** :

```
                    Market Regime Detector
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │ BULL Bot │ │ BEAR Bot │ │RANGE Bot │
          │          │ │          │ │          │
          │ Trend    │ │ Défensif │ │ Mean     │
          │ Following│ │ + Rebonds│ │ Reversion│
          └────┬─────┘ └────┬─────┘ └────┬─────┘
               │            │            │
        ┌──────┴──────┬─────┴──────┬─────┴──────┐
        ▼             ▼            ▼            ▼
  ┌───────────┐ ┌───────────┐ ┌──────────┐
  │ Safe (1%) │ │ Aggro (3%)│ │          │
  │ profil    │ │ profil    │ │ Réalloc. │
  │           │ │           │ │ Gains    │
  └───────────┘ └───────────┘ └──────────┘
        │             │            │
        │    gains    │            │
        │◄────────────┤   30%      │
        │             │ réalloc    │
```

**Mécanique de réallocation** :
```
┌─────────────────┐         ┌─────────────────┐
│  Profil Agressif│         │ Profil Sécurit. │
│                 │         │                  │
│  Capital: 300$  │  gains  │  Capital: 700$   │
│  Risk: Max (3%) │────────►│  Risk: Low (1%)  │
│  Trades: +50$   │  30%    │  Reçoit: +15$    │
│                 │ réalloc │                  │
└─────────────────┘         └─────────────────┘

Ratio configurable : 10% → 50% des gains
Fréquence : après chaque trade gagnant du profil agressif
S'applique quel que soit le bot spécialiste actif
```

**Mécanique de réduction de risque** :
```
Pertes consécutives ≥ 3 → Risque ÷ 2
Pertes consécutives ≥ 5 → Risque ÷ 4 (ou pause trading)
2 gains consécutifs     → Restauration progressive du risque
Applicable par bot spécialiste ET par profil de risque
```

**Gestion des transitions de régime** :
```
Régime change de BULL → BEAR :
  1. Le Bull Bot ferme ses positions ouvertes (ordres de sortie progressifs)
  2. Période tampon (TRANSITION) : pas de nouveaux trades
  3. Le Bear Bot s'active avec le capital disponible
  4. Les positions du Bull Bot non fermées passent en mode "exit only"
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
  ├── Bot: Bull Bot (Agressif)
  ├── Régime: BULL (confiance 85%)
  ├── Quantité: 0.0045 BTC
  ├── Stop-Loss: 66,101$ (-2.0%) [Trailing]
  ├── Take-Profit: 74,195$ (+10.0%) [Résistance]
  ├── Risque: 30.00$
  ├── Gain potentiel: 150.00$
  ├── Ratio R/R: 5.0
  ├── Confiance: 78%
  └── Indicateurs: RSI ✅ MACD ✅ EMA ✅ Fibo ✅ Vol ⚠️

  🔴 VENTE — BTC/USDT @ 74,195$ (+10.0%)
  ├── Bot: Bull Bot (Agressif)
  ├── P&L: +150.00$ (+10.0%)
  ├── Réallocation: 45.00$ → Profil Sécuritaire
  └── Durée: 3j 14h

  🔄 RÉGIME CHANGÉ — BULL → RANGING
  ├── Ancien régime: Bull (durée: 45 jours)
  ├── Nouveau régime: Ranging
  ├── Action: Bull Bot → fermeture positions
  ├── Action: Range Bot → activation
  └── Range détecté: 65,200$ — 68,800$

  ⚠️ RISQUE RÉDUIT — Range Bot (Agressif)
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
    name VARCHAR(50) NOT NULL,            -- ex: "Bull Bot Safe", "Range Bot Aggressive"
    specialist_type VARCHAR(20) NOT NULL, -- bull / bear / range
    risk_profile VARCHAR(20) NOT NULL,    -- safe / aggressive
    status VARCHAR(20) DEFAULT 'stopped', -- running / stopped / paused
    capital DECIMAL(20,8) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,      -- Low / Mid / Max
    current_risk_ratio DECIMAL(5,4),      -- Ratio dynamique après ajustements
    strategy_config JSONB,                -- Configuration de la stratégie
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Régimes de marché détectés (historique)
CREATE TABLE market_regimes (
    id SERIAL PRIMARY KEY,
    pair_id INTEGER REFERENCES trading_pairs(id),
    regime VARCHAR(20) NOT NULL,          -- bull / bear / ranging / transition
    confidence DECIMAL(5,4) NOT NULL,     -- Confiance dans la détection (0-1)
    detected_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,                 -- NULL si régime actif
    duration_candles INTEGER,             -- Durée en nombre de bougies
    indicators_snapshot JSONB,            -- État des indicateurs à la détection
    created_at TIMESTAMPTZ DEFAULT NOW()
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

// Channel: regime
{
  "timestamp": "2026-02-11T14:29:55Z",
  "pair": "BTCUSDT",
  "regime": "bull",
  "previous_regime": "ranging",
  "confidence": 0.85,
  "duration_candles": 0,
  "detection_indicators": {
    "adx": 32.5,
    "ema_alignment": "bullish",
    "macd_trend": "positive",
    "choppiness": 45.2
  }
}

// Channel: signals
{
  "timestamp": "2026-02-11T14:30:01Z",
  "pair": "BTCUSDT",
  "action": "buy",
  "confidence": 0.78,
  "regime": "bull",
  "specialist": "bull_bot",
  "risk_profile": "aggressive",
  "target_bot": "bull_bot_aggressive"
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
│   │   ├── portfolio_manager.py      # Gestionnaire de portefeuille
│   │   └── market_regime_detector.py # Détecteur de régime de marché
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
│   │   ├── adx.py                    # ADX (Average Directional Index)
│   │   ├── support_resistance.py
│   │   ├── fear_greed.py
│   │   ├── choppiness.py
│   │   └── google_trends.py
│   │
│   ├── strategies/                   # Stratégies de décision
│   │   ├── base.py                   # BaseStrategy (ABC)
│   │   ├── conservative.py           # Profil de risque sécuritaire
│   │   ├── aggressive.py             # Profil de risque agressif
│   │   ├── bull_market.py            # Spécialiste marché haussier
│   │   ├── bear_market.py            # Spécialiste marché baissier
│   │   └── range_market.py           # Spécialiste latéralisation
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
│   │   ├── market_regime.py          # Régimes de marché
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
