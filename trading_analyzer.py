# trading_analyzer.py - Sistema de Análise Técnica Sem TA-Lib
import json
import time
import threading
from datetime import datetime, timedelta
import requests
import sqlite3
import logging
import numpy as np
import pandas as pd
from collections import deque

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

# ==================== MODELS ====================
class TradingSignal:
    """Modelo para sinais de trading"""
    def __init__(self, timestamp, price, pattern_type, entry_price, target_price, 
                 stop_loss, confidence, indicators_used, status='ACTIVE'):
        self.timestamp = timestamp
        self.price = price
        self.pattern_type = pattern_type
        self.entry_price = entry_price
        self.target_price = target_price
        self.stop_loss = stop_loss
        self.confidence = confidence
        self.indicators_used = indicators_used
        self.status = status
        self.created_at = timestamp
        self.closed_at = None
        self.profit_loss = 0.0
        
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
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'profit_loss': self.profit_loss
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

# ==================== TECHNICAL ANALYSIS ENGINE ====================
class TechnicalAnalysisEngine:
    """Engine de análise técnica - detecta padrões e calcula indicadores"""
    
    def __init__(self, lookback_periods=200):
        self.lookback_periods = lookback_periods
        self.price_history = deque(maxlen=lookback_periods)
        self.indicators = TechnicalIndicators()
        
    def add_price_data(self, price_data):
        """Adiciona novo dado de preço ao histórico"""
        self.price_history.append(price_data)
        
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
            
            # Volume
            indicators['VOLUME_SMA'] = self.indicators.sma(volumes, 20)
            
        except Exception as e:
            logging.error(f"Erro ao calcular indicadores: {e}")
            
        return indicators
    
    def detect_double_bottom(self):
        """Detecta padrão de fundo duplo"""
        if len(self.price_history) < 50:
            return None
            
        closes = [p.close for p in self.price_history]
        lows = [p.low for p in self.price_history]
        
        # Busca por dois mínimos similares
        recent_lows = []
        for i in range(10, len(lows) - 10):
            window_lows = lows[i-10:i+10]
            if lows[i] == min(window_lows):  # Local minimum
                recent_lows.append((i, lows[i]))
        
        if len(recent_lows) >= 2:
            # Pega os dois últimos mínimos
            first_low = recent_lows[-2]
            second_low = recent_lows[-1]
            
            # Verifica se são similares (diferença < 2%)
            price_diff = abs(first_low[1] - second_low[1]) / first_low[1]
            if price_diff < 0.02:  # 2% de tolerância
                # Calcula alvo
                peak_between = max(lows[first_low[0]:second_low[0]])
                target_height = peak_between - min(first_low[1], second_low[1])
                
                return {
                    'pattern': 'DOUBLE_BOTTOM',
                    'entry': second_low[1] * 1.005,
                    'target': second_low[1] + target_height,
                    'stop': second_low[1] * 0.98,
                    'confidence': min(95, 60 + (1 - price_diff) * 35)
                }
        return None
    
    def detect_head_and_shoulders(self):
        """Detecta padrão ombro-cabeça-ombro"""
        if len(self.price_history) < 60:
            return None
            
        highs = [p.high for p in self.price_history]
        
        # Busca por três picos
        recent_peaks = []
        for i in range(15, len(highs) - 15):
            window_highs = highs[i-15:i+15]
            if highs[i] == max(window_highs):  # Local maximum
                recent_peaks.append((i, highs[i]))
        
        if len(recent_peaks) >= 3:
            left_shoulder = recent_peaks[-3]
            head = recent_peaks[-2]
            right_shoulder = recent_peaks[-1]
            
            # Verifica se a cabeça é mais alta que os ombros
            if (head[1] > left_shoulder[1] * 1.02 and 
                head[1] > right_shoulder[1] * 1.02 and
                abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1] < 0.03):
                
                # Calcula linha de pescoço
                neckline = min(left_shoulder[1], right_shoulder[1])
                target_height = head[1] - neckline
                
                return {
                    'pattern': 'HEAD_AND_SHOULDERS',
                    'entry': neckline * 0.995,
                    'target': neckline - target_height,
                    'stop': head[1] * 1.02,
                    'confidence': 75
                }
        return None
    
    def detect_triangle_breakout(self):
        """Detecta rompimento de triângulo"""
        if len(self.price_history) < 40:
            return None
            
        closes = [p.close for p in self.price_history]
        highs = [p.high for p in self.price_history]
        lows = [p.low for p in self.price_history]
        
        # Analisa convergência
        recent_highs = highs[-30:]
        recent_lows = lows[-30:]
        recent_closes = closes[-30:]
        
        early_range = max(recent_highs[:15]) - min(recent_lows[:15])
        late_range = max(recent_highs[-15:]) - min(recent_lows[-15:])
        
        if late_range < early_range * 0.7:  # Range diminuiu 30%
            current_price = recent_closes[-1]
            resistance = max(recent_highs[-10:])
            support = min(recent_lows[-10:])
            
            if current_price > resistance * 0.998:  # Próximo da resistência
                return {
                    'pattern': 'TRIANGLE_BREAKOUT_UP',
                    'entry': resistance * 1.002,
                    'target': resistance + (resistance - support),
                    'stop': support * 0.99,
                    'confidence': 70
                }
            elif current_price < support * 1.002:  # Próximo do suporte
                return {
                    'pattern': 'TRIANGLE_BREAKOUT_DOWN',
                    'entry': support * 0.998,
                    'target': support - (resistance - support),
                    'stop': resistance * 1.01,
                    'confidence': 70
                }
        return None
    
    def analyze_indicators_confluence(self, indicators):
        """Analisa confluência de indicadores para gerar sinais"""
        signals = []
        current_price = self.price_history[-1].close if self.price_history else 0
        
        if not indicators or current_price == 0:
            return signals
        
        buy_signals = 0
        sell_signals = 0
        
        # RSI
        if indicators.get('RSI'):
            if indicators['RSI'] < 30:
                buy_signals += 1
            elif indicators['RSI'] > 70:
                sell_signals += 1
        
        # Stochastic
        if indicators.get('STOCH_K') and indicators.get('STOCH_D'):
            if indicators['STOCH_K'] < 20 and indicators['STOCH_D'] < 20:
                buy_signals += 1
            elif indicators['STOCH_K'] > 80 and indicators['STOCH_D'] > 80:
                sell_signals += 1
        
        # MACD
        if indicators.get('MACD') and indicators.get('MACD_SIGNAL'):
            if indicators['MACD'] > indicators['MACD_SIGNAL']:
                buy_signals += 1
            else:
                sell_signals += 1
        
        # Moving Averages
        if indicators.get('SMA_12') and indicators.get('SMA_30'):
            if indicators['SMA_12'] > indicators['SMA_30']:
                buy_signals += 1
            else:
                sell_signals += 1
        
        # Bollinger Bands
        if indicators.get('BB_LOWER') and indicators.get('BB_UPPER'):
            if current_price < indicators['BB_LOWER']:
                buy_signals += 1
            elif current_price > indicators['BB_UPPER']:
                sell_signals += 1
        
        # Gera sinal se há confluência (3+ indicadores)
        if buy_signals >= 3:
            signals.append({
                'pattern': 'INDICATORS_BUY',
                'entry': current_price * 1.001,
                'target': current_price * 1.05,
                'stop': current_price * 0.97,
                'confidence': min(90, 50 + buy_signals * 10)
            })
        elif sell_signals >= 3:
            signals.append({
                'pattern': 'INDICATORS_SELL',
                'entry': current_price * 0.999,
                'target': current_price * 0.95,
                'stop': current_price * 1.03,
                'confidence': min(90, 50 + sell_signals * 10)
            })
        
        return signals

# ==================== SIGNAL MANAGER ====================
class SignalManager:
    """Gerencia sinais de trading"""
    
    def __init__(self, db_path="data/trading_signals.db"):
        self.db_path = db_path
        self.active_signals = {}
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
                status TEXT,
                created_at DATETIME,
                closed_at DATETIME,
                profit_loss REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_signal(self, pattern_data, indicators_used, current_price):
        """Cria novo sinal"""
        signal = TradingSignal(
            timestamp=datetime.now(),
            price=current_price,
            pattern_type=pattern_data['pattern'],
            entry_price=pattern_data['entry'],
            target_price=pattern_data['target'],
            stop_loss=pattern_data['stop'],
            confidence=pattern_data['confidence'],
            indicators_used=json.dumps(indicators_used)
        )
        
        self.save_signal(signal)
        signal_id = f"{signal.pattern_type}_{int(signal.timestamp.timestamp())}"
        self.active_signals[signal_id] = signal
        
        logging.info(f"Novo sinal: {signal.pattern_type} - Entry: ${signal.entry_price:.2f}")
        return signal
    
    def save_signal(self, signal):
        """Salva sinal no banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trading_signals 
            (timestamp, price, pattern_type, entry_price, target_price, stop_loss,
             confidence, indicators_used, status, created_at, closed_at, profit_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal.timestamp, signal.price, signal.pattern_type, signal.entry_price,
            signal.target_price, signal.stop_loss, signal.confidence,
            signal.indicators_used, signal.status, signal.created_at,
            signal.closed_at, signal.profit_loss
        ))
        
        conn.commit()
        conn.close()
    
    def update_signals(self, current_price):
        """Atualiza sinais ativos"""
        updated_signals = []
        
        for signal_id, signal in list(self.active_signals.items()):
            if signal.status != 'ACTIVE':
                continue
                
            # Verifica target/stop
            if ((signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM') and 
                current_price >= signal.target_price):
                signal.status = 'HIT_TARGET'
                signal.closed_at = datetime.now()
                signal.profit_loss = (signal.target_price - signal.entry_price) / signal.entry_price * 100
                updated_signals.append(signal)
                del self.active_signals[signal_id]
                
            elif ((signal.pattern_type.endswith('_BUY') or signal.pattern_type == 'DOUBLE_BOTTOM') and 
                  current_price <= signal.stop_loss):
                signal.status = 'HIT_STOP'
                signal.closed_at = datetime.now()
                signal.profit_loss = (signal.stop_loss - signal.entry_price) / signal.entry_price * 100
                updated_signals.append(signal)
                del self.active_signals[signal_id]
                
            # Expira após 24h
            elif (datetime.now() - signal.created_at).total_seconds() > 86400:
                signal.status = 'EXPIRED'
                signal.closed_at = datetime.now()
                signal.profit_loss = 0
                updated_signals.append(signal)
                del self.active_signals[signal_id]
        
        # Atualiza no banco
        for signal in updated_signals:
            self.update_signal_in_db(signal)
            
        return updated_signals
    
    def update_signal_in_db(self, signal):
        """Atualiza sinal no banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trading_signals 
            SET status = ?, closed_at = ?, profit_loss = ?
            WHERE pattern_type = ? AND created_at = ?
        ''', (signal.status, signal.closed_at, signal.profit_loss, 
              signal.pattern_type, signal.created_at))
        
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
                'status': row[9],
                'created_at': row[10],
                'closed_at': row[11],
                'profit_loss': row[12] or 0
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
            WHERE status IN ('HIT_TARGET', 'HIT_STOP')
            GROUP BY pattern_type
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        statistics = []
        for row in results:
            total = row[1]
            successful = row[2] or 0
            success_rate = (successful / total * 100) if total > 0 else 0
            
            statistics.append({
                'pattern_type': row[0],
                'total_signals': total,
                'successful_signals': successful,
                'failed_signals': row[3] or 0,
                'success_rate': round(success_rate, 2),
                'avg_profit': round(row[4] or 0, 2),
                'avg_loss': round(row[5] or 0, 2)
            })
        
        return statistics

# ==================== MAIN TRADING ANALYZER ====================
class TradingAnalyzer:
    """Classe principal do analisador"""
    
    def __init__(self):
        self.ta_engine = TechnicalAnalysisEngine()
        self.signal_manager = SignalManager()
        self.is_running = False
        
    def add_price_data(self, timestamp, price, volume=0):
        """Adiciona dados e analisa"""
        price_data = PriceData(
            timestamp=timestamp,
            open_price=price * 0.999,
            high=price * 1.001,
            low=price * 0.999,
            close=price,
            volume=volume
        )
        
        self.ta_engine.add_price_data(price_data)
        self.analyze_market()
        
    def analyze_market(self):
        """Análise completa"""
        if len(self.ta_engine.price_history) < 20:
            return
            
        current_price = self.ta_engine.price_history[-1].close
        indicators = self.ta_engine.calculate_indicators()
        
        # Atualiza sinais existentes
        self.signal_manager.update_signals(current_price)
        
        # Detecta novos padrões
        patterns = []
        
        double_bottom = self.ta_engine.detect_double_bottom()
        if double_bottom:
            patterns.append(double_bottom)
            
        head_shoulders = self.ta_engine.detect_head_and_shoulders()
        if head_shoulders:
            patterns.append(head_shoulders)
            
        triangle = self.ta_engine.detect_triangle_breakout()
        if triangle:
            patterns.append(triangle)
        
        indicator_signals = self.ta_engine.analyze_indicators_confluence(indicators)
        patterns.extend(indicator_signals)
        
        # Cria novos sinais (evita duplicatas)
        for pattern in patterns:
            if not self._has_recent_signal(pattern['pattern']):
                self.signal_manager.create_signal(pattern, indicators, current_price)
    
    def _has_recent_signal(self, pattern_type):
        """Verifica sinais recentes do mesmo tipo"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        for signal in self.signal_manager.active_signals.values():
            if (signal.pattern_type == pattern_type and 
                signal.created_at > cutoff_time):
                return True
        return False
    
    def get_current_analysis(self):
        """Análise atual completa"""
        if not self.ta_engine.price_history:
            return {}
            
        current_price = self.ta_engine.price_history[-1].close
        indicators = self.ta_engine.calculate_indicators()
        
        return {
            'current_price': current_price,
            'indicators': indicators,
            'active_signals': len(self.signal_manager.active_signals),
            'recent_signals': self.signal_manager.get_recent_signals(10),
            'pattern_stats': self.signal_manager.get_pattern_statistics()
        }

if __name__ == "__main__":
    # Teste básico
    analyzer = TradingAnalyzer()
    
    # Simula dados
    base_price = 43000
    for i in range(100):
        price = base_price + (i * 10) + (i % 10 * 50)
        analyzer.add_price_data(datetime.now(), price, 1000000)
        time.sleep(0.1)
    
    analysis = analyzer.get_current_analysis()
    print(f"Análise: {json.dumps(analysis, indent=2, default=str)}")