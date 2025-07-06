# core/data_streamer.py - Streaming de Dados de Múltiplas Fontes
import logging
import threading
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from .trading_pair import TradingPair, PriceData, trading_pair_manager

logger = logging.getLogger(__name__)

class DataSource:
    """Classe base para fontes de dados"""
    
    def __init__(self, name: str, base_url: str, rate_limit: float = 1.0):
        """
        Inicializa fonte de dados
        
        Args:
            name: Nome da fonte
            base_url: URL base da API
            rate_limit: Limite de requisições por segundo
        """
        self.name = name
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.error_count = 0
        self.max_errors = 5
        self.is_available = True
        
    def fetch_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados para um símbolo específico
        Deve ser implementado pelas subclasses
        """
        raise NotImplementedError("Subclasses devem implementar fetch_data")
    
    def _make_request(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Faz requisição HTTP com rate limiting"""
        try:
            # Rate limiting
            time_since_last = time.time() - self.last_request_time
            if time_since_last < self.rate_limit:
                time.sleep(self.rate_limit - time_since_last)
            
            self.last_request_time = time.time()
            
            # Faz requisição
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Reset contador de erros em caso de sucesso
            self.error_count = 0
            self.is_available = True
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self._handle_error(f"Erro na requisição para {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            self._handle_error(f"Erro ao decodificar JSON de {url}: {e}")
            return None
        except Exception as e:
            self._handle_error(f"Erro inesperado ao buscar {url}: {e}")
            return None
    
    def _handle_error(self, error_message: str):
        """Trata erros da fonte de dados"""
        self.error_count += 1
        logger.error(f"[{self.name}] {error_message}")
        
        if self.error_count >= self.max_errors:
            self.is_available = False
            logger.warning(f"Fonte {self.name} marcada como indisponível após {self.error_count} erros")
    
    def reset_errors(self):
        """Reseta contador de erros"""
        self.error_count = 0
        self.is_available = True
        logger.info(f"Erros resetados para fonte {self.name}")


class BinanceDataSource(DataSource):
    """Fonte de dados da Binance"""
    
    def __init__(self):
        super().__init__("Binance", "https://api.binance.com", 0.5)
    
    def fetch_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Busca dados da Binance"""
        if not self.is_available:
            return None
        
        # Remove USDT do final se presente para usar formato da Binance
        binance_symbol = symbol.replace('USDT', 'USDT')
        url = f"{self.base_url}/api/v3/ticker/24hr?symbol={binance_symbol}"
        
        data = self._make_request(url)
        if not data:
            return None
        
        try:
            return {
                'price': float(data['lastPrice']),
                'open': float(data['openPrice']),
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'close': float(data['lastPrice']),
                'volume': float(data['volume']),
                'price_change_24h': float(data['priceChangePercent']),
                'source': self.name
            }
        except (KeyError, ValueError, TypeError) as e:
            self._handle_error(f"Erro ao processar dados da Binance para {symbol}: {e}")
            return None


class CoinGeckoDataSource(DataSource):
    """Fonte de dados da CoinGecko"""
    
    def __init__(self):
        super().__init__("CoinGecko", "https://api.coingecko.com", 1.0)
        
        # Mapeamento de símbolos para IDs do CoinGecko
        self.symbol_map = {
            'BTCUSDT': 'bitcoin',
            'ETHUSDT': 'ethereum',
            'SOLUSDT': 'solana',
            'BNBUSDT': 'binancecoin',
            'ADAUSDT': 'cardano',
            'DOTUSDT': 'polkadot',
            'LINKUSDT': 'chainlink'
        }
    
    def fetch_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Busca dados da CoinGecko"""
        if not self.is_available:
            return None
        
        coin_id = self.symbol_map.get(symbol)
        if not coin_id:
            logger.warning(f"Símbolo {symbol} não mapeado para CoinGecko")
            return None
        
        url = f"{self.base_url}/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
        
        data = self._make_request(url)
        if not data or coin_id not in data:
            return None
        
        try:
            coin_data = data[coin_id]
            price = coin_data['usd']
            
            return {
                'price': price,
                'open': price,  # CoinGecko não fornece open diretamente
                'high': price,  # Aproximação
                'low': price,   # Aproximação
                'close': price,
                'volume': coin_data.get('usd_24h_vol', 0),
                'price_change_24h': coin_data.get('usd_24h_change', 0),
                'source': self.name
            }
        except (KeyError, ValueError, TypeError) as e:
            self._handle_error(f"Erro ao processar dados da CoinGecko para {symbol}: {e}")
            return None


class SimulatedDataSource(DataSource):
    """Fonte de dados simulada para testes"""
    
    def __init__(self):
        super().__init__("Simulated", "http://localhost", 0.1)
        self.base_prices = {
            'BTCUSDT': 45000,
            'ETHUSDT': 3000,
            'SOLUSDT': 100,
            'BNBUSDT': 300,
            'ADAUSDT': 0.5,
            'DOTUSDT': 6,
            'LINKUSDT': 15
        }
        self.last_prices = self.base_prices.copy()
    
    def fetch_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Gera dados simulados"""
        if not self.is_available:
            return None
        
        if symbol not in self.base_prices:
            return None
        
        # Simula variação de preço (-2% a +2%)
        import random
        base_price = self.last_prices[symbol]
        variation = random.uniform(-0.02, 0.02)
        new_price = base_price * (1 + variation)
        
        # Atualiza último preço
        self.last_prices[symbol] = new_price
        
        # Simula dados OHLC
        high = new_price * random.uniform(1.0, 1.01)
        low = new_price * random.uniform(0.99, 1.0)
        
        return {
            'price': new_price,
            'open': base_price,
            'high': high,
            'low': low,
            'close': new_price,
            'volume': random.uniform(1000000, 5000000),
            'price_change_24h': ((new_price - self.base_prices[symbol]) / self.base_prices[symbol]) * 100,
            'source': self.name
        }


class MultiPairDataStreamer:
    """
    Streamer de dados para múltiplos pares de diferentes fontes
    Gerencia coleta de dados em paralelo com fallback entre fontes
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Inicializa o streamer
        
        Args:
            max_workers: Número máximo de threads para coleta paralela
        """
        self.max_workers = max_workers
        self.is_running = False
        self.update_interval = 5  # segundos
        
        # Thread principal de streaming
        self.streaming_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Pool de threads para coleta paralela
        self.executor: Optional[ThreadPoolExecutor] = None
        
        # Fontes de dados (ordenadas por prioridade)
        self.data_sources: List[DataSource] = [
            BinanceDataSource(),
            CoinGeckoDataSource(),
            SimulatedDataSource()  # Fallback
        ]
        
        # Estatísticas
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': None,
            'last_update': None,
            'sources_used': {source.name: 0 for source in self.data_sources}
        }
        
        logger.info("MultiPairDataStreamer inicializado")
    
    # ==================== CONTROLE DO STREAMING ====================
    
    def start_all_enabled(self) -> bool:
        """
        Inicia streaming para todos os pares habilitados
        
        Returns:
            True se iniciado com sucesso
        """
        if self.is_running:
            logger.warning("Streaming já está em execução")
            return False
        
        # Inicia streaming para pares habilitados
        enabled_pairs = trading_pair_manager.get_enabled_pairs()
        if not enabled_pairs:
            logger.warning("Nenhum par habilitado para streaming")
            return False
        
        # Inicia streaming de cada par
        started_count = 0
        for pair in enabled_pairs:
            if pair.start_streaming():
                started_count += 1
        
        if started_count == 0:
            logger.error("Nenhum par pôde ser iniciado para streaming")
            return False
        
        # Inicia thread principal
        self.is_running = True
        self.stop_event.clear()
        self.stats['start_time'] = datetime.now()
        
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.streaming_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self.streaming_thread.start()
        
        logger.info(f"Streaming iniciado para {started_count} pares")
        return True
    
    def stop_all(self):
        """Para todo o streaming"""
        if not self.is_running:
            logger.warning("Streaming não está em execução")
            return
        
        logger.info("Parando streaming...")
        
        # Sinaliza parada
        self.is_running = False
        self.stop_event.set()
        
        # Para streaming de todos os pares
        streaming_pairs = trading_pair_manager.get_streaming_pairs()
        for pair in streaming_pairs:
            pair.stop_streaming()
        
        # Aguarda thread principal terminar
        if self.streaming_thread and self.streaming_thread.is_alive():
            self.streaming_thread.join(timeout=10)
        
        # Finaliza executor
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None
        
        logger.info("Streaming parado")
    
    def start_pair(self, symbol: str) -> bool:
        """
        Inicia streaming para par específico
        
        Args:
            symbol: Símbolo do par
            
        Returns:
            True se iniciado com sucesso
        """
        pair = trading_pair_manager.get_pair(symbol)
        if not pair:
            logger.error(f"Par {symbol} não encontrado")
            return False
        
        if not pair.enabled:
            logger.error(f"Par {symbol} está desabilitado")
            return False
        
        if pair.start_streaming():
            logger.info(f"Streaming iniciado para {symbol}")
            
            # Se streaming geral não estiver rodando, inicia
            if not self.is_running:
                self.start_all_enabled()
            
            return True
        
        return False
    
    def stop_pair(self, symbol: str) -> bool:
        """
        Para streaming para par específico
        
        Args:
            symbol: Símbolo do par
            
        Returns:
            True se parado com sucesso
        """
        pair = trading_pair_manager.get_pair(symbol)
        if not pair:
            logger.error(f"Par {symbol} não encontrado")
            return False
        
        if pair.is_streaming:
            pair.stop_streaming()
            logger.info(f"Streaming parado para {symbol}")
            return True
        
        logger.warning(f"Par {symbol} não estava em streaming")
        return False
    
    # ==================== LOOP PRINCIPAL ====================
    
    def _streaming_loop(self):
        """Loop principal de streaming"""
        logger.info("Loop de streaming iniciado")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Coleta dados de todos os pares em streaming
                self._collect_all_data()
                
                # Atualiza timestamp
                self.stats['last_update'] = datetime.now()
                
                # Aguarda próxima iteração
                if not self.stop_event.wait(self.update_interval):
                    continue  # Timeout normal, continua loop
                else:
                    break  # Stop event foi setado
                    
            except Exception as e:
                logger.error(f"Erro no loop de streaming: {e}", exc_info=True)
                time.sleep(1)  # Evita loop infinito em caso de erro
        
        logger.info("Loop de streaming finalizado")
    
    def _collect_all_data(self):
        """Coleta dados de todos os pares em streaming usando threads"""
        streaming_pairs = trading_pair_manager.get_streaming_pairs()
        
        if not streaming_pairs:
            return
        
        # Submete tarefas para o pool de threads
        futures = {}
        for pair in streaming_pairs:
            future = self.executor.submit(self._collect_pair_data, pair)
            futures[future] = pair
        
        # Processa resultados conforme completam
        for future in as_completed(futures, timeout=30):
            pair = futures[future]
            try:
                price_data = future.result()
                if price_data:
                    pair.add_price_data(price_data)
                    self.stats['successful_requests'] += 1
                else:
                    self.stats['failed_requests'] += 1
                    
            except Exception as e:
                logger.error(f"Erro ao processar dados do par {pair.symbol}: {e}")
                self.stats['failed_requests'] += 1
        
        self.stats['total_requests'] += len(streaming_pairs)
    
    def _collect_pair_data(self, pair: TradingPair) -> Optional[PriceData]:
        """
        Coleta dados para um par específico usando múltiplas fontes
        
        Args:
            pair: Par para coletar dados
            
        Returns:
            PriceData se sucesso, None caso contrário
        """
        for source in self.data_sources:
            if not source.is_available:
                continue
            
            try:
                raw_data = source.fetch_data(pair.symbol)
                if raw_data:
                    # Converte para PriceData
                    price_data = PriceData(
                        timestamp=datetime.now(),
                        symbol=pair.symbol,
                        price=raw_data['price'],
                        open=raw_data.get('open', raw_data['price']),
                        high=raw_data.get('high', raw_data['price']),
                        low=raw_data.get('low', raw_data['price']),
                        close=raw_data.get('close', raw_data['price']),
                        volume=raw_data.get('volume', 0),
                        source=source.name
                    )
                    
                    # Atualiza estatísticas da fonte
                    self.stats['sources_used'][source.name] += 1
                    
                    logger.debug(f"Dados coletados para {pair.symbol} de {source.name}: ${price_data.price}")
                    return price_data
                    
            except Exception as e:
                logger.error(f"Erro ao coletar dados de {source.name} para {pair.symbol}: {e}")
                source._handle_error(f"Erro na coleta: {e}")
        
        # Se chegou até aqui, todas as fontes falharam
        logger.warning(f"Todas as fontes falharam para {pair.symbol}")
        return None
    
    # ==================== DADOS HISTÓRICOS ====================
    
    def get_pair_data(self, symbol: str, limit: int = 50) -> List[PriceData]:
        """
        Obtém dados históricos de um par
        
        Args:
            symbol: Símbolo do par
            limit: Número máximo de registros
            
        Returns:
            Lista de dados de preço
        """
        pair = trading_pair_manager.get_pair(symbol)
        if not pair:
            logger.warning(f"Par {symbol} não encontrado")
            return []
        
        return pair.get_price_history(limit)
    
    def get_all_pairs_data(self, limit: int = 10) -> Dict[str, List[PriceData]]:
        """
        Obtém dados de todos os pares
        
        Args:
            limit: Número máximo de registros por par
            
        Returns:
            Dicionário com dados de cada par
        """
        result = {}
        
        for pair in trading_pair_manager.get_all_pairs():
            data = pair.get_price_history(limit)
            if data:
                result[pair.symbol] = data
        
        return result
    
    def get_latest_prices(self) -> Dict[str, float]:
        """
        Obtém preços mais recentes de todos os pares
        
        Returns:
            Dicionário com preços atuais
        """
        prices = {}
        
        for pair in trading_pair_manager.get_all_pairs():
            latest = pair.get_latest_price()
            if latest:
                prices[pair.symbol] = latest.price
        
        return prices
    
    # ==================== ESTATÍSTICAS ====================
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas completas do streamer"""
        uptime = 0
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        # Calcula taxa de sucesso
        total_requests = self.stats['total_requests']
        success_rate = 0
        if total_requests > 0:
            success_rate = (self.stats['successful_requests'] / total_requests) * 100
        
        # Estatísticas das fontes
        sources_stats = {}
        for source in self.data_sources:
            sources_stats[source.name] = {
                'is_available': source.is_available,
                'error_count': source.error_count,
                'requests_made': self.stats['sources_used'][source.name],
                'rate_limit': source.rate_limit
            }
        
        return {
            'summary': {
                'is_running': self.is_running,
                'uptime_seconds': uptime,
                'active_streams': len(trading_pair_manager.get_streaming_pairs()),
                'total_pairs': len(trading_pair_manager.get_all_pairs()),
                'total_data_points': sum(len(p.price_history) for p in trading_pair_manager.get_all_pairs()),
                'total_requests': total_requests,
                'successful_requests': self.stats['successful_requests'],
                'failed_requests': self.stats['failed_requests'],
                'success_rate': success_rate,
                'last_update': self.stats['last_update'].isoformat() if self.stats['last_update'] else None
            },
            'sources': sources_stats,
            'pairs_status': {
                pair.symbol: {
                    'is_streaming': pair.is_streaming,
                    'data_points': len(pair.price_history),
                    'last_update': pair.last_update.isoformat() if pair.last_update else None,
                    'error_count': pair.error_count,
                    'health_status': 'healthy' if pair.is_streaming_healthy() else 'unhealthy'
                }
                for pair in trading_pair_manager.get_all_pairs()
            }
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de performance"""
        total_requests = self.stats['total_requests']
        uptime = 0
        
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        requests_per_second = total_requests / uptime if uptime > 0 else 0
        
        # Calcula latência média (simulada, seria necessário medir real)
        avg_latency = 0.5  # segundos (placeholder)
        
        return {
            'requests_per_second': requests_per_second,
            'avg_latency_seconds': avg_latency,
            'memory_usage_mb': self._estimate_memory_usage(),
            'thread_count': self.max_workers,
            'data_points_per_minute': self._calculate_data_points_per_minute(),
            'error_rate': (self.stats['failed_requests'] / total_requests * 100) if total_requests > 0 else 0
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estima uso de memória (simplificado)"""
        total_data_points = sum(len(p.price_history) for p in trading_pair_manager.get_all_pairs())
        # Aproximação: cada PriceData ~= 200 bytes
        estimated_mb = (total_data_points * 200) / (1024 * 1024)
        return round(estimated_mb, 2)
    
    def _calculate_data_points_per_minute(self) -> float:
        """Calcula pontos de dados coletados por minuto"""
        if not self.stats['start_time']:
            return 0
        
        uptime_minutes = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        total_data_points = sum(len(p.price_history) for p in trading_pair_manager.get_all_pairs())
        
        return total_data_points / uptime_minutes if uptime_minutes > 0 else 0
    
    # ==================== MANUTENÇÃO ====================
    
    def reset_all_errors(self):
        """Reseta erros de todas as fontes e pares"""
        # Reset fontes
        for source in self.data_sources:
            source.reset_errors()
        
        # Reset pares
        trading_pair_manager.reset_all_errors()
        
        logger.info("Todos os erros resetados")
    
    def cleanup_old_data(self, hours: int = 24):
        """
        Remove dados antigos dos pares
        
        Args:
            hours: Manter apenas dados das últimas X horas
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        total_removed = 0
        
        for pair in trading_pair_manager.get_all_pairs():
            old_count = len(pair.price_history)
            
            # Filtra dados recentes
            pair.price_history = [
                data for data in pair.price_history 
                if data.timestamp >= cutoff_time
            ]
            
            removed = old_count - len(pair.price_history)
            total_removed += removed
        
        logger.info(f"Cleanup: removidos {total_removed} pontos de dados antigos")
        return total_removed
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica saúde geral do sistema de streaming"""
        issues = []
        status = 'healthy'
        
        # Verifica se está rodando
        if not self.is_running:
            issues.append("Streaming não está em execução")
            status = 'stopped'
        
        # Verifica fontes de dados
        available_sources = [s for s in self.data_sources if s.is_available]
        if len(available_sources) == 0:
            issues.append("Nenhuma fonte de dados disponível")
            status = 'critical'
        elif len(available_sources) == 1:
            issues.append("Apenas uma fonte de dados disponível")
            if status == 'healthy':
                status = 'degraded'
        
        # Verifica pares em streaming
        streaming_pairs = trading_pair_manager.get_streaming_pairs()
        healthy_pairs = [p for p in streaming_pairs if p.is_streaming_healthy()]
        
        if len(streaming_pairs) == 0:
            issues.append("Nenhum par em streaming")
            if status == 'healthy':
                status = 'warning'
        elif len(healthy_pairs) < len(streaming_pairs):
            unhealthy_count = len(streaming_pairs) - len(healthy_pairs)
            issues.append(f"{unhealthy_count} pares com problemas de saúde")
            if status == 'healthy':
                status = 'degraded'
        
        # Verifica taxa de erro
        if self.stats['total_requests'] > 0:
            error_rate = (self.stats['failed_requests'] / self.stats['total_requests']) * 100
            if error_rate > 20:
                issues.append(f"Alta taxa de erro: {error_rate:.1f}%")
                if status == 'healthy':
                    status = 'degraded'
        
        return {
            'status': status,
            'issues': issues,
            'available_sources': len(available_sources),
            'total_sources': len(self.data_sources),
            'healthy_pairs': len(healthy_pairs),
            'total_streaming_pairs': len(streaming_pairs),
            'error_rate': (self.stats['failed_requests'] / self.stats['total_requests'] * 100) if self.stats['total_requests'] > 0 else 0,
            'uptime_hours': (datetime.now() - self.stats['start_time']).total_seconds() / 3600 if self.stats['start_time'] else 0
        }
    
    # ==================== CONFIGURAÇÃO ====================
    
    def update_config(self, **config):
        """Atualiza configurações do streamer"""
        if 'update_interval' in config:
            self.update_interval = max(1, int(config['update_interval']))
            logger.info(f"Intervalo de atualização alterado para {self.update_interval}s")
        
        if 'max_workers' in config and not self.is_running:
            self.max_workers = max(1, int(config['max_workers']))
            logger.info(f"Máximo de workers alterado para {self.max_workers}")
        
        # Atualiza configurações das fontes
        for source in self.data_sources:
            if f'{source.name.lower()}_rate_limit' in config:
                source.rate_limit = max(0.1, float(config[f'{source.name.lower()}_rate_limit']))
                logger.info(f"Rate limit da fonte {source.name} alterado para {source.rate_limit}s")
    
    def add_data_source(self, source: DataSource):
        """Adiciona nova fonte de dados"""
        self.data_sources.append(source)
        self.stats['sources_used'][source.name] = 0
        logger.info(f"Fonte de dados adicionada: {source.name}")
    
    def remove_data_source(self, source_name: str) -> bool:
        """Remove fonte de dados"""
        for i, source in enumerate(self.data_sources):
            if source.name == source_name:
                del self.data_sources[i]
                if source_name in self.stats['sources_used']:
                    del self.stats['sources_used'][source_name]
                logger.info(f"Fonte de dados removida: {source_name}")
                return True
        
        logger.warning(f"Fonte de dados não encontrada: {source_name}")
        return False
    
    # ==================== SHUTDOWN ====================
    
    def shutdown(self):
        """Finalização completa do streamer"""
        logger.info("Iniciando shutdown do MultiPairDataStreamer...")
        
        # Para streaming
        self.stop_all()
        
        # Cleanup de recursos
        if self.executor:
            self.executor.shutdown(wait=True)
        
        # Reset estatísticas
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': None,
            'last_update': None,
            'sources_used': {source.name: 0 for source in self.data_sources}
        }
        
        logger.info("MultiPairDataStreamer finalizado")
    
    def __str__(self) -> str:
        """Representação string do streamer"""
        streaming_count = len(trading_pair_manager.get_streaming_pairs())
        return f"MultiPairDataStreamer(running={self.is_running}, streaming_pairs={streaming_count}, sources={len(self.data_sources)})"


# Instância global do streamer
multi_pair_streamer = MultiPairDataStreamer()