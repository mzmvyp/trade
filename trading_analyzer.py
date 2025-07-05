# trading_analyzer.py - Sistema de Análise Técnica Corrigido
import json
import time
import threading
import hashlib
from datetime import datetime, timedelta
import sqlite3
import logging
from collections import deque, defaultdict

# Configurar logging compatível
class SafeFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        replacements = {
            '🚀': '[START]', '📊': '[DATA]', '✅': '[OK]', '❌': '[ERROR]',
            '🛑': '[STOP]', '💰': '[BTC]', '📈': '[TRADE]', '🔄': '[API]',
            '🎯': '[TARGET]', '🧹': '[CLEAN]', '⏰': '[TIME]', '🔧': '[FIX]'
        }
        for emoji, replacement in replacements.items():
            msg = msg.replace(emoji, replacement)
        return msg

logger = logging.getLogger(__name__)

# ==================== TECHNICAL INDICATORS ====================
class TechnicalIndicators:
    """Implementações próprias dos indicadores técnicos"""
    
    @staticmethod
    def sma(prices, period):
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    @staticmethod
    def ema(prices, period):
        if len(prices) < period:
            return None
        sma = sum(prices[:period]) / period
        multiplier = 2 / (period + 1)
        ema_values = [sma]
        for i in range(period, len(prices)):
            ema_value = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema_value)
        return ema_values[-1] if ema_values else None
    
    @staticmethod
    def rsi(prices, period=14):
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def stochastic(highs, lows, closes, k_period=14, d_period=3):
        if len(closes) < k_period:
            return None, None
        lowest_low = min(lows[-k_period:])
        highest_high = max(highs[-k_period:])
        if highest_high == lowest_low:
            k_percent = 50
        else:
            k_percent = 100 * (closes[-1] - lowest_low) / (highest_high - lowest_low)
        d_percent = k_percent  # Simplificado
        return k_percent, d_percent
    
    @staticmethod
    def macd(prices, fast_period=12, slow_period=26, signal_period=9):
        if len(prices) < slow_period:
            return None, None, None
        ema_fast = TechnicalIndicators.ema(prices, fast_period)
        ema_slow = TechnicalIndicators.ema(prices, slow_period)
        if ema_fast is None or ema_slow is None:
            return None, None, None
        macd_line = ema_fast - ema_slow
        signal_line = macd_line * 0.9  # Simplificado
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices, period=20, std_dev=2):
        if len(prices) < period:
            return None, None, None
        sma = TechnicalIndicators.sma(prices, period)
        if sma is None:
            return None, None, None
        variance = sum((price - sma) ** 2 for price in prices[-period:]) / period
        std = variance ** 0.5
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        return upper_band, sma, lower_band

# ==================== SIGNAL UNIQUENESS SYSTEM ====================
class SignalUniquenesSystem:
    """Sistema para garantir unicidade de sinais"""
    
    def __init__(self):
        self.signal_hashes = set()
        self.pattern_cooldowns = defaultdict(datetime)
        self.cooldown_periods = {
            'DOUBLE_BOTTOM': timedelta(hours=4),
            'HEAD_AND_SHOULDERS': timedelta(hours=6),
            'TRIANGLE_BREAKOUT_UP': timedelta(hours=2),
            'TRIANGLE_BREAKOUT_DOWN': timedelta(hours=2),
            'INDICATORS_BUY': timedelta(minutes=30),
            'INDICATORS_SELL': timedelta(minutes=30)
        }
    
    def generate_signal_hash(self, pattern_data, current_price):
        """Gera hash único para o sinal"""
        entry = round(pattern_data['entry'], 2)
        target = round(pattern_data['target'], 2)
        stop = round(pattern_data['stop'], 2)
        current = round(current_price, 2)
        hash_string = f"{pattern_data['pattern']}_{entry}_{target}_{stop}_{current}"
        return hashlib.md5(hash_string.encode()).hexdigest()[:12]
    
    def is_signal_unique(self, signal_hash):
        """Verifica se o sinal é único"""
        return signal_hash not in self.signal_hashes
    
    def add_signal_hash(self, signal_hash):
        """Adiciona hash à lista"""
        self.signal_hashes.add(signal_hash)
        if len(self.signal_hashes) > 1000:
            self.signal_hashes = set(list(self.signal_hashes)[-800:])
    
    def is_pattern_in_cooldown(self, pattern_type):
        """Verifica cooldown"""
        if pattern_type not in self.pattern_cooldowns:
            return False
        cooldown_period = self.cooldown_periods.get(pattern_type, timedelta(hours=1))
        return datetime.now() - self.pattern_cooldowns[pattern_type] < cooldown_period
    
    def set_pattern_cooldown(self, pattern_type):
        """Define cooldown"""
        self.pattern_cooldowns[pattern_type] = datetime.now()

# ==================== SIGNAL VALIDATOR ====================
class SignalValidator:
    """Validador rigoroso de sinais"""
    
    @staticmethod
    def validate_signal_parameters(pattern_data, current_price, indicators=None):
        """Valida parâmetros do sinal"""
        try:
            entry = pattern_data['entry']
            target = pattern_data['target']
            stop = pattern_data['stop']
            
            if any(price <= 0 for price in [entry, target, stop, current_price]):
                return False, "Preços devem ser positivos"
            
            price_diff_pct = abs(entry - current_price) / current_price * 100
            if price_diff_pct > 2.0:
                return False, f"Entry muito distante ({price_diff_pct:.2f}%)"
            
            if pattern_data['pattern'].endswith('_BUY') or pattern_data['pattern'] == 'DOUBLE_BOTTOM':
                if target <= entry:
                    return False, "Target deve ser maior que entry"
                if stop >= entry:
                    return False, "Stop deve ser menor que entry"
            else:
                if target >= entry:
                    return False, "Target deve ser menor que entry"
                if stop <= entry:
                    return False, "Stop deve ser maior que entry"
            
            risk = abs(entry - stop)
            reward = abs(target - entry)
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            if risk_reward_ratio < 1.5:
                return False, f"Risk/Reward baixo ({risk_reward_ratio:.2f})"
            
            risk_pct = (risk / entry) * 100
            if risk_pct > 5.0:
                return False, f"Risk alto ({risk_pct:.2f}%)"
            
            return True, "Válido"
            
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    @staticmethod
    def validate_market_conditions(indicators):
        """Valida condições de mercado"""
        if not indicators:
            return False, "Indicadores não disponíveis"
        
        required = ['RSI', 'SMA_12', 'SMA_30']
        missing = [ind for ind in required if ind not in indicators or indicators[ind] is None]
        
        if missing:
            return False, f"Indicadores em falta: {', '.join(missing)}"
        
        return True, "Condições adequadas"

# ==================== MODELS ====================
class TradingSignal:
    """Modelo aprimorado para sinais"""
    def __init__(self, timestamp, price, pattern_type, entry_price, target_price, 
                 stop_loss, confidence, indicators_used, signal_hash, status='ACTIVE'):
        self.timestamp = timestamp
        self.price = price
        self.pattern_type = pattern_type
        self.entry_price = entry_price
        self.target_price = target_price
        self.stop_loss = stop_loss
        self.confidence = confidence
        self.indicators_used = indicators_used
        self.signal_hash = signal_hash
        self.status = status
        self.created_at = timestamp
        self.closed_at = None
        self.profit_loss = 0.0
        self.activated = False
        self.risk_reward_ratio = self._calculate_risk_reward()
        
    def _calculate_risk_reward(self):
        """Calcula ratio risk/reward"""
        try:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.target_price - self.entry_price)
            return reward / risk if risk > 0 else 0
        except:
            return 0
        
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'pattern_type': self.pattern_type,
            'entry_price': self.entry_price,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'confidence': self.confidence,
            'indicators_used': self.indicators_used,
            'signal_hash': self.signal_hash,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'profit_loss': self.profit_loss,
            'activated': self.activated,
            'risk_reward_ratio': round(self.risk_reward_ratio, 2)
        }

class PriceData:
    """Modelo para dados OHLCV"""
    def __init__(self, timestamp, open_price, high, low, close, volume):
        self.timestamp = timestamp
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

# ==================== TECHNICAL ANALYSIS ENGINE ====================
class TechnicalAnalysisEngine:
    """Engine de análise técnica"""
    
    def __init__(self, lookback_periods=200):
        self.lookback_periods = lookback_periods
        self.price_history = deque(maxlen=lookback_periods)
        self.indicators = TechnicalIndicators()
        self.last_analysis_time = None
        self.min_analysis_interval = 30
        
    def add_price_data(self, price_data):
        """Adiciona dados de preço"""
        self.price_history.append(price_data)
        
    def can_analyze(self):
        """Verifica se pode analisar"""
        if self.last_analysis_time is None:
            return True
        time_since_last = (datetime.now() - self.last_analysis_time).total_seconds()
        return time_since_last >= self.min_analysis_interval
        
    def mark_analysis_done(self):
        """Marca análise feita"""
        self.last_analysis_time = datetime.now()
        
    def get_price_arrays(self):
        """Converte histórico para arrays"""
        if len(self.price_history) < 20:
            return None, None, None, None, None
            
        opens = [p.open for p in self.price_history]
        highs = [p.high for p in self.price_history]
        lows = [p.low for p in self.price_history]
        closes = [p.close for p in self.price_history]
        volumes = [p.volume for p in self.price_history]
        
        return opens, highs, lows, closes, volumes
    
    def calculate_indicators(self):
        """Calcula indicadores técnicos"""
        opens, highs, lows, closes, volumes = self.get_price_arrays()
        if closes is None:
            return {}
            
        indicators = {}
        
        try:
            # Médias Móveis
            indicators['SMA_12'] = self.indicators.sma(closes, 12)
            indicators['SMA_30'] = self.indicators.sma(closes, 30)
            indicators['SMA_60'] = self.indicators.sma(closes, 60)
            
            # EMA
            indicators['EMA_12'] = self.indicators.ema(closes, 12)
            indicators['EMA_26'] = self.indicators.ema(closes, 26)
            
            # RSI
            indicators['RSI'] = self.indicators.rsi(closes, 14)
            
            # Stochastic
            stoch_k, stoch_d = self.indicators.stochastic(highs, lows, closes)
            indicators['STOCH_K'] = stoch_k
            indicators['STOCH_D'] = stoch_d
            
            # MACD
            macd, signal, histogram = self.indicators.macd(closes)
            indicators['MACD'] = macd
            indicators['MACD_SIGNAL'] = signal
            indicators['MACD_HISTOGRAM'] = histogram
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(closes)
            indicators['BB_UPPER'] = bb_upper
            indicators['BB_MIDDLE'] = bb_middle
            indicators['BB_LOWER'] = bb_lower
            
            # Volume
            indicators['VOLUME_SMA'] = self.indicators.sma(volumes, 20)
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores: {e}")
            
        return indicators
    
    def detect_double_bottom(self):
        """Detecta padrão duplo fundo"""
        if len(self.price_history) < 80:
            return None
            
        closes = [p.close for p in self.price_history]
        lows = [p.low for p in self.price_history]
        
        recent_lows = []
        for i in range(20, len(lows) - 20):
            window_lows = lows[i-20:i+20]
            if lows[i] == min(window_lows):
                recent_lows.append((i, lows[i]))
        
        if len(recent_lows) >= 2:
            first_low = recent_lows[-2]
            second_low = recent_lows[-1]
            
            time_diff = second_low[0] - first_low[0]
            if time_diff < 20:
                return None
            
            price_diff = abs(first_low[1] - second_low[1]) / first_low[1]
            if price_diff < 0.015:
                peak_between = max(lows[first_low[0]:second_low[0]])
                target_height = peak_between - min(first_low[1], second_low[1])
                
                if target_height / second_low[1] < 0.02:
                    return None
                
                entry_price = second_low[1] * 1.008
                target_price = entry_price + target_height * 0.8
                stop_price = second_low[1] * 0.985
                
                return {
                    'pattern': 'DOUBLE_BOTTOM',
                    'entry': entry_price,
                    'target': target_price,
                    'stop': stop_price,
                    'confidence': min(85, 50 + (1 - price_diff) * 35)
                }
        return None
    
    def analyze_indicators_confluence(self, indicators):
        """Analisa confluência de indicadores"""
        signals = []
        current_price = self.price_history[-1].close if self.price_history else 0
        
        if not indicators or current_price == 0:
            return signals
        
        buy_score = 0
        sell_score = 0
        total_indicators = 0
        
        # RSI
        if indicators.get('RSI'):
            rsi = indicators['RSI']
            total_indicators += 2
            if rsi < 25:
                buy_score += 2
            elif rsi < 35:
                buy_score += 1
            elif rsi > 75:
                sell_score += 2
            elif rsi > 65:
                sell_score += 1
        
        # Stochastic
        if indicators.get('STOCH_K') and indicators.get('STOCH_D'):
            stoch_k, stoch_d = indicators['STOCH_K'], indicators['STOCH_D']
            total_indicators += 1.5
            if stoch_k < 15 and stoch_d < 15:
                buy_score += 1.5
            elif stoch_k > 85 and stoch_d > 85:
                sell_score += 1.5
        
        # MACD
        if indicators.get('MACD') and indicators.get('MACD_SIGNAL'):
            macd, signal = indicators['MACD'], indicators['MACD_SIGNAL']
            total_indicators += 2
            if macd > signal and macd > 0:
                buy_score += 2
            elif macd < signal and macd < 0:
                sell_score += 2
            elif macd > signal:
                buy_score += 1
            else:
                sell_score += 1
        
        # Moving Averages
        if indicators.get('SMA_12') and indicators.get('SMA_30'):
            sma12, sma30 = indicators['SMA_12'], indicators['SMA_30']
            total_indicators += 1.5
            if sma12 > sma30 and current_price > sma12:
                buy_score += 1.5
            elif sma12 < sma30 and current_price < sma12:
                sell_score += 1.5
        
        # Bollinger Bands
        if indicators.get('BB_LOWER') and indicators.get('BB_UPPER'):
            total_indicators += 1
            if current_price < indicators['BB_LOWER']:
                buy_score += 1
            elif current_price > indicators['BB_UPPER']:
                sell_score += 1
        
        # Calcula confluência
        if total_indicators > 0:
            buy_confluence = (buy_score / total_indicators) * 100
            sell_confluence = (sell_score / total_indicators) * 100
            
            # Gera sinal apenas com confluência alta (>60%)
            if buy_confluence > 60:
                target_multiplier = min(3, buy_confluence / 30)
                
                signals.append({
                    'pattern': 'INDICATORS_BUY',
                    'entry': current_price * 1.002,
                    'target': current_price * (1 + 0.02 * target_multiplier),
                    'stop': current_price * (1 - 0.015),
                    'confidence': min(90, buy_confluence)
                })
            elif sell_confluence > 60:
                target_multiplier = min(3, sell_confluence / 30)
                
                signals.append({
                    'pattern': 'INDICATORS_SELL',
                    'entry': current_price * 0.998,
                    'target': current_price * (1 - 0.02 * target_multiplier),
                    'stop': current_price * (1 + 0.015),
                    'confidence': min(90, sell_confluence)
                })
        
        return signals

# ==================== SIGNAL MANAGER ====================
class SignalManager:
    """Gerenciador de sinais aprimorado"""
    
    def __init__(self, db_path="data/trading_signals.db"):
        self.db_path = db_path
        self.active_signals = {}
        self.uniqueness_system = SignalUniquenesSystem()
        self.validator = SignalValidator()
        self.max_active_signals = 10
        self.init_database()
        
    def init_database(self):
        """Inicializa banco de dados"""
        import os
        os.makedirs('data', exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                price REAL,
                pattern_type TEXT,
                entry_price REAL,
                target_price REAL,
                stop_loss REAL,
                confidence INTEGER,
                indicators_used TEXT,
                signal_hash TEXT UNIQUE,
                status TEXT,
                created_at DATETIME,
                closed_at DATETIME,
                profit_loss REAL,
                activated BOOLEAN DEFAULT 0,
                risk_reward_ratio REAL
            )
        ''')
        
        # Índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signal_hash ON trading_signals(signal_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON trading_signals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON trading_signals(created_at)')
        
        conn.commit()
        conn.close()
        
        # Carrega sinais ativos
        self._load_active_signals()
        
    def _load_active_signals(self):
        """Carrega sinais ativos do banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT signal_hash, timestamp, price, pattern_type, entry_price, 
                       target_price, stop_loss, confidence, indicators_used, 
                       status, created_at, activated, risk_reward_ratio
                FROM trading_signals 
                WHERE status = 'ACTIVE'
            ''')
            
            for row in cursor.fetchall():
                signal = TradingSignal(
                    timestamp=datetime.fromisoformat(row[1]),
                    price=row[2],
                    pattern_type=row[3],
                    entry_price=row[4],
                    target_price=row[5],
                    stop_loss=row[6],
                    confidence=row[7],
                    indicators_used=row[8],
                    signal_hash=row[0],
                    status=row[9]
                )
                signal.created_at = datetime.fromisoformat(row[10])
                signal.activated = bool(row[11]) if row[11] is not None else False
                signal.risk_reward_ratio = row[12] or 0
                
                self.active_signals[row[0]] = signal
                self.uniqueness_system.add_signal_hash(row[0])
            
            conn.close()
            logger.info(f"Carregados {len(self.active_signals)} sinais ativos")
            
        except Exception as e:
            logger.error(f"Erro ao carregar sinais ativos: {e}")
        
    def can_create_signal(self, pattern_data, current_price, indicators):
        """Verifica se pode criar sinal"""
        
        if len(self.active_signals) >= self.max_active_signals:
            return False, "Limite de sinais atingido"
        
        if self.uniqueness_system.is_pattern_in_cooldown(pattern_data['pattern']):
            return False, f"Padrão {pattern_data['pattern']} em cooldown"
        
        valid, message = self.validator.validate_signal_parameters(pattern_data, current_price, indicators)
        if not valid:
            return False, f"Parâmetros inválidos: {message}"
        
        valid, message = self.validator.validate_market_conditions(indicators)
        if not valid:
            return False, f"Condições inadequadas: {message}"
        
        signal_hash = self.uniqueness_system.generate_signal_hash(pattern_data, current_price)
        if not self.uniqueness_system.is_signal_unique(signal_hash):
            return False, "Sinal duplicado"
        
        if self._has_overlapping_signal(pattern_data, current_price):
            return False, "Sobreposição detectada"
        
        return True, "Válido"
    
    def _has_overlapping_signal(self, pattern_data, current_price):
        """Verifica sobreposição"""
        entry_price = pattern_data['entry']
        
        for signal in self.active_signals.values():
            price_diff_pct = abs(signal.entry_price - entry_price) / entry_price * 100
            if price_diff_pct < 1.0:
                same_direction = (
                    (pattern_data['pattern'].endswith('_BUY') and signal.pattern_type.endswith('_BUY')) or
                    (pattern_data['pattern'].endswith('_SELL') and signal.pattern_type.endswith('_SELL')) or
                    (pattern_data['pattern'] == 'DOUBLE_BOTTOM' and signal.target_price > signal.entry_price)
                )
                
                if same_direction:
                    return True
        
        return False
    
    def create_signal(self, pattern_data, indicators_used, current_price):
        """Cria novo sinal"""
        
        can_create, reason = self.can_create_signal(pattern_data, current_price, indicators_used)
        if not can_create:
            logger.debug(f"Sinal não criado: {reason}")
            return None
        
        signal_hash = self.uniqueness_system.generate_signal_hash(pattern_data, current_price)
        
        signal = TradingSignal(
            timestamp=datetime.now(),
            price=current_price,
            pattern_type=pattern_data['pattern'],
            entry_price=pattern_data['entry'],
            target_price=pattern_data['target'],
            stop_loss=pattern_data['stop'],
            confidence=pattern_data['confidence'],
            indicators_used=json.dumps(indicators_used),
            signal_hash=signal_hash
        )
        
        self.save_signal(signal)
        self.active_signals[signal_hash] = signal
        self.uniqueness_system.add_signal_hash(signal_hash)
        self.uniqueness_system.set_pattern_cooldown(pattern_data['pattern'])
        
        logger.info(f"[OK] Novo sinal: {signal.pattern_type} - Entry: ${signal.entry_price:.2f}")
        return signal
    
    def save_signal(self, signal):
        """Salva sinal no banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO trading_signals 
                (timestamp, price, pattern_type, entry_price, target_price, stop_loss,
                 confidence, indicators_used, signal_hash, status, created_at, 
                 closed_at, profit_loss, activated, risk_reward_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.timestamp, signal.price, signal.pattern_type, signal.entry_price,
                signal.target_price, signal.stop_loss, signal.confidence,
                signal.indicators_used, signal.signal_hash, signal.status, 
                signal.created_at, signal.closed_at, signal.profit_loss,
                signal.activated, signal.risk_reward_ratio
            ))
            
            conn.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.debug(f"Sinal duplicado no banco: {signal.signal_hash}")
            else:
                logger.error(f"Erro de integridade: {e}")
        except Exception as e:
            logger.error(f"Erro ao salvar sinal: {e}")
        finally:
            conn.close()
    
    def update_signals(self, current_price):
        """Atualiza sinais ativos"""
        updated_signals = []
        
        for signal_hash, signal in list(self.active_signals.items()):
            if signal.status != 'ACTIVE':
                continue
            
            original_status = signal.status
            
            # Verifica ativação
            if not signal.activated:
                if self._check_signal_activation(signal, current_price):
                    signal.activated = True
                    logger.info(f"[TARGET] Sinal ativado: {signal.pattern_type}")
            
            # Verifica target/stop
            if signal.activated:
                if self._check_target_hit(signal, current_price):
                    signal.status = 'HIT_TARGET'
                    signal.closed_at = datetime.now()
                    signal.profit_loss = self._calculate_profit_loss(signal, signal.target_price)
                    logger.info(f"[TARGET] Target: {signal.pattern_type} - {signal.profit_loss:.2f}%")
                    
                elif self._check_stop_hit(signal, current_price):
                    signal.status = 'HIT_STOP'
                    signal.closed_at = datetime.now()
                    signal.profit_loss = self._calculate_profit_loss(signal, signal.stop_loss)
                    logger.info(f"[STOP] Stop: {signal.pattern_type} - {signal.profit_loss:.2f}%")
            
            # Verifica expiração
            max_age = timedelta(hours=48 if signal.activated else 24)
            if (datetime.now() - signal.created_at) > max_age:
                signal.status = 'EXPIRED'
                signal.closed_at = datetime.now()
                signal.profit_loss = 0
                logger.info(f"[TIME] Sinal expirado: {signal.pattern_type}")
            
            if signal.status != original_status:
                updated_signals.append(signal)
                if signal.status != 'ACTIVE':
                    del self.active_signals[signal_hash]
        
        # Atualiza no banco
        for signal in updated_signals:
            self.update_signal_in_db(signal)
            
        return updated_signals
    
    def _check_signal_activation(self, signal, current_price):
        """Verifica ativação"""
        tolerance = 0.001
        
        if signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM':
            return current_price >= signal.entry_price * (1 - tolerance)
        else:
            return current_price <= signal.entry_price * (1 + tolerance)
    
    def _check_target_hit(self, signal, current_price):
        """Verifica target"""
        if signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM':
            return current_price >= signal.target_price
        else:
            return current_price <= signal.target_price
    
    def _check_stop_hit(self, signal, current_price):
        """Verifica stop"""
        if signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM':
            return current_price <= signal.stop_loss
        else:
            return current_price >= signal.stop_loss
    
    def _calculate_profit_loss(self, signal, exit_price):
        """Calcula P&L"""
        if signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM':
            return ((exit_price - signal.entry_price) / signal.entry_price) * 100
        else:
            return ((signal.entry_price - exit_price) / signal.entry_price) * 100
    
    def update_signal_in_db(self, signal):
        """Atualiza sinal no banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trading_signals 
            SET status = ?, closed_at = ?, profit_loss = ?, activated = ?
            WHERE signal_hash = ?
        ''', (signal.status, signal.closed_at, signal.profit_loss, 
              signal.activated, signal.signal_hash))
        
        conn.commit()
        conn.close()
    
    def get_recent_signals(self, limit=50):
        """Retorna sinais recentes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trading_signals 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in results:
            signals.append({
                'id': row[0],
                'timestamp': row[1],
                'price': row[2],
                'pattern_type': row[3],
                'entry_price': row[4],
                'target_price': row[5],
                'stop_loss': row[6],
                'confidence': row[7],
                'indicators_used': row[8],
                'signal_hash': row[9],
                'status': row[10],
                'created_at': row[11],
                'closed_at': row[12],
                'profit_loss': row[13] or 0,
                'activated': bool(row[14]) if len(row) > 14 else False,
                'risk_reward_ratio': row[15] if len(row) > 15 else 0
            })
        
        return signals
    
    def get_pattern_statistics(self):
        """Estatísticas por padrão"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                pattern_type,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'HIT_TARGET' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'HIT_STOP' THEN 1 ELSE 0 END) as failed,
                AVG(CASE WHEN status = 'HIT_TARGET' THEN profit_loss END) as avg_profit,
                AVG(CASE WHEN status = 'HIT_STOP' THEN profit_loss END) as avg_loss
            FROM trading_signals 
            WHERE status IN ('HIT_TARGET', 'HIT_STOP', 'EXPIRED', 'ACTIVE')
            GROUP BY pattern_type
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        statistics = []
        for row in results:
            total = row[1]
            successful = row[2] or 0
            failed = row[3] or 0
            completed = successful + failed
            success_rate = (successful / completed * 100) if completed > 0 else 0
            
            statistics.append({
                'pattern_type': row[0],
                'total_signals': total,
                'successful_signals': successful,
                'failed_signals': failed,
                'success_rate': round(success_rate, 2),
                'avg_profit': round(row[4] or 0, 2),
                'avg_loss': round(row[5] or 0, 2)
            })
        
        return statistics
    
    def cleanup_old_data(self, days_to_keep=30):
        """Remove dados antigos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        cursor.execute('''
            DELETE FROM trading_signals 
            WHERE created_at < ? AND status != 'ACTIVE'
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"[CLEAN] Removidos {deleted_count} sinais antigos")

# ==================== MAIN TRADING ANALYZER ====================
class TradingAnalyzer:
    """Classe principal do analisador"""
    
    def __init__(self):
        self.ta_engine = TechnicalAnalysisEngine()
        self.signal_manager = SignalManager()
        self.is_running = False
        self.analysis_count = 0
        self.last_cleanup = datetime.now()
        
    def add_price_data(self, timestamp, price, volume=0):
        """Adiciona dados e analisa"""
        
        price_data = PriceData(
            timestamp=timestamp,
            open_price=price * 0.9995,
            high=price * 1.0008,
            low=price * 0.9992,
            close=price,
            volume=volume
        )
        
        self.ta_engine.add_price_data(price_data)
        
        # Análise com rate limiting
        if self.ta_engine.can_analyze():
            self.analyze_market()
            self.ta_engine.mark_analysis_done()
            self.analysis_count += 1
            
            # Cleanup periódico
            if (datetime.now() - self.last_cleanup).total_seconds() > 3600:
                self.signal_manager.cleanup_old_data()
                self.last_cleanup = datetime.now()
        
    def analyze_market(self):
        """Análise completa do mercado"""
        if len(self.ta_engine.price_history) < 30:
            return
            
        current_price = self.ta_engine.price_history[-1].close
        indicators = self.ta_engine.calculate_indicators()
        
        # Atualiza sinais existentes
        updated_signals = self.signal_manager.update_signals(current_price)
        
        # Detecta novos padrões
        new_patterns = self._detect_all_patterns(indicators)
        
        # Cria novos sinais
        created_signals = 0
        for pattern in new_patterns:
            signal = self.signal_manager.create_signal(pattern, indicators, current_price)
            if signal:
                created_signals += 1
        
        # Log periódico
        if self.analysis_count % 20 == 0:
            logger.info(f"Análise #{self.analysis_count}: {created_signals} novos, "
                       f"{len(updated_signals)} atualizados, "
                       f"{len(self.signal_manager.active_signals)} ativos")
    
    def _detect_all_patterns(self, indicators):
        """Detecta todos os padrões"""
        patterns = []
        
        try:
            # Double Bottom
            double_bottom = self.ta_engine.detect_double_bottom()
            if double_bottom:
                patterns.append(double_bottom)
                
            # Confluência de indicadores
            indicator_signals = self.ta_engine.analyze_indicators_confluence(indicators)
            patterns.extend(indicator_signals)
            
        except Exception as e:
            logger.error(f"Erro na detecção: {e}")
        
        return patterns
    
    def get_current_analysis(self):
        """Análise atual completa"""
        if not self.ta_engine.price_history:
            return {
                'current_price': 0,
                'indicators': {},
                'active_signals': 0,
                'recent_signals': [],
                'pattern_stats': [],
                'system_info': {
                    'analysis_count': self.analysis_count,
                    'data_points': 0,
                    'last_analysis': None
                }
            }
            
        current_price = self.ta_engine.price_history[-1].close
        indicators = self.ta_engine.calculate_indicators()
        
        return {
            'current_price': current_price,
            'indicators': indicators,
            'active_signals': len(self.signal_manager.active_signals),
            'recent_signals': self.signal_manager.get_recent_signals(20),
            'pattern_stats': self.signal_manager.get_pattern_statistics(),
            'system_info': {
                'analysis_count': self.analysis_count,
                'data_points': len(self.ta_engine.price_history),
                'last_analysis': self.ta_engine.last_analysis_time.isoformat() if self.ta_engine.last_analysis_time else None
            }
        }
    
    def get_system_health(self):
        """Informações de saúde do sistema"""
        return {
            'total_analysis': self.analysis_count,
            'active_signals': len(self.signal_manager.active_signals),
            'data_points': len(self.ta_engine.price_history),
            'last_analysis': self.ta_engine.last_analysis_time,
            'memory_usage': {
                'price_history': len(self.ta_engine.price_history),
                'signal_hashes': len(self.signal_manager.uniqueness_system.signal_hashes),
                'cooldowns': len(self.signal_manager.uniqueness_system.pattern_cooldowns)
            }
        }

# ==================== TESTING ====================
def test_trading_analyzer():
    """Teste básico do sistema"""
    logger.info("[START] Testando Trading Analyzer...")
    
    analyzer = TradingAnalyzer()
    
    # Simula dados
    base_price = 43000
    for i in range(100):
        timestamp = datetime.now() - timedelta(minutes=100-i)
        price = base_price + (i * 5) + ((i * 13) % 50)
        analyzer.add_price_data(timestamp, price, 1000000)
        
        if i % 25 == 0:
            analysis = analyzer.get_current_analysis()
            logger.info(f"Teste {i}: ${price:.2f}, {analysis['active_signals']} sinais")
    
    final_analysis = analyzer.get_current_analysis()
    logger.info(f"[DATA] Preço final: ${final_analysis['current_price']:.2f}")
    logger.info(f"[DATA] Sinais ativos: {final_analysis['active_signals']}")
    logger.info(f"[DATA] Total sinais: {len(final_analysis['recent_signals'])}")
    logger.info("[OK] Teste concluído")
    
    return analyzer

if __name__ == "__main__":
    test_trading_analyzer()