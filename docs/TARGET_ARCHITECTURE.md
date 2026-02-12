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

**Rôle** : Déterminer la condition actuelle du marché (haussier, baissier, latéralisation) pour activer le bot spécialiste le plus adapté. Fonctionne en **deux modes** (temps réel et batch) et analyse **top-down** du timeframe le plus haut vers le plus bas.

#### Mode dual : Real-time & Batch

```python
class DataMode(Enum):
    REALTIME = "realtime"  # Données au fil de l'eau (exchange WebSocket/polling)
    BATCH = "batch"        # Données historiques (DataFrame complet)

class MarketRegime(Enum):
    """Régimes de marché détectés."""
    BULL = "bull"              # Tendance haussière confirmée
    BEAR = "bear"              # Tendance baissière confirmée
    RANGING = "ranging"        # Latéralisation / consolidation
    TRANSITION = "transition"  # Phase de transition (incertain)

class MarketRegimeDetector:
    """Détecte le régime de marché — dual mode (realtime + batch).

    Principe fondamental : analyse TOP-DOWN.
    Le régime est d'abord déterminé sur le timeframe le plus haut (Monthly),
    puis affiné en descendant (Weekly → Daily → Intraday → Scalping).
    Le timeframe haut donne la TENDANCE MAJEURE, le timeframe bas donne le TIMING.
    """

    def __init__(self, config: RegimeConfig):
        self.lookback_period: int = 50
        self.confirmation_candles: int = 3
        self.adx_threshold: float = 25.0
        self.chop_threshold: float = 61.8
        self.timeframe_hierarchy: list[Timeframe] = [
            Timeframe.MONTHLY,   # Tendance primaire (poids: 40%)
            Timeframe.WEEKLY,    # Tendance secondaire (poids: 25%)
            Timeframe.DAILY,     # Tendance intermédiaire (poids: 20%)
            Timeframe.INTRADAY,  # Contexte court terme (poids: 10%)
            Timeframe.SCALPING,  # Timing précis (poids: 5%)
        ]
        self.timeframe_weights: dict[Timeframe, float] = {
            Timeframe.MONTHLY: 0.40,
            Timeframe.WEEKLY: 0.25,
            Timeframe.DAILY: 0.20,
            Timeframe.INTRADAY: 0.10,
            Timeframe.SCALPING: 0.05,
        }

    # --- MODE REAL-TIME ---
    def detect_realtime(
        self,
        candle: OHLCVCandle,
        timeframe: Timeframe
    ) -> RegimeSnapshot:
        """Traite une bougie en temps réel et met à jour l'état interne.
        Appelé à chaque nouvelle bougie reçue de l'exchange."""

    # --- MODE BATCH ---
    def detect_batch(
        self,
        datasets: dict[Timeframe, pd.DataFrame]
    ) -> list[RegimeSegment]:
        """Analyse un DataFrame complet et retourne les segments de régime.
        Utilisé par le BacktestEngine pour découper les données historiques."""

    # --- ANALYSE TOP-DOWN ---
    def detect_top_down(
        self,
        datasets: dict[Timeframe, pd.DataFrame],
        current_index: int
    ) -> TopDownAnalysis:
        """Analyse top-down : commence par Monthly, descend jusqu'à Scalping.
        Chaque timeframe confirme ou infirme le régime du timeframe supérieur."""

    def get_regime_confidence(self) -> float:
        """Confiance dans le régime détecté (0.0 - 1.0)."""

    def get_regime_duration(self) -> int:
        """Nombre de bougies dans le régime actuel."""

    def get_regime_per_timeframe(self) -> dict[Timeframe, MarketRegime]:
        """Retourne le régime détecté par timeframe (pour analyse divergente)."""
```

#### Analyse top-down multi-timeframe

```
ANALYSE TOP-DOWN (du plus haut au plus bas)
═══════════════════════════════════════════

Monthly ──► BULL (EMA20 > EMA50, MACD+, ADX=32)      Poids: 40%
   │
   ▼
Weekly  ──► BULL (confirme, Higher Highs)              Poids: 25%
   │
   ▼
Daily   ──► RANGING (consolidation temporaire)         Poids: 20%
   │
   ▼
Intraday──► BEAR (pullback en cours)                   Poids: 10%
   │
   ▼
Scalping──► BEAR (vente court terme)                   Poids: 5%


Score pondéré:
  BULL  = 0.40×1 + 0.25×1 + 0.20×0 + 0.10×0 + 0.05×0 = 0.65
  BEAR  = 0.40×0 + 0.25×0 + 0.20×0 + 0.10×1 + 0.05×1 = 0.15
  RANGE = 0.40×0 + 0.25×0 + 0.20×1 + 0.10×0 + 0.05×0 = 0.20

RÉSULTAT: BULL (confiance 65%) — le pullback intraday est une
OPPORTUNITÉ D'ACHAT pour le Bull Bot, pas un signal baissier.

DÉCISION PAR TIMEFRAME:
  ├── Monthly/Weekly : Le Bull Bot prend des positions long terme
  ├── Daily : Le Range Bot peut jouer la consolidation
  └── Intraday/Scalping : Le Bull Bot attend le rebond pour entrer
```

**Principe clé** : Un régime BEAR sur un timeframe bas dans un contexte BULL sur les timeframes hauts = **pullback/opportunité d'achat**, pas un retournement. C'est le timeframe haut qui prime.

#### Résultats typés

```python
@dataclass
class RegimeSnapshot:
    """État du régime à un instant T (mode real-time)."""
    regime: MarketRegime
    confidence: float
    per_timeframe: dict[Timeframe, MarketRegime]
    dominant_timeframe: Timeframe  # Le TF qui a le plus de poids dans la décision
    timestamp: datetime

@dataclass
class RegimeSegment:
    """Segment temporel d'un régime (mode batch/backtest)."""
    regime: MarketRegime
    start_index: int
    end_index: int
    start_date: datetime
    end_date: datetime
    confidence: float
    per_timeframe: dict[Timeframe, MarketRegime]
    duration_candles: int

@dataclass
class TopDownAnalysis:
    """Résultat de l'analyse top-down multi-timeframe."""
    global_regime: MarketRegime
    global_confidence: float
    per_timeframe: dict[Timeframe, MarketRegime]
    per_timeframe_confidence: dict[Timeframe, float]
    weighted_scores: dict[MarketRegime, float]
    recommendation: str  # ex: "BULL pullback — buy opportunity on Daily"
    trading_timeframes: dict[Timeframe, MarketRegime]  # Régime effectif par TF pour les bots
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
                    ┌──────────┬──────────┬─────────────┬────────────────┐
                    │ Safe (x1)│Aggro (x1)│Safe Lev (x3)│Aggro Lev (x10)│
    ┌───────────────┼──────────┼──────────┼─────────────┼────────────────┤
    │ Bull Bot      │ Bull+Safe│Bull+Aggro│ Bull+SafeLev│ Bull+AggroLev  │
    │ Bear Bot      │ Bear+Safe│Bear+Aggro│ Bear+SafeLev│ Bear+AggroLev  │
    │ Range Bot     │Range+Safe│Range+Aggr│Range+SafeLev│Range+AggroLev  │
    └───────────────┴──────────┴──────────┴─────────────┴────────────────┘

    → 12 combinaisons possibles (4 actives à la fois selon le régime)
    → Le profil de risque module la TAILLE de la position + le LEVIER
    → La stratégie de marché module la LOGIQUE d'entrée/sortie
    → Le DataProvider alimente indifféremment en live ou en backtest
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

### 4. DataProvider & Backtest Engine

#### 4a. DataProvider (Fournisseur de données dual-mode)

**Problème résolu** : Les bots sont conçus pour recevoir des données au fil de l'eau (temps réel). Comment les alimenter avec un DataFrame historique sans réécrire toute la logique ?

**Solution** : Un `DataProvider` abstrait avec deux implémentations qui exposent la **même interface**. Les bots ne savent pas s'ils consomment des données live ou historiques.

```python
class DataProvider(ABC):
    """Interface unifiée : les bots consomment des données
    sans savoir si c'est du live ou du batch."""

    @abstractmethod
    async def get_next_candle(self, timeframe: Timeframe) -> Optional[OHLCVCandle]:
        """Retourne la prochaine bougie (bloquant en live, itératif en batch)."""

    @abstractmethod
    async def get_window(self, timeframe: Timeframe, size: int) -> pd.DataFrame:
        """Retourne les N dernières bougies (pour le calcul d'indicateurs)."""

    @abstractmethod
    def get_current_price(self) -> Decimal:
        """Prix actuel (dernière close en batch, prix live en realtime)."""

    @abstractmethod
    def get_available_timeframes(self) -> list[Timeframe]:
        """Timeframes disponibles."""


class RealtimeDataProvider(DataProvider):
    """Mode temps réel — données depuis l'exchange."""

    def __init__(self, exchange: BaseExchange, pairs: list[str]):
        self.exchange = exchange
        self._buffers: dict[Timeframe, deque[OHLCVCandle]] = {}

    async def get_next_candle(self, timeframe: Timeframe) -> Optional[OHLCVCandle]:
        """Attend la prochaine bougie via WebSocket/polling."""

    async def get_window(self, timeframe: Timeframe, size: int) -> pd.DataFrame:
        """Retourne les N dernières bougies depuis le buffer ou l'API."""


class BatchDataProvider(DataProvider):
    """Mode batch — données depuis un DataFrame historique.

    Simule le passage du temps en itérant sur les lignes du DataFrame.
    Supporte plusieurs timeframes simultanément.
    """

    def __init__(self, datasets: dict[Timeframe, pd.DataFrame]):
        self.datasets = datasets                    # {Timeframe: DataFrame complet}
        self._cursors: dict[Timeframe, int] = {}    # Position courante par TF
        self._synced: bool = True                    # Synchronisation inter-TF

    async def get_next_candle(self, timeframe: Timeframe) -> Optional[OHLCVCandle]:
        """Avance le curseur d'une bougie et retourne la bougie courante.
        Retourne None quand le DataFrame est épuisé."""
        cursor = self._cursors[timeframe]
        if cursor >= len(self.datasets[timeframe]):
            return None
        candle = self._row_to_candle(self.datasets[timeframe].iloc[cursor])
        self._cursors[timeframe] += 1
        return candle

    async def get_window(self, timeframe: Timeframe, size: int) -> pd.DataFrame:
        """Retourne les N bougies AVANT le curseur courant (sliding window).
        C'est la clé : le bot ne voit que le passé, jamais le futur."""
        cursor = self._cursors[timeframe]
        start = max(0, cursor - size)
        return self.datasets[timeframe].iloc[start:cursor].copy()

    def advance_all(self) -> bool:
        """Avance tous les curseurs d'un pas (synchronisé par timestamp).
        Gère le fait que 1 bougie Daily = 24 bougies Intraday = 96 bougies 15min."""
```

**Flux du backtest** :

```
DataFrame historique (ex: 2 ans de données BTC)
    │
    ▼
BatchDataProvider
    │
    ├── datasets = {
    │       Monthly: DataFrame[24 rows],
    │       Weekly:  DataFrame[104 rows],
    │       Daily:   DataFrame[730 rows],
    │       Intraday:DataFrame[17520 rows],
    │       Scalping:DataFrame[70080 rows]
    │   }
    │
    ├── Synchronisation temporelle :
    │   Quand le curseur Daily avance d'1 jour,
    │   le curseur Intraday avance de 24 bougies,
    │   le curseur Scalping avance de 96 bougies.
    │
    ▼
Les bots reçoivent les données bougie par bougie
via get_next_candle() — identique au mode live.
Ils ne voient JAMAIS les données futures (sliding window).
```

#### 4b. BacktestRouter (Routeur par régime)

**Problème résolu** : En backtest, il faut automatiquement router les segments de données vers le bon bot spécialiste (Bull, Bear, Range) exactement comme le ferait le MarketRegimeDetector en live.

```python
class BacktestRouter:
    """Route les données historiques vers les bons bots spécialistes.

    1. Le MarketRegimeDetector analyse le DataFrame en mode batch
    2. Il découpe les données en segments par régime
    3. Chaque segment est soumis au bot spécialiste correspondant
    4. Les résultats sont agrégés pour le rapport final
    """

    def __init__(
        self,
        regime_detector: MarketRegimeDetector,
        specialist_bots: dict[MarketRegime, BaseStrategy],
        indicator_engine: IndicatorEngine
    ):
        self.regime_detector = regime_detector
        self.specialist_bots = specialist_bots
        self.indicator_engine = indicator_engine

    def run(
        self,
        datasets: dict[Timeframe, pd.DataFrame],
        risk_profiles: list[RiskProfile],
        initial_capital: Decimal,
        config: BacktestConfig
    ) -> BacktestReport:
        """Exécute le backtest complet avec routage par régime.

        Étapes :
        1. Créer un BatchDataProvider à partir des datasets
        2. Pour chaque pas de temps (bougie du TF principal) :
           a. Le MarketRegimeDetector fait l'analyse top-down
           b. Le régime détermine quel bot spécialiste est actif
           c. Le bot actif reçoit les indicateurs et prend sa décision
           d. L'Order Engine simule l'exécution
           e. Le Portfolio Manager gère la réallocation si nécessaire
        3. En cas de changement de régime : transition propre
        4. Agréger les résultats
        """

    def _segment_by_regime(
        self,
        datasets: dict[Timeframe, pd.DataFrame]
    ) -> list[RegimeSegment]:
        """Découpe les données en segments par régime détecté.
        Utilise l'analyse top-down multi-timeframe."""

    def _run_segment(
        self,
        segment: RegimeSegment,
        bot: BaseStrategy,
        data_provider: BatchDataProvider
    ) -> list[SimulatedTrade]:
        """Exécute un segment sur le bot spécialiste approprié."""


@dataclass
class BacktestConfig:
    fees: Decimal = Decimal("0.001")       # 0.1% par défaut
    slippage: Decimal = Decimal("0.0005")  # 0.05% par défaut
    primary_timeframe: Timeframe = Timeframe.DAILY  # TF de référence pour l'itération
    use_top_down: bool = True              # Analyse top-down multi-TF

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

@dataclass
class BacktestReport:
    """Rapport complet incluant l'analyse par régime."""
    overall: BacktestResult                           # Performance globale
    per_regime: dict[MarketRegime, BacktestResult]    # Performance par régime
    per_bot: dict[str, BacktestResult]                # Performance par bot spécialiste
    per_risk_profile: dict[str, BacktestResult]       # Performance par profil de risque
    regime_segments: list[RegimeSegment]               # Timeline des régimes détectés
    regime_transitions: int                            # Nombre de changements de régime
    regime_distribution: dict[MarketRegime, float]    # % du temps dans chaque régime
    reallocations: list[ReallocationEvent]             # Historique des réallocations
```

**Exemple concret : backtest sur 2 ans de BTC** :

```
Données: BTC/USDT 2022-01-01 → 2024-01-01

Le BacktestRouter analyse et découpe automatiquement :

Segment 1: 2022-01 → 2022-05  BEAR    ──► BearMarketStrategy
  ├── Bear Bot Safe : -3.2% (SL serrés, peu de trades)
  └── Bear Bot Aggro: -8.1% (plus de trades, mais bien limité)

Segment 2: 2022-06 → 2022-11  RANGING ──► RangeStrategy
  ├── Range Bot Safe : +4.5% (mean reversion prudent)
  └── Range Bot Aggro: +11.2% (plus de rotations dans le range)

Segment 3: 2022-11 → 2023-01  BEAR    ──► BearMarketStrategy
  ├── Bear Bot Safe : -1.8%
  └── Bear Bot Aggro: -5.4%

Segment 4: 2023-01 → 2023-07  BULL    ──► BullMarketStrategy
  ├── Bull Bot Safe : +18.3% (trend following prudent)
  └── Bull Bot Aggro: +42.7% (trend following agressif)

Segment 5: 2023-07 → 2023-10  RANGING ──► RangeStrategy
  ...

RAPPORT FINAL :
  ├── Performance globale : +38.5%
  ├── Meilleur bot : Bull Bot Aggro (+42.7% sur segment bull)
  ├── Pire segment : Bear Aggro segment 1 (-8.1%)
  ├── Distribution : 35% Bull, 25% Bear, 35% Range, 5% Transition
  ├── Réallocations : 12 (total 450$ Aggro → Safe)
  └── Le système dual Safe/Aggro a protégé le capital en bear
```

**Améliorations vs existant** :
- **DataProvider dual-mode** : même interface pour live et backtest
- **Routage automatique par régime** : chaque segment va au bon bot
- **Analyse top-down** : le backtest utilise la vraie hiérarchie de timeframes
- Prise en compte des **frais** et du **slippage**
- Calcul du **Sharpe Ratio**, **Max Drawdown**, **Profit Factor**
- Rapport **par régime**, **par bot**, **par profil de risque**
- Courbe d'**equity** avec zones colorées par régime

---

### 5. Portfolio Manager (Gestionnaire de portefeuille)

**Rôle** : Gérer les profils de risque (sécuritaire + agressif), les bots spécialistes (bull, bear, range), la réallocation des gains et l'orchestration par régime de marché.

```python
class PortfolioManager:
    """Gestionnaire de portefeuille multi-bots avec orchestration par régime."""

    def __init__(self, config: PortfolioConfig):
        # 4 Profils de risque (spot + levier)
        self.risk_profiles: dict[str, RiskProfile] = {
            "safe":              RiskProfile(ratio=0.01, allocation=0.40, leverage=1),
            "aggressive":        RiskProfile(ratio=0.03, allocation=0.25, leverage=1),
            "safe_leverage":     RiskProfile(ratio=0.01, allocation=0.20, leverage=3),
            "aggressive_leverage":RiskProfile(ratio=0.03, allocation=0.15, leverage=10),
        }

        # Bots spécialistes (1 par régime × profil de risque = 12 combinaisons)
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

#### Les 4 profils de risque

```python
@dataclass
class RiskProfile:
    name: str
    ratio: float          # % du capital risqué par trade
    allocation: float     # % du capital total alloué
    leverage: int         # Effet de levier (1 = spot)
    max_drawdown: float   # DD max avant pause
    market_type: str      # "spot" ou "futures"
```

| Profil | Risque/trade | Allocation | Levier | Marché | Max DD | Description |
|--------|-------------|-----------|--------|--------|--------|-------------|
| **Safe** | 1% | 40% | x1 | Spot | 10% | Conservateur, pas de levier |
| **Aggressive** | 3% | 25% | x1 | Spot | 20% | Plus de risque, spot uniquement |
| **Safe Leverage** | 1% | 20% | x3 | Futures | 8% | Prudent mais avec levier modéré |
| **Aggressive Leverage** | 3% | 15% | x10 | Futures | 15% | Maximum de risque + levier élevé |

**Pourquoi ces allocations ?**
- Les profils **spot** (Safe + Aggressive = 65%) gèrent la majorité du capital → stabilité
- Les profils **leverage** (Safe Lev + Aggro Lev = 35%) gèrent une fraction → exposition amplifiée avec capital limité
- Le levier x3 safe = rendements amplifiés mais maîtrisés (liquidation lointaine)
- Le levier x10 aggro = rendements maximum, mais capital réduit (15%) pour limiter les dégâts

**Impact du levier sur le trading** :
```
Exemple : BTC @ 60,000$, capital alloué = 150$ (profil Aggro Lev x10)

Position effective = 150$ × 10 = 1,500$ de BTC
Risque par trade (3%) = 4.50$ de capital réel

Si BTC monte de 2% :
  └── Sans levier : +3.00$ (+2%)
  └── Avec x10 :    +30.00$ (+20%)

Si BTC baisse de 2% :
  └── Sans levier : -3.00$ (-2%)
  └── Avec x10 :    -30.00$ (-20%)

Prix de liquidation (x10) ≈ 54,000$ (-10%)
  → Le SL doit TOUJOURS être placé AVANT le prix de liquidation
  → Marge de sécurité : SL à -7% max pour x10 (liquidation à -10%)
```

**Sécurités spécifiques au levier** :
- SL **obligatoire** et placé avant le prix de liquidation (marge de sécurité 30%)
- Max drawdown **réduit** pour les profils leverage (8% safe lev, 15% aggro lev)
- **Pas de levier en BEAR market** pour le profil Safe Leverage (risque ÷ 2 automatique)
- Les profils leverage utilisent les **Futures** (pas le spot avec margin)
- Monitoring du **funding rate** : si trop élevé, réduire les positions

**Matrice complète : 3 spécialistes × 4 profils = 12 combinaisons** :
```
                    ┌────────────┬────────────┬──────────────┬──────────────────┐
                    │  Safe (x1) │ Aggro (x1) │ Safe Lev (x3)│ Aggro Lev (x10) │
┌───────────────────┼────────────┼────────────┼──────────────┼──────────────────┤
│ Bull Bot          │  Bull+Safe │ Bull+Aggro │ Bull+SafeLev │  Bull+AggroLev   │
│ Bear Bot          │  Bear+Safe │ Bear+Aggro │ Bear+SafeLev │  Bear+AggroLev   │
│ Range Bot         │ Range+Safe │Range+Aggro │Range+SafeLev │ Range+AggroLev   │
└───────────────────┴────────────┴────────────┴──────────────┴──────────────────┘

12 combinaisons, mais seules 4 sont actives à la fois
(1 régime actif × 4 profils de risque)
```

**Réallocation** : les gains des profils à levier sont redistribués vers les profils sans levier.
```
Flux de réallocation (configurable) :
  Aggressive Leverage ──(30% gains)──► Safe
  Aggressive          ──(30% gains)──► Safe
  Safe Leverage        ──(20% gains)──► Safe

Le profil Safe est le "coffre-fort" qui accumule les gains.
En cas de pertes graves sur les profils levier, le Safe est protégé.
```

**Mécanique de réduction de risque** :
```
Pertes consécutives ≥ 3 → Risque ÷ 2 (et levier ÷ 2 pour profils leverage)
Pertes consécutives ≥ 5 → Pause du profil (et fermeture positions leverage)
2 gains consécutifs     → Restauration progressive
Applicable par bot spécialiste ET par profil de risque

Spécifique au levier :
  - Si funding rate > 0.1% → Réduire les positions leverage de 50%
  - Si volatilité > seuil  → Réduire le levier automatiquement (x10→x5→x3)
  - Si prix approche liquidation → Fermeture d'urgence AVANT liquidation
```

**Gestion des transitions de régime** :
```
Régime change de BULL → BEAR :
  1. Les Bull Bots ferment leurs positions (ordres de sortie progressifs)
  2. Les profils LEVERAGE ferment en PRIORITÉ (risque de liquidation)
  3. Période tampon (TRANSITION) : pas de nouveaux trades
  4. Les Bear Bots s'activent avec le capital disponible
  5. En BEAR, le Safe Leverage passe automatiquement à x1 (pas de levier)
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
