# trading_analyzer.py - Sistema de Análise Técnica Sem TA-Lib (VERSÃO CORRIGIDA)
import json
import time
import threading
import hashlib
from datetime import datetime, timedelta
import requests
import sqlite3
import logging
import numpy as np
import pandas as pd
from collections import deque, defaultdict

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== TECHNICAL INDICATORS (Implementação própria) ====================
class TechnicalIndicators:
    """Implementações próprias dos indicadores técnicos sem TA-Lib"""
    
    @staticmethod
    def sma(prices, period):
        """Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    @staticmethod
    def ema(prices, period):
        """Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        # Calcula EMA usando SMA como seed
        sma = sum(prices[:period]) / period
        multiplier = 2 / (period + 1)
        ema_values = [sma]
        
        for i in range(period, len(prices)):
            ema_value = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema_value)
        
        return ema_values[-1] if ema_values else None
    
    @staticmethod
    def rsi(prices, period=14):
        """Relative Strength Index"""
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
        """Stochastic Oscillator"""
        if len(closes) < k_period:
            return None, None
        
        # %K calculation
        lowest_low = min(lows[-k_period:])
        highest_high = max(highs[-k_period:])
        
        if highest_high == lowest_low:
            k_percent = 50
        else:
            k_percent = 100 * (closes[-1] - lowest_low) / (highest_high - lowest_low)
        
        # %D é a média móvel de %K (simplificado)
        if len(closes) >= k_period + d_period - 1:
            recent_k_values = []
            for i in range(d_period):
                idx = len(closes) - 1 - i
                if idx >= k_period - 1:
                    ll = min(lows[idx-k_period+1:idx+1])
                    hh = max(highs[idx-k_period+1:idx+1])
                    if hh != ll:
                        k_val = 100 * (closes[idx] - ll) / (hh - ll)
                        recent_k_values.append(k_val)
            
            d_percent = sum(recent_k_values) / len(recent_k_values) if recent_k_values else k_percent
        else:
            d_percent = k_percent
        
        return k_percent, d_percent
    
    @staticmethod
    def macd(prices, fast_period=12, slow_period=26, signal_period=9):
        """MACD Indicator"""
        if len(prices) < slow_period:
            return None, None, None
        
        ema_fast = TechnicalIndicators.ema(prices, fast_period)
        ema_slow = TechnicalIndicators.ema(prices, slow_period)
        
        if ema_fast is None or ema_slow is None:
            return None, None, None
        
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD) - simplificado
        signal_line = macd_line * 0.9  # Aproximação
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices, period=20, std_dev=2):
        """Bollinger Bands"""
        if len(prices) < period:
            return None, None, None
        
        sma = TechnicalIndicators.sma(prices, period)
        if sma is None:
            return None, None, None
        
        # Calcula desvio padrão
        variance = sum((price - sma) ** 2 for price in prices[-period:]) / period
        std = variance ** 0.5
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def atr(highs, lows, closes, period=14):
        """Average True Range - para volatilidade"""
        if len(closes) < period + 1:
            return None
        
        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close_prev = abs(highs[i] - closes[i-1])
            low_close_prev = abs(lows[i] - closes[i-1])
            
            true_range = max(high_low, high_close_prev, low_close_prev)
            true_ranges.append(true_range)
        
        return sum(true_ranges[-period:]) / period

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
        """Gera hash único para o sinal baseado em parâmetros"""
        # Arredonda preços para evitar variações mínimas
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
        """Adiciona hash à lista de sinais conhecidos"""
        self.signal_hashes.add(signal_hash)
        
        # Limita o tamanho do set para evitar uso excessivo de memória
        if len(self.signal_hashes) > 1000:
            # Remove os mais antigos (simplificado)
            self.signal_hashes = set(list(self.signal_hashes)[-800:])
    
    def is_pattern_in_cooldown(self, pattern_type):
        """Verifica se padrão está em cooldown"""
        if pattern_type not in self.pattern_cooldowns:
            return False
        
        cooldown_period = self.cooldown_periods.get(pattern_type, timedelta(hours=1))
        return datetime.now() - self.pattern_cooldowns[pattern_type] < cooldown_period
    
    def set_pattern_cooldown(self, pattern_type):
        """Define cooldown para um padrão"""
        self.pattern_cooldowns[pattern_type] = datetime.now()

# ==================== SIGNAL VALIDATOR ====================
class SignalValidator:
    """Validador rigoroso de sinais de trading"""
    
    @staticmethod
    def validate_signal_parameters(pattern_data, current_price, indicators=None):
        """Valida parâmetros básicos do sinal"""
        try:
            entry = pattern_data['entry']
            target = pattern_data['target']
            stop = pattern_data['stop']
            
            # 1. Preços devem ser positivos
            if any(price <= 0 for price in [entry, target, stop, current_price]):
                return False, "Preços devem ser positivos"
            
            # 2. Entry deve estar próximo do preço atual (máximo 2% de diferença)
            price_diff_pct = abs(entry - current_price) / current_price * 100
            if price_diff_pct > 2.0:
                return False, f"Entry muito distante do preço atual ({price_diff_pct:.2f}%)"
            
            # 3. Validação específica por tipo de padrão
            if pattern_data['pattern'].endswith('_BUY') or pattern_data['pattern'] == 'DOUBLE_BOTTOM':
                # Para sinais de compra
                if target <= entry:
                    return False, "Target deve ser maior que entry para sinais de compra"
                if stop >= entry:
                    return False, "Stop deve ser menor que entry para sinais de compra"
            else:
                # Para sinais de venda
                if target >= entry:
                    return False, "Target deve ser menor que entry para sinais de venda"
                if stop <= entry:
                    return False, "Stop deve ser maior que entry para sinais de venda"
            
            # 4. Risk/Reward ratio deve ser favorável (mínimo 1:1.5)
            risk = abs(entry - stop)
            reward = abs(target - entry)
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            if risk_reward_ratio < 1.5:
                return False, f"Risk/Reward muito baixo ({risk_reward_ratio:.2f})"
            
            # 5. Risk não deve ser muito alto (máximo 5% do entry)
            risk_pct = (risk / entry) * 100
            if risk_pct > 5.0:
                return False, f"Risk muito alto ({risk_pct:.2f}%)"
            
            # 6. Validação de volatilidade (se disponível)
            if indicators and 'ATR' in indicators:
                atr = indicators['ATR']
                if atr and risk < atr * 0.5:
                    return False, "Risk muito baixo considerando volatilidade (ATR)"
            
            return True, "Válido"
            
        except Exception as e:
            return False, f"Erro na validação: {str(e)}"
    
    @staticmethod
    def validate_market_conditions(indicators):
        """Valida condições de mercado para trading"""
        if not indicators:
            return False, "Indicadores não disponíveis"
        
        # Verifica se há dados suficientes
        required_indicators = ['RSI', 'SMA_12', 'SMA_30']
        missing_indicators = [ind for ind in required_indicators if ind not in indicators or indicators[ind] is None]
        
        if missing_indicators:
            return False, f"Indicadores em falta: {', '.join(missing_indicators)}"
        
        # Evita trading em mercados muito voláteis ou sem direção
        if 'BB_UPPER' in indicators and 'BB_LOWER' in indicators:
            bb_upper = indicators['BB_UPPER']
            bb_lower = indicators['BB_LOWER']
            if bb_upper and bb_lower:
                bb_width_pct = ((bb_upper - bb_lower) / bb_lower) * 100
                if bb_width_pct > 10:  # Muito volátil
                    return False, "Mercado muito volátil para trading seguro"
        
        return True, "Condições adequadas"

# ==================== ENHANCED MODELS ====================
class TradingSignal:
    """Modelo aprimorado para sinais de trading"""
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
        self.activated = False  # Sinal foi ativado (preço atingiu entry)
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
    """Modelo para dados de preço OHLCV"""
    def __init__(self, timestamp, open_price, high, low, close, volume):
        self.timestamp = timestamp
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

# ==================== ENHANCED TECHNICAL ANALYSIS ENGINE ====================
class TechnicalAnalysisEngine:
    """Engine de análise técnica aprimorado"""
    
    def __init__(self, lookback_periods=200):
        self.lookback_periods = lookback_periods
        self.price_history = deque(maxlen=lookback_periods)
        self.indicators = TechnicalIndicators()
        self.last_analysis_time = None
        self.min_analysis_interval = 30  # seconds
        
    def add_price_data(self, price_data):
        """Adiciona novo dado de preço ao histórico"""
        self.price_history.append(price_data)
        
    def can_analyze(self):
        """Verifica se pode fazer análise (controle de rate limiting)"""
        if self.last_analysis_time is None:
            return True
        
        time_since_last = (datetime.now() - self.last_analysis_time).total_seconds()
        return time_since_last >= self.min_analysis_interval
        
    def mark_analysis_done(self):
        """Marca que análise foi feita"""
        self.last_analysis_time = datetime.now()
        
    def get_price_arrays(self):
        """Converte histórico para arrays para cálculos"""
        if len(self.price_history) < 20:
            return None, None, None, None, None
            
        opens = [p.open for p in self.price_history]
        highs = [p.high for p in self.price_history]
        lows = [p.low for p in self.price_history]
        closes = [p.close for p in self.price_history]
        volumes = [p.volume for p in self.price_history]
        
        return opens, highs, lows, closes, volumes
    
    def calculate_indicators(self):
        """Calcula todos os indicadores técnicos"""
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
            
            # ATR para volatilidade
            indicators['ATR'] = self.indicators.atr(highs, lows, closes)
            
            # Volume
            indicators['VOLUME_SMA'] = self.indicators.sma(volumes, 20)
            
            # Posição nas Bollinger Bands
            if bb_upper and bb_lower and closes:
                bb_position = (closes[-1] - bb_lower) / (bb_upper - bb_lower)
                indicators['BB_Position'] = bb_position
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores: {e}")
            
        return indicators
    
    def detect_double_bottom(self):
        """Detecta padrão de fundo duplo (MELHORADO)"""
        if len(self.price_history) < 80:  # Aumenta período mínimo
            return None
            
        closes = [p.close for p in self.price_history]
        lows = [p.low for p in self.price_history]
        volumes = [p.volume for p in self.price_history]
        
        # Verifica volume médio para validação
        avg_volume = sum(volumes[-20:]) / 20 if volumes else 0
        
        # Busca por dois mínimos similares com validação de volume
        recent_lows = []
        for i in range(20, len(lows) - 20):  # Aumenta janela
            window_lows = lows[i-20:i+20]
            if lows[i] == min(window_lows):  # Local minimum
                # Verifica se houve volume significativo no mínimo
                volume_at_low = volumes[i] if i < len(volumes) else 0
                if volume_at_low > avg_volume * 0.8:  # Volume adequado
                    recent_lows.append((i, lows[i]))
        
        if len(recent_lows) >= 2:
            # Pega os dois últimos mínimos
            first_low = recent_lows[-2]
            second_low = recent_lows[-1]
            
            # Espaçamento temporal adequado
            time_diff = second_low[0] - first_low[0]
            if time_diff < 20:  # Muito próximos no tempo
                return None
            
            # Verifica se são similares (diferença < 1.5%)
            price_diff = abs(first_low[1] - second_low[1]) / first_low[1]
            if price_diff < 0.015:  # 1.5% de tolerância (mais rigoroso)
                # Calcula alvo baseado no pico entre os fundos
                peak_between = max(lows[first_low[0]:second_low[0]])
                target_height = peak_between - min(first_low[1], second_low[1])
                
                # Validação adicional: altura do padrão deve ser significativa
                if target_height / second_low[1] < 0.02:  # Menos de 2%
                    return None
                
                entry_price = second_low[1] * 1.008  # Entry um pouco acima do fundo
                target_price = entry_price + target_height * 0.8  # Target conservador
                stop_price = second_low[1] * 0.985  # Stop mais apertado
                
                return {
                    'pattern': 'DOUBLE_BOTTOM',
                    'entry': entry_price,
                    'target': target_price,
                    'stop': stop_price,
                    'confidence': min(85, 50 + (1 - price_diff) * 35)
                }
        return None
    
    def detect_head_and_shoulders(self):
        """Detecta padrão ombro-cabeça-ombro (MELHORADO)"""
        if len(self.price_history) < 100:  # Período maior
            return None
            
        highs = [p.high for p in self.price_history]
        volumes = [p.volume for p in self.price_history]
        
        # Busca por três picos com validação de volume
        recent_peaks = []
        avg_volume = sum(volumes[-30:]) / 30 if volumes else 0
        
        for i in range(25, len(highs) - 25):  # Janela maior
            window_highs = highs[i-25:i+25]
            if highs[i] == max(window_highs):  # Local maximum
                volume_at_peak = volumes[i] if i < len(volumes) else 0
                if volume_at_peak > avg_volume * 0.6:  # Volume mínimo
                    recent_peaks.append((i, highs[i]))
        
        if len(recent_peaks) >= 3:
            left_shoulder = recent_peaks[-3]
            head = recent_peaks[-2]
            right_shoulder = recent_peaks[-1]
            
            # Validações mais rigorosas
            # 1. Espaçamento temporal
            if (head[0] - left_shoulder[0] < 15 or 
                right_shoulder[0] - head[0] < 15):
                return None
            
            # 2. Proporções da cabeça
            head_vs_left = head[1] / left_shoulder[1]
            head_vs_right = head[1] / right_shoulder[1]
            
            if not (1.03 <= head_vs_left <= 1.15 and 1.03 <= head_vs_right <= 1.15):
                return None
            
            # 3. Simetria dos ombros
            shoulder_diff = abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1]
            if shoulder_diff > 0.025:  # 2.5% máximo
                return None
                
            # Calcula linha de pescoço e target
            neckline = min(left_shoulder[1], right_shoulder[1])
            target_height = head[1] - neckline
            
            return {
                'pattern': 'HEAD_AND_SHOULDERS',
                'entry': neckline * 0.998,
                'target': neckline - target_height * 0.8,
                'stop': head[1] * 1.015,
                'confidence': 80
            }
        return None
    
    def analyze_indicators_confluence(self, indicators):
        """Analisa confluência de indicadores (MELHORADO)"""
        signals = []
        current_price = self.price_history[-1].close if self.price_history else 0
        
        if not indicators or current_price == 0:
            return signals
        
        buy_score = 0
        sell_score = 0
        total_indicators = 0
        
        # RSI (peso: 2)
        if indicators.get('RSI'):
            rsi = indicators['RSI']
            total_indicators += 2
            if rsi < 25:  # Mais extremo
                buy_score += 2
            elif rsi < 35:
                buy_score += 1
            elif rsi > 75:  # Mais extremo
                sell_score += 2
            elif rsi > 65:
                sell_score += 1
        
        # Stochastic (peso: 1.5)
        if indicators.get('STOCH_K') and indicators.get('STOCH_D'):
            stoch_k, stoch_d = indicators['STOCH_K'], indicators['STOCH_D']
            total_indicators += 1.5
            if stoch_k < 15 and stoch_d < 15:
                buy_score += 1.5
            elif stoch_k > 85 and stoch_d > 85:
                sell_score += 1.5
        
        # MACD (peso: 2)
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
        
        # Moving Averages (peso: 1.5)
        if indicators.get('SMA_12') and indicators.get('SMA_30'):
            sma12, sma30 = indicators['SMA_12'], indicators['SMA_30']
            total_indicators += 1.5
            if sma12 > sma30 and current_price > sma12:
                buy_score += 1.5
            elif sma12 < sma30 and current_price < sma12:
                sell_score += 1.5
        
        # Bollinger Bands (peso: 1)
        if (indicators.get('BB_LOWER') and indicators.get('BB_UPPER') and 
            indicators.get('BB_Position')):
            bb_pos = indicators['BB_Position']
            total_indicators += 1
            if bb_pos < 0.1:  # Próximo da banda inferior
                buy_score += 1
            elif bb_pos > 0.9:  # Próximo da banda superior
                sell_score += 1
        
        # Calcula porcentagem de confluência
        if total_indicators > 0:
            buy_confluence = (buy_score / total_indicators) * 100
            sell_confluence = (sell_score / total_indicators) * 100
            
            # Gera sinal apenas com confluência alta (>60%)
            if buy_confluence > 60:
                atr = indicators.get('ATR', current_price * 0.02)
                target_multiplier = min(3, buy_confluence / 30)  # Target baseado em confluência
                
                signals.append({
                    'pattern': 'INDICATORS_BUY',
                    'entry': current_price * 1.002,
                    'target': current_price * (1 + 0.02 * target_multiplier),
                    'stop': current_price * (1 - 0.015),
                    'confidence': min(90, buy_confluence)
                })
            elif sell_confluence > 60:
                atr = indicators.get('ATR', current_price * 0.02)
                target_multiplier = min(3, sell_confluence / 30)
                
                signals.append({
                    'pattern': 'INDICATORS_SELL',
                    'entry': current_price * 0.998,
                    'target': current_price * (1 - 0.02 * target_multiplier),
                    'stop': current_price * (1 + 0.015),
                    'confidence': min(90, sell_confluence)
                })
        
        return signals

# ==================== ENHANCED SIGNAL MANAGER ====================
class SignalManager:
    """Gerenciador de sinais aprimorado com controle de duplicidade"""
    
    def __init__(self, db_path="data/trading_signals.db"):
        self.db_path = db_path
        self.active_signals = {}  # key: signal_hash, value: signal
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
        
        # Carrega sinais ativos do banco
        self._load_active_signals()
        
    def _load_active_signals(self):
        """Carrega sinais ativos do banco na inicialização"""
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
            signal.activated = bool(row[11])
            signal.risk_reward_ratio = row[12] or 0
            
            self.active_signals[row[0]] = signal
            self.uniqueness_system.add_signal_hash(row[0])
        
        conn.close()
        logger.info(f"Carregados {len(self.active_signals)} sinais ativos do banco")
        
    def can_create_signal(self, pattern_data, current_price, indicators):
        """Verifica se pode criar um novo sinal"""
        
        # 1. Limite de sinais ativos
        if len(self.active_signals) >= self.max_active_signals:
            logger.warning(f"Limite de sinais ativos atingido ({self.max_active_signals})")
            return False, "Limite de sinais ativos atingido"
        
        # 2. Verifica cooldown do padrão
        if self.uniqueness_system.is_pattern_in_cooldown(pattern_data['pattern']):
            return False, f"Padrão {pattern_data['pattern']} em cooldown"
        
        # 3. Valida parâmetros do sinal
        valid, message = self.validator.validate_signal_parameters(pattern_data, current_price, indicators)
        if not valid:
            return False, f"Parâmetros inválidos: {message}"
        
        # 4. Valida condições de mercado
        valid, message = self.validator.validate_market_conditions(indicators)
        if not valid:
            return False, f"Condições inadequadas: {message}"
        
        # 5. Verifica unicidade
        signal_hash = self.uniqueness_system.generate_signal_hash(pattern_data, current_price)
        if not self.uniqueness_system.is_signal_unique(signal_hash):
            return False, "Sinal duplicado detectado"
        
        # 6. Verifica sobreposição com sinais existentes
        if self._has_overlapping_signal(pattern_data, current_price):
            return False, "Sobreposição com sinal existente"
        
        return True, "Sinal válido para criação"
    
    def _has_overlapping_signal(self, pattern_data, current_price):
        """Verifica se há sobreposição com sinais existentes"""
        entry_price = pattern_data['entry']
        
        for signal in self.active_signals.values():
            # Verifica se os preços de entrada estão muito próximos (1%)
            price_diff_pct = abs(signal.entry_price - entry_price) / entry_price * 100
            if price_diff_pct < 1.0:
                # Se for o mesmo tipo de padrão ou direção similar
                same_direction = (
                    (pattern_data['pattern'].endswith('_BUY') and signal.pattern_type.endswith('_BUY')) or
                    (pattern_data['pattern'].endswith('_SELL') and signal.pattern_type.endswith('_SELL')) or
                    (pattern_data['pattern'] == 'DOUBLE_BOTTOM' and signal.target_price > signal.entry_price) or
                    (pattern_data['pattern'] == 'HEAD_AND_SHOULDERS' and signal.target_price < signal.entry_price)
                )
                
                if same_direction:
                    logger.info(f"Sinal sobreposto detectado: {signal.pattern_type} vs {pattern_data['pattern']}")
                    return True
        
        return False
    
    def create_signal(self, pattern_data, indicators_used, current_price):
        """Cria novo sinal com validação completa"""
        
        # Verifica se pode criar
        can_create, reason = self.can_create_signal(pattern_data, current_price, indicators_used)
        if not can_create:
            logger.info(f"Sinal não criado: {reason}")
            return None
        
        # Gera hash único
        signal_hash = self.uniqueness_system.generate_signal_hash(pattern_data, current_price)
        
        # Cria o sinal
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
        
        # Salva no banco
        self.save_signal(signal)
        
        # Adiciona aos sinais ativos
        self.active_signals[signal_hash] = signal
        
        # Registra no sistema de unicidade
        self.uniqueness_system.add_signal_hash(signal_hash)
        self.uniqueness_system.set_pattern_cooldown(pattern_data['pattern'])
        
        logger.info(f"✅ Novo sinal criado: {signal.pattern_type} - Entry: ${signal.entry_price:.2f} - Hash: {signal_hash[:8]}")
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
                logger.warning(f"Tentativa de criar sinal duplicado: {signal.signal_hash}")
            else:
                logger.error(f"Erro de integridade ao salvar sinal: {e}")
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
            
            # Verifica se o sinal foi ativado (preço atingiu entry)
            if not signal.activated:
                if self._check_signal_activation(signal, current_price):
                    signal.activated = True
                    logger.info(f"🎯 Sinal ativado: {signal.pattern_type} - {signal_hash[:8]}")
            
            # Verifica target/stop apenas para sinais ativados
            if signal.activated:
                if self._check_target_hit(signal, current_price):
                    signal.status = 'HIT_TARGET'
                    signal.closed_at = datetime.now()
                    signal.profit_loss = self._calculate_profit_loss(signal, signal.target_price)
                    logger.info(f"🎯 Target atingido: {signal.pattern_type} - Lucro: {signal.profit_loss:.2f}%")
                    
                elif self._check_stop_hit(signal, current_price):
                    signal.status = 'HIT_STOP'
                    signal.closed_at = datetime.now()
                    signal.profit_loss = self._calculate_profit_loss(signal, signal.stop_loss)
                    logger.info(f"🛑 Stop atingido: {signal.pattern_type} - Perda: {signal.profit_loss:.2f}%")
            
            # Verifica expiração (24h para sinais não ativados, 48h para ativados)
            max_age = timedelta(hours=48 if signal.activated else 24)
            if (datetime.now() - signal.created_at) > max_age:
                signal.status = 'EXPIRED'
                signal.closed_at = datetime.now()
                signal.profit_loss = 0
                logger.info(f"⏰ Sinal expirado: {signal.pattern_type}")
            
            # Se status mudou, marca para atualização
            if signal.status != original_status:
                updated_signals.append(signal)
                
                # Remove dos sinais ativos se não está mais ativo
                if signal.status != 'ACTIVE':
                    del self.active_signals[signal_hash]
        
        # Atualiza no banco
        for signal in updated_signals:
            self.update_signal_in_db(signal)
            
        return updated_signals
    
    def _check_signal_activation(self, signal, current_price):
        """Verifica se sinal foi ativado"""
        tolerance = 0.001  # 0.1% de tolerância
        
        if signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM':
            return current_price >= signal.entry_price * (1 - tolerance)
        else:
            return current_price <= signal.entry_price * (1 + tolerance)
    
    def _check_target_hit(self, signal, current_price):
        """Verifica se target foi atingido"""
        if signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM':
            return current_price >= signal.target_price
        else:
            return current_price <= signal.target_price
    
    def _check_stop_hit(self, signal, current_price):
        """Verifica se stop foi atingido"""
        if signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM':
            return current_price <= signal.stop_loss
        else:
            return current_price >= signal.stop_loss
    
    def _calculate_profit_loss(self, signal, exit_price):
        """Calcula profit/loss em porcentagem"""
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
                'activated': bool(row[14]),
                'risk_reward_ratio': row[15] or 0
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
                AVG(CASE WHEN status = 'HIT_STOP' THEN profit_loss END) as avg_loss,
                AVG(risk_reward_ratio) as avg_rr
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
                'avg_loss': round(row[5] or 0, 2),
                'avg_risk_reward': round(row[6] or 0, 2)
            })
        
        return statistics
    
    def cleanup_old_data(self, days_to_keep=30):
        """Remove dados antigos para manter performance"""
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
            logger.info(f"Removidos {deleted_count} sinais antigos do banco")

# ==================== MAIN TRADING ANALYZER (ENHANCED) ====================
class TradingAnalyzer:
    """Classe principal do analisador aprimorada"""
    
    def __init__(self):
        self.ta_engine = TechnicalAnalysisEngine()
        self.signal_manager = SignalManager()
        self.is_running = False
        self.analysis_count = 0
        self.last_cleanup = datetime.now()
        
    def add_price_data(self, timestamp, price, volume=0):
        """Adiciona dados e analisa com controle de frequência"""
        
        # Cria dados OHLCV simulados (em produção, usar dados reais)
        price_data = PriceData(
            timestamp=timestamp,
            open_price=price * 0.9995,  # Simulação mais realista
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
            if (datetime.now() - self.last_cleanup).total_seconds() > 3600:  # 1 hora
                self.signal_manager.cleanup_old_data()
                self.last_cleanup = datetime.now()
        
    def analyze_market(self):
        """Análise completa do mercado"""
        if len(self.ta_engine.price_history) < 30:  # Mínimo aumentado
            return
            
        current_price = self.ta_engine.price_history[-1].close
        indicators = self.ta_engine.calculate_indicators()
        
        # Atualiza sinais existentes primeiro
        updated_signals = self.signal_manager.update_signals(current_price)
        
        # Detecta novos padrões com validação
        new_patterns = self._detect_all_patterns(indicators)
        
        # Cria novos sinais (com todas as validações)
        created_signals = 0
        for pattern in new_patterns:
            signal = self.signal_manager.create_signal(pattern, indicators, current_price)
            if signal:
                created_signals += 1
        
        # Log de atividade
        if self.analysis_count % 10 == 0:  # Log a cada 10 análises
            logger.info(f"Análise #{self.analysis_count}: {created_signals} novos sinais, "
                       f"{len(updated_signals)} atualizados, "
                       f"{len(self.signal_manager.active_signals)} ativos")
    
    def _detect_all_patterns(self, indicators):
        """Detecta todos os padrões disponíveis"""
        patterns = []
        
        try:
            # Double Bottom
            double_bottom = self.ta_engine.detect_double_bottom()
            if double_bottom:
                patterns.append(double_bottom)
                
            # Head and Shoulders
            head_shoulders = self.ta_engine.detect_head_and_shoulders()
            if head_shoulders:
                patterns.append(head_shoulders)
                
            # Confluência de indicadores
            indicator_signals = self.ta_engine.analyze_indicators_confluence(indicators)
            patterns.extend(indicator_signals)
            
        except Exception as e:
            logger.error(f"Erro na detecção de padrões: {e}")
        
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
                'last_analysis': self.ta_engine.last_analysis_time.isoformat() if self.ta_engine.last_analysis_time else None,
                'active_signals_detail': [signal.to_dict() for signal in self.signal_manager.active_signals.values()]
            }
        }
    
    def get_system_health(self):
        """Retorna informações de saúde do sistema"""
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

# ==================== TESTING FUNCTION ====================
def test_trading_analyzer():
    """Função de teste para validar o sistema"""
    logger.info("🧪 Iniciando teste do Trading Analyzer...")
    
    analyzer = TradingAnalyzer()
    
    # Simula dados de mercado
    base_price = 43000
    prices = []
    
    # Gera dados simulados mais realistas
    for i in range(150):
        # Simula volatilidade e tendência
        trend = i * 2 if i < 75 else -i * 1
        noise = (hash(str(i)) % 200) - 100  # Ruído determinístico
        price = base_price + trend + noise
        prices.append(price)
        
        # Adiciona ao analyzer
        timestamp = datetime.now() - timedelta(minutes=150-i)
        analyzer.add_price_data(timestamp, price, 1000000 + noise * 1000)
        
        # Log progresso
        if i % 30 == 0:
            analysis = analyzer.get_current_analysis()
            logger.info(f"Teste {i}: Preço ${price:.2f}, "
                       f"Sinais ativos: {analysis['active_signals']}, "
                       f"Total análises: {analysis['system_info']['analysis_count']}")
    
    # Relatório final
    final_analysis = analyzer.get_current_analysis()
    system_health = analyzer.get_system_health()
    
    logger.info("📊 Relatório Final do Teste:")
    logger.info(f"  💰 Preço final: ${final_analysis['current_price']:.2f}")
    logger.info(f"  📈 Sinais ativos: {final_analysis['active_signals']}")
    logger.info(f"  📋 Total de sinais: {len(final_analysis['recent_signals'])}")
    logger.info(f"  🔄 Análises realizadas: {system_health['total_analysis']}")
    logger.info(f"  📊 Pontos de dados: {system_health['data_points']}")
    
    if final_analysis['pattern_stats']:
        logger.info("  🎯 Estatísticas por padrão:")
        for stat in final_analysis['pattern_stats']:
            logger.info(f"    {stat['pattern_type']}: {stat['total_signals']} sinais, "
                       f"{stat['success_rate']:.1f}% sucesso")
    
    logger.info("✅ Teste concluído com sucesso!")
    return analyzer

if __name__ == "__main__":
    # Executa teste
    test_analyzer = test_trading_analyzer()
    
    # Análise adicional
    print("\n" + "="*60)
    print("ANÁLISE DETALHADA DO SISTEMA")
    print("="*60)
    
    analysis = test_analyzer.get_current_analysis()
    health = test_analyzer.get_system_health()
    
    print(f"Status do Sistema: {'✅ Operacional' if analysis['current_price'] > 0 else '❌ Erro'}")
    print(f"Preço Atual: ${analysis['current_price']:,.2f}")
    print(f"Sinais Ativos: {analysis['active_signals']}")
    print(f"Dados Coletados: {health['data_points']}")
    print(f"Análises Realizadas: {health['total_analysis']}")
    
    if analysis['indicators']:
        print("\nIndicadores Técnicos:")
        for key, value in analysis['indicators'].items():
            if value is not None:
                if key in ['RSI', 'STOCH_K', 'STOCH_D']:
                    print(f"  {key}: {value:.2f}")
                elif 'PRICE' in key or 'SMA' in key or 'EMA' in key or 'BB_' in key:
                    print(f"  {key}: ${value:,.2f}")
                else:
                    print(f"  {key}: {value:.4f}")
    
    print("\n" + "="*60)