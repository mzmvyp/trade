# integrated_app.py - Aplicação Completa Integrada
import json
import time
import threading
import os
from datetime import datetime, timedelta
import requests
from collections import deque
import sqlite3
from flask import Flask, render_template, jsonify, request
import logging

# Importa componentes existentes
from trading_analyzer import TradingAnalyzer

# ==================== BITCOIN DATA STREAMER (do projeto original) ====================
class BitcoinData:
    """Modelo para dados do Bitcoin"""
    def __init__(self, timestamp, price, volume_24h, market_cap, price_change_24h, source):
        self.timestamp = timestamp
        self.price = price
        self.volume_24h = volume_24h
        self.market_cap = market_cap
        self.price_change_24h = price_change_24h
        self.source = source
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'volume_24h': self.volume_24h,
            'market_cap': self.market_cap,
            'price_change_24h': self.price_change_24h,
            'source': self.source
        }

class BitcoinDataStreamer:
    """Stream de dados Bitcoin (do projeto original)"""
    
    def __init__(self):
        self.is_running = False
        self.data_queue = deque(maxlen=1000)
        self.subscribers = []
        
    def add_subscriber(self, callback):
        """Adiciona subscriber"""
        self.subscribers.append(callback)
        
    def _fetch_coingecko_data(self):
        """Busca dados da API CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            bitcoin_info = data['bitcoin']
            return BitcoinData(
                timestamp=datetime.now(),
                price=bitcoin_info['usd'],
                volume_24h=bitcoin_info.get('usd_24h_vol', 0),
                market_cap=bitcoin_info.get('usd_market_cap', 0),
                price_change_24h=bitcoin_info.get('usd_24h_change', 0),
                source='coingecko'
            )
        except Exception as e:
            logging.error(f"Erro ao buscar dados CoinGecko: {e}")
            return None
    
    def _fetch_binance_data(self):
        """Busca dados da API Binance"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            return BitcoinData(
                timestamp=datetime.now(),
                price=float(data['lastPrice']),
                volume_24h=float(data['volume']),
                market_cap=0,
                price_change_24h=float(data['priceChangePercent']),
                source='binance'
            )
        except Exception as e:
            logging.error(f"Erro ao buscar dados Binance: {e}")
            return None
    
    def start_streaming(self):
        """Inicia o streaming"""
        self.is_running = True
        
        def stream_worker():
            while self.is_running:
                try:
                    # Alterna entre APIs
                    if time.time() % 2 == 0:
                        data = self._fetch_coingecko_data()
                    else:
                        data = self._fetch_binance_data()
                    
                    if data:
                        self.data_queue.append(data)
                        
                        # Notifica subscribers
                        for callback in self.subscribers:
                            try:
                                callback(data)
                            except Exception as e:
                                logging.error(f"Erro no subscriber: {e}")
                    
                    time.sleep(5)  # Coleta a cada 5 segundos
                    
                except Exception as e:
                    logging.error(f"Erro no streaming: {e}")
                    time.sleep(10)
        
        thread = threading.Thread(target=stream_worker)
        thread.daemon = True
        thread.start()
        
    def stop_streaming(self):
        """Para o streaming"""
        self.is_running = False
        
    def get_recent_data(self, limit=100):
        """Retorna dados recentes"""
        return list(self.data_queue)[-limit:]

# ==================== BITCOIN STREAM PROCESSOR ====================
class BitcoinStreamProcessor:
    """Processador de dados Bitcoin (do projeto original)"""
    
    def __init__(self, db_path="data/bitcoin_stream.db"):
        self.db_path = db_path
        self.batch_size = 10
        self.batch_buffer = []
        self.init_database()
        
    def init_database(self):
        """Inicializa banco de dados"""
        os.makedirs('data', exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bitcoin_stream (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                price REAL,
                volume_24h REAL,
                market_cap REAL,
                price_change_24h REAL,
                source TEXT,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bitcoin_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                window_start DATETIME,
                window_end DATETIME,
                avg_price REAL,
                min_price REAL,
                max_price REAL,
                price_volatility REAL,
                total_volume REAL,
                data_points INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def process_stream_data(self, data):
        """Processa dados do stream"""
        self.batch_buffer.append(data)
        
        if len(self.batch_buffer) >= self.batch_size:
            self._process_batch()
            
    def _process_batch(self):
        """Processa lote de dados"""
        if not self.batch_buffer:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insere dados brutos
        for data in self.batch_buffer:
            cursor.execute('''
                INSERT INTO bitcoin_stream 
                (timestamp, price, volume_24h, market_cap, price_change_24h, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.timestamp, data.price, data.volume_24h,
                data.market_cap, data.price_change_24h, data.source
            ))
        
        # Analytics
        window_start = min(d.timestamp for d in self.batch_buffer)
        window_end = max(d.timestamp for d in self.batch_buffer)
        
        prices = [d.price for d in self.batch_buffer]
        volumes = [d.volume_24h for d in self.batch_buffer if d.volume_24h > 0]
        
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            price_volatility = (max_price - min_price) / avg_price * 100
            total_volume = sum(volumes) if volumes else 0
            
            cursor.execute('''
                INSERT INTO bitcoin_analytics 
                (window_start, window_end, avg_price, min_price, max_price, 
                 price_volatility, total_volume, data_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                window_start, window_end, avg_price, min_price, max_price,
                price_volatility, total_volume, len(self.batch_buffer)
            ))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Processado lote de {len(self.batch_buffer)} registros")
        self.batch_buffer.clear()

# ==================== BITCOIN ANALYTICS ENGINE ====================
class BitcoinAnalyticsEngine:
    """Engine de analytics Bitcoin (do projeto original)"""
    
    def __init__(self, db_path="data/bitcoin_stream.db"):
        self.db_path = db_path
        
    def get_real_time_metrics(self):
        """Métricas em tempo real"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        five_min_ago = datetime.now() - timedelta(minutes=5)
        
        cursor.execute('''
            SELECT 
                COUNT(*) as count,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(price_change_24h) as avg_change
            FROM bitcoin_stream 
            WHERE timestamp > ?
        ''', (five_min_ago,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] > 0:
            return {
                'data_points': result[0],
                'avg_price': round(result[1], 2),
                'min_price': round(result[2], 2),
                'max_price': round(result[3], 2),
                'avg_change_24h': round(result[4], 2),
                'price_range': round(result[3] - result[2], 2),
                'last_update': datetime.now().isoformat()
            }
        else:
            return {
                'data_points': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'avg_change_24h': 0,
                'price_range': 0,
                'last_update': datetime.now().isoformat()
            }

# ==================== INTEGRATED CONTROLLER ====================
class IntegratedController:
    """Controller principal que integra Bitcoin Pipeline + Trading Analyzer"""
    
    def __init__(self):
        self.app = Flask(__name__)
        
        # Componentes Bitcoin Pipeline
        self.bitcoin_streamer = BitcoinDataStreamer()
        self.bitcoin_processor = BitcoinStreamProcessor()
        self.bitcoin_analytics = BitcoinAnalyticsEngine()
        
        # Componente Trading Analyzer
        self.trading_analyzer = TradingAnalyzer()
        
        # Conecta pipeline com analyzer
        self.bitcoin_streamer.add_subscriber(self.bitcoin_processor.process_stream_data)
        self.bitcoin_streamer.add_subscriber(self._feed_trading_analyzer)
        
        self.setup_routes()
        
    def _feed_trading_analyzer(self, bitcoin_data):
        """Alimenta o trading analyzer com dados do Bitcoin"""
        try:
            self.trading_analyzer.add_price_data(
                timestamp=bitcoin_data.timestamp,
                price=bitcoin_data.price,
                volume=bitcoin_data.volume_24h
            )
        except Exception as e:
            logging.error(f"Erro ao alimentar trading analyzer: {e}")
        
    def setup_routes(self):
        """Configura todas as rotas da aplicação"""
        
        # ==================== ROTAS PRINCIPAIS ====================
        @self.app.route('/')
        def dashboard():
            """Dashboard integrado principal"""
            return render_template('integrated_dashboard.html')
        
        @self.app.route('/bitcoin')
        def bitcoin_dashboard():
            """Dashboard apenas Bitcoin"""
            return render_template('bitcoin_dashboard.html')
            
        @self.app.route('/trading')
        def trading_dashboard():
            """Dashboard apenas Trading"""
            return render_template('trading_dashboard.html')
        
        # ==================== ROTAS BITCOIN PIPELINE ====================
        @self.app.route('/api/bitcoin/start-stream', methods=['POST'])
        def start_bitcoin_stream():
            """Inicia streaming Bitcoin"""
            self.bitcoin_streamer.start_streaming()
            return jsonify({'status': 'started'})
        
        @self.app.route('/api/bitcoin/stop-stream', methods=['POST'])
        def stop_bitcoin_stream():
            """Para streaming Bitcoin"""
            self.bitcoin_streamer.stop_streaming()
            return jsonify({'status': 'stopped'})
        
        @self.app.route('/api/bitcoin/metrics')
        def get_bitcoin_metrics():
            """Métricas Bitcoin em tempo real"""
            return jsonify(self.bitcoin_analytics.get_real_time_metrics())
        
        @self.app.route('/api/bitcoin/recent-data')
        def get_bitcoin_recent_data():
            """Dados recentes Bitcoin"""
            limit = request.args.get('limit', 50, type=int)
            recent_data = self.bitcoin_streamer.get_recent_data(limit)
            return jsonify([data.to_dict() for data in recent_data])
        
        # ==================== ROTAS TRADING ANALYZER ====================
        @self.app.route('/api/trading/analysis')
        def get_trading_analysis():
            """Análise completa de trading"""
            return jsonify(self.trading_analyzer.get_current_analysis())
        
        @self.app.route('/api/trading/signals')
        def get_trading_signals():
            """Sinais de trading recentes"""
            limit = request.args.get('limit', 20, type=int)
            signals = self.trading_analyzer.signal_manager.get_recent_signals(limit)
            return jsonify(signals)
        
        @self.app.route('/api/trading/active-signals')
        def get_active_signals():
            """Sinais ativos"""
            active = []
            for signal in self.trading_analyzer.signal_manager.active_signals.values():
                signal_dict = signal.to_dict()
                # Adiciona preço atual para cálculo de progresso
                if self.bitcoin_streamer.data_queue:
                    signal_dict['current_price'] = self.bitcoin_streamer.data_queue[-1].price
                active.append(signal_dict)
            return jsonify(active)
        
        @self.app.route('/api/trading/pattern-stats')
        def get_pattern_statistics():
            """Estatísticas por padrão"""
            return jsonify(self.trading_analyzer.signal_manager.get_pattern_statistics())
        
        @self.app.route('/api/trading/indicators')
        def get_current_indicators():
            """Indicadores técnicos atuais"""
            if len(self.trading_analyzer.ta_engine.price_history) > 0:
                indicators = self.trading_analyzer.ta_engine.calculate_indicators()
                return jsonify(indicators)
            return jsonify({})
        
        # ==================== ROTAS INTEGRADAS ====================
        @self.app.route('/api/integrated/status')
        def get_integrated_status():
            """Status geral da aplicação"""
            bitcoin_data_count = len(self.bitcoin_streamer.data_queue)
            trading_data_count = len(self.trading_analyzer.ta_engine.price_history)
            active_signals_count = len(self.trading_analyzer.signal_manager.active_signals)
            
            return jsonify({
                'bitcoin_streaming': self.bitcoin_streamer.is_running,
                'bitcoin_data_points': bitcoin_data_count,
                'trading_data_points': trading_data_count,
                'active_signals': active_signals_count,
                'last_bitcoin_price': self.bitcoin_streamer.data_queue[-1].price if bitcoin_data_count > 0 else 0,
                'system_status': 'running' if self.bitcoin_streamer.is_running else 'stopped'
            })
        
        @self.app.route('/api/integrated/dashboard-data')
        def get_dashboard_data():
            """Dados completos para dashboard integrado"""
            # Bitcoin data
            bitcoin_metrics = self.bitcoin_analytics.get_real_time_metrics()
            recent_bitcoin = self.bitcoin_streamer.get_recent_data(10)
            
            # Trading data
            trading_analysis = self.trading_analyzer.get_current_analysis()
            
            return jsonify({
                'bitcoin': {
                    'metrics': bitcoin_metrics,
                    'recent_data': [data.to_dict() for data in recent_bitcoin],
                    'streaming': self.bitcoin_streamer.is_running
                },
                'trading': trading_analysis,
                'integrated_status': {
                    'total_data_points': len(self.bitcoin_streamer.data_queue),
                    'analysis_ready': len(self.trading_analyzer.ta_engine.price_history) >= 20,
                    'last_update': datetime.now().isoformat()
                }
            })
    
    def run(self, debug=True, port=5000):
        """Inicia a aplicação integrada"""
        logging.basicConfig(level=logging.INFO)
        print("🚀 Sistema Integrado Bitcoin + Trading iniciado!")
        print(f"📊 Dashboard Principal: http://localhost:{port}")
        print(f"💰 Dashboard Bitcoin: http://localhost:{port}/bitcoin")
        print(f"📈 Dashboard Trading: http://localhost:{port}/trading")
        print("🔄 APIs disponíveis:")
        print(f"   - Status: http://localhost:{port}/api/integrated/status")
        print(f"   - Bitcoin: http://localhost:{port}/api/bitcoin/metrics")
        print(f"   - Trading: http://localhost:{port}/api/trading/analysis")
        
        self.app.run(debug=debug, port=port, host='0.0.0.0')

# ==================== MAIN ====================
if __name__ == "__main__":
    # Cria diretórios necessários
    os.makedirs('data', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    # Inicializa e executa aplicação integrada
    controller = IntegratedController()
    controller.run(debug=True, port=5000)