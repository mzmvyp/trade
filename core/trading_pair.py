# core/trading_pair.py - Definição de Pares de Trading
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class PairStatus(Enum):
    """Status do par de trading"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class PriceData:
    """Estrutura de dados de preço"""
    timestamp: datetime
    symbol: str
    price: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'price': self.price,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'source': self.source
        }
    
    @classmethod
    def from_api_data(cls, symbol: str, api_data: Dict[str, Any], source: str = "unknown"):
        """Cria instância a partir de dados da API"""
        try:
            # Mapeia campos comuns das APIs
            price = float(api_data.get('price', api_data.get('last', 0)))
            
            return cls(
                timestamp=datetime.now(),
                symbol=symbol,
                price=price,
                open=float(api_data.get('open', price)),
                high=float(api_data.get('high', price)),
                low=float(api_data.get('low', price)),
                close=float(api_data.get('close', price)),
                volume=float(api_data.get('volume', 0)),
                source=source
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Erro ao criar PriceData de {source}: {e}")
            raise

class TradingPair:
    """
    Representa um par de trading (ex: BTCUSDT)
    Gerencia configurações, status e dados históricos
    """
    
    def __init__(self, symbol: str, display_name: str, enabled: bool = True, 
                 color: str = "#007bff", icon: str = "fas fa-coins"):
        """
        Inicializa par de trading
        
        Args:
            symbol: Símbolo do par (ex: BTCUSDT)
            display_name: Nome para exibição (ex: Bitcoin/USDT)
            enabled: Se o par está habilitado
            color: Cor para exibição
            icon: Ícone para exibição
        """
        self.symbol = symbol.upper()
        self.display_name = display_name
        self.enabled = enabled
        self.color = color
        self.icon = icon
        
        # Estado interno
        self.status = PairStatus.ENABLED if enabled else PairStatus.DISABLED
        self.is_streaming = False
        self.last_update = None
        self.error_count = 0
        self.last_error = None
        
        # Configurações de streaming
        self.update_interval = 5  # segundos
        self.max_errors = 10
        self.retry_delay = 30  # segundos
        
        # Dados históricos em memória (limitado)
        self.price_history: List[PriceData] = []
        self.max_history_size = 1000
        
        # Estatísticas
        self.stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'first_update': None,
            'last_successful_update': None,
            'avg_price_24h': 0.0,
            'price_change_24h': 0.0,
            'volume_24h': 0.0
        }
        
        logger.info(f"TradingPair criado: {self.symbol} - {self.display_name}")
    
    # ==================== CONFIGURAÇÃO ====================
    
    def enable(self):
        """Habilita o par para trading"""
        self.enabled = True
        self.status = PairStatus.ENABLED
        self.error_count = 0
        logger.info(f"Par {self.symbol} habilitado")
    
    def disable(self):
        """Desabilita o par para trading"""
        self.enabled = False
        self.status = PairStatus.DISABLED
        self.is_streaming = False
        logger.info(f"Par {self.symbol} desabilitado")
    
    def set_maintenance(self, reason: str = "Manutenção"):
        """Coloca par em manutenção"""
        self.status = PairStatus.MAINTENANCE
        self.is_streaming = False
        self.last_error = reason
        logger.warning(f"Par {self.symbol} em manutenção: {reason}")
    
    def update_config(self, **kwargs):
        """Atualiza configurações do par"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.debug(f"Config {key} atualizada para {value} no par {self.symbol}")
    
    # ==================== DADOS DE PREÇO ====================
    
    def add_price_data(self, price_data: PriceData):
        """
        Adiciona dados de preço ao histórico
        
        Args:
            price_data: Dados de preço a serem adicionados
        """
        try:
            # Adiciona ao histórico
            self.price_history.append(price_data)
            
            # Mantém tamanho limitado do histórico
            if len(self.price_history) > self.max_history_size:
                self.price_history = self.price_history[-self.max_history_size:]
            
            # Atualiza estatísticas
            self._update_stats(price_data)
            
            # Marca update bem-sucedido
            self.last_update = datetime.now()
            self.stats['successful_updates'] += 1
            self.error_count = 0  # Reset contador de erros
            
            logger.debug(f"Dados adicionados para {self.symbol}: ${price_data.price}")
            
        except Exception as e:
            self._handle_error(f"Erro ao adicionar dados de preço: {e}")
    
    def get_latest_price(self) -> Optional[PriceData]:
        """Retorna dados de preço mais recentes"""
        return self.price_history[-1] if self.price_history else None
    
    def get_price_history(self, limit: int = None) -> List[PriceData]:
        """
        Retorna histórico de preços
        
        Args:
            limit: Número máximo de registros (None = todos)
            
        Returns:
            Lista de dados de preço
        """
        if limit is None:
            return self.price_history.copy()
        
        return self.price_history[-limit:] if limit > 0 else []
    
    def get_price_range(self, hours: int = 24) -> Dict[str, float]:
        """
        Calcula range de preços para período específico
        
        Args:
            hours: Número de horas para calcular o range
            
        Returns:
            Dicionário com min, max, média dos preços
        """
        cutoff_time = datetime.now().replace(microsecond=0)
        cutoff_time = cutoff_time.replace(hour=cutoff_time.hour - hours)
        
        recent_prices = [
            data.price for data in self.price_history 
            if data.timestamp >= cutoff_time
        ]
        
        if not recent_prices:
            return {'min': 0.0, 'max': 0.0, 'avg': 0.0, 'count': 0}
        
        return {
            'min': min(recent_prices),
            'max': max(recent_prices),
            'avg': sum(recent_prices) / len(recent_prices),
            'count': len(recent_prices)
        }
    
    # ==================== STREAMING ====================
    
    def start_streaming(self) -> bool:
        """
        Inicia streaming de dados
        
        Returns:
            True se iniciado com sucesso, False caso contrário
        """
        if not self.enabled:
            logger.warning(f"Tentativa de iniciar streaming para par desabilitado: {self.symbol}")
            return False
        
        if self.status == PairStatus.MAINTENANCE:
            logger.warning(f"Tentativa de iniciar streaming para par em manutenção: {self.symbol}")
            return False
        
        self.is_streaming = True
        self.status = PairStatus.ENABLED
        logger.info(f"Streaming iniciado para {self.symbol}")
        return True
    
    def stop_streaming(self):
        """Para streaming de dados"""
        self.is_streaming = False
        logger.info(f"Streaming parado para {self.symbol}")
    
    def is_streaming_healthy(self) -> bool:
        """Verifica se streaming está saudável"""
        if not self.is_streaming:
            return False
        
        # Verifica se teve update recente
        if self.last_update:
            time_since_update = (datetime.now() - self.last_update).total_seconds()
            if time_since_update > self.update_interval * 3:  # 3x o intervalo normal
                return False
        
        # Verifica contador de erros
        if self.error_count >= self.max_errors:
            return False
        
        return True
    
    # ==================== ESTATÍSTICAS ====================
    
    def _update_stats(self, price_data: PriceData):
        """Atualiza estatísticas internas"""
        self.stats['total_updates'] += 1
        self.stats['last_successful_update'] = price_data.timestamp
        
        if self.stats['first_update'] is None:
            self.stats['first_update'] = price_data.timestamp
        
        # Calcula estatísticas de 24h
        self._calculate_24h_stats()
    
    def _calculate_24h_stats(self):
        """Calcula estatísticas de 24 horas"""
        range_data = self.get_price_range(24)
        self.stats['avg_price_24h'] = range_data['avg']
        
        # Calcula mudança de preço 24h
        if len(self.price_history) >= 2:
            current_price = self.price_history[-1].price
            
            # Encontra preço de ~24h atrás
            cutoff_time = datetime.now().replace(microsecond=0)
            cutoff_time = cutoff_time.replace(hour=cutoff_time.hour - 24)
            
            old_prices = [
                data.price for data in self.price_history 
                if data.timestamp <= cutoff_time
            ]
            
            if old_prices:
                old_price = old_prices[-1]  # Preço mais próximo de 24h atrás
                self.stats['price_change_24h'] = ((current_price - old_price) / old_price) * 100
            else:
                self.stats['price_change_24h'] = 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas completas do par"""
        latest = self.get_latest_price()
        
        return {
            'symbol': self.symbol,
            'display_name': self.display_name,
            'current_price': latest.price if latest else 0.0,
            'is_streaming': self.is_streaming,
            'status': self.status.value,
            'total_updates': self.stats['total_updates'],
            'successful_updates': self.stats['successful_updates'],
            'failed_updates': self.stats['failed_updates'],
            'success_rate': self._calculate_success_rate(),
            'price_change_24h': self.stats['price_change_24h'],
            'avg_price_24h': self.stats['avg_price_24h'],
            'data_points': len(self.price_history),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'error_count': self.error_count,
            'health_status': 'healthy' if self.is_streaming_healthy() else 'unhealthy'
        }
    
    def _calculate_success_rate(self) -> float:
        """Calcula taxa de sucesso dos updates"""
        total = self.stats['total_updates']
        if total == 0:
            return 0.0
        
        return (self.stats['successful_updates'] / total) * 100
    
    # ==================== ERROR HANDLING ====================
    
    def _handle_error(self, error_message: str):
        """Trata erros do par"""
        self.error_count += 1
        self.last_error = error_message
        self.stats['failed_updates'] += 1
        
        logger.error(f"Erro no par {self.symbol}: {error_message}")
        
        # Se muitos erros, coloca em manutenção
        if self.error_count >= self.max_errors:
            self.set_maintenance(f"Muitos erros consecutivos: {self.error_count}")
    
    def reset_errors(self):
        """Reseta contador de erros"""
        self.error_count = 0
        self.last_error = None
        
        if self.status == PairStatus.MAINTENANCE and self.enabled:
            self.status = PairStatus.ENABLED
        
        logger.info(f"Erros resetados para {self.symbol}")
    
    # ==================== STATUS ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual do par"""
        latest = self.get_latest_price()
        
        return {
            'symbol': self.symbol,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'status': self.status.value,
            'is_streaming': self.is_streaming,
            'color': self.color,
            'icon': self.icon,
            'current_price': latest.price if latest else 0.0,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'data_points': len(self.price_history),
            'error_count': self.error_count,
            'health_status': 'healthy' if self.is_streaming_healthy() else 'unhealthy',
            'price_change_24h': self.stats['price_change_24h']
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte par para dicionário"""
        return self.get_status()
    
    def __str__(self) -> str:
        """Representação string do par"""
        return f"TradingPair({self.symbol}: {self.display_name}, enabled={self.enabled}, streaming={self.is_streaming})"
    
    def __repr__(self) -> str:
        """Representação para debug"""
        return self.__str__()


class TradingPairManager:
    """
    Gerenciador de pares de trading
    Centraliza operações com múltiplos pares
    """
    
    def __init__(self):
        """Inicializa gerenciador de pares"""
        self.pairs: Dict[str, TradingPair] = {}
        self.logger = logger
        
        # Inicializa pares padrão
        self._initialize_default_pairs()
        
        logger.info("TradingPairManager inicializado")
    
    def _initialize_default_pairs(self):
        """Inicializa pares padrão do sistema"""
        default_pairs = [
            {
                'symbol': 'BTCUSDT',
                'display_name': 'Bitcoin/USDT',
                'enabled': True,
                'color': '#f7931a',
                'icon': 'fab fa-bitcoin'
            },
            {
                'symbol': 'ETHUSDT',
                'display_name': 'Ethereum/USDT',
                'enabled': True,
                'color': '#627eea',
                'icon': 'fab fa-ethereum'
            },
            {
                'symbol': 'SOLUSDT',
                'display_name': 'Solana/USDT',
                'enabled': False,
                'color': '#9945ff',
                'icon': 'fas fa-sun'
            },
            {
                'symbol': 'BNBUSDT',
                'display_name': 'BNB/USDT',
                'enabled': False,
                'color': '#f3ba2f',
                'icon': 'fas fa-coins'
            },
            {
                'symbol': 'ADAUSDT',
                'display_name': 'Cardano/USDT',
                'enabled': False,
                'color': '#0033ad',
                'icon': 'fas fa-heart'
            },
            {
                'symbol': 'DOTUSDT',
                'display_name': 'Polkadot/USDT',
                'enabled': False,
                'color': '#e6007a',
                'icon': 'fas fa-circle'
            },
            {
                'symbol': 'LINKUSDT',
                'display_name': 'Chainlink/USDT',
                'enabled': False,
                'color': '#2a5ada',
                'icon': 'fas fa-link'
            }
        ]
        
        for pair_config in default_pairs:
            self.add_pair(**pair_config)
    
    # ==================== GERENCIAMENTO DE PARES ====================
    
    def add_pair(self, symbol: str, display_name: str, enabled: bool = True, 
                 color: str = "#007bff", icon: str = "fas fa-coins") -> TradingPair:
        """
        Adiciona novo par de trading
        
        Args:
            symbol: Símbolo do par
            display_name: Nome para exibição
            enabled: Se está habilitado
            color: Cor para exibição
            icon: Ícone para exibição
            
        Returns:
            Instância do TradingPair criado
        """
        symbol = symbol.upper()
        
        if symbol in self.pairs:
            logger.warning(f"Par {symbol} já existe, atualizando configurações")
            pair = self.pairs[symbol]
            pair.display_name = display_name
            pair.enabled = enabled
            pair.color = color
            pair.icon = icon
            return pair
        
        pair = TradingPair(symbol, display_name, enabled, color, icon)
        self.pairs[symbol] = pair
        
        logger.info(f"Par adicionado: {symbol} - {display_name}")
        return pair
    
    def remove_pair(self, symbol: str) -> bool:
        """
        Remove par de trading
        
        Args:
            symbol: Símbolo do par a ser removido
            
        Returns:
            True se removido, False se não encontrado
        """
        symbol = symbol.upper()
        
        if symbol not in self.pairs:
            logger.warning(f"Tentativa de remover par inexistente: {symbol}")
            return False
        
        # Para streaming se estiver ativo
        pair = self.pairs[symbol]
        if pair.is_streaming:
            pair.stop_streaming()
        
        del self.pairs[symbol]
        logger.info(f"Par removido: {symbol}")
        return True
    
    def get_pair(self, symbol: str) -> Optional[TradingPair]:
        """
        Obtém par específico
        
        Args:
            symbol: Símbolo do par
            
        Returns:
            TradingPair ou None se não encontrado
        """
        return self.pairs.get(symbol.upper())
    
    def get_all_pairs(self) -> List[TradingPair]:
        """Retorna todos os pares"""
        return list(self.pairs.values())
    
    def get_enabled_pairs(self) -> List[TradingPair]:
        """Retorna apenas pares habilitados"""
        return [pair for pair in self.pairs.values() if pair.enabled]
    
    def get_streaming_pairs(self) -> List[TradingPair]:
        """Retorna pares que estão em streaming"""
        return [pair for pair in self.pairs.values() if pair.is_streaming]
    
    # ==================== OPERAÇÕES EM LOTE ====================
    
    def enable_all_pairs(self):
        """Habilita todos os pares"""
        for pair in self.pairs.values():
            pair.enable()
        logger.info("Todos os pares habilitados")
    
    def disable_all_pairs(self):
        """Desabilita todos os pares"""
        for pair in self.pairs.values():
            pair.disable()
        logger.info("Todos os pares desabilitados")
    
    def start_all_streaming(self) -> int:
        """
        Inicia streaming para todos os pares habilitados
        
        Returns:
            Número de pares que iniciaram streaming com sucesso
        """
        count = 0
        for pair in self.get_enabled_pairs():
            if pair.start_streaming():
                count += 1
        
        logger.info(f"Streaming iniciado para {count} pares")
        return count
    
    def stop_all_streaming(self):
        """Para streaming para todos os pares"""
        streaming_pairs = self.get_streaming_pairs()
        
        for pair in streaming_pairs:
            pair.stop_streaming()
        
        logger.info(f"Streaming parado para {len(streaming_pairs)} pares")
    
    def reset_all_errors(self):
        """Reseta erros de todos os pares"""
        for pair in self.pairs.values():
            pair.reset_errors()
        logger.info("Erros resetados para todos os pares")
    
    # ==================== ESTATÍSTICAS ====================
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo do gerenciador"""
        enabled_pairs = self.get_enabled_pairs()
        streaming_pairs = self.get_streaming_pairs()
        
        # Calcula estatísticas agregadas
        total_data_points = sum(len(pair.price_history) for pair in self.pairs.values())
        total_updates = sum(pair.stats['total_updates'] for pair in self.pairs.values())
        successful_updates = sum(pair.stats['successful_updates'] for pair in self.pairs.values())
        
        return {
            'total_pairs': len(self.pairs),
            'enabled_pairs': len(enabled_pairs),
            'streaming_pairs': len(streaming_pairs),
            'total_data_points': total_data_points,
            'total_updates': total_updates,
            'successful_updates': successful_updates,
            'success_rate': (successful_updates / total_updates * 100) if total_updates > 0 else 0,
            'healthy_pairs': len([p for p in self.pairs.values() if p.is_streaming_healthy()]),
            'pairs_in_error': len([p for p in self.pairs.values() if p.error_count > 0])
        }
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas detalhadas de todos os pares"""
        return {
            'summary': self.get_summary(),
            'pairs': {symbol: pair.get_statistics() for symbol, pair in self.pairs.items()}
        }
    
    def get_health_report(self) -> Dict[str, Any]:
        """Gera relatório de saúde dos pares"""
        healthy_pairs = []
        unhealthy_pairs = []
        maintenance_pairs = []
        
        for pair in self.pairs.values():
            if pair.status == PairStatus.MAINTENANCE:
                maintenance_pairs.append(pair.symbol)
            elif pair.is_streaming_healthy():
                healthy_pairs.append(pair.symbol)
            else:
                unhealthy_pairs.append(pair.symbol)
        
        return {
            'healthy_pairs': healthy_pairs,
            'unhealthy_pairs': unhealthy_pairs,
            'maintenance_pairs': maintenance_pairs,
            'overall_health': 'healthy' if len(unhealthy_pairs) == 0 else 'degraded'
        }
    
    # ==================== CONFIGURAÇÃO ====================
    
    def update_pair_config(self, symbol: str, **config) -> bool:
        """
        Atualiza configuração de um par
        
        Args:
            symbol: Símbolo do par
            **config: Configurações a serem atualizadas
            
        Returns:
            True se atualizado com sucesso
        """
        pair = self.get_pair(symbol)
        if not pair:
            logger.warning(f"Tentativa de atualizar configuração de par inexistente: {symbol}")
            return False
        
        pair.update_config(**config)
        return True
    
    def bulk_update_config(self, pairs_config: Dict[str, Dict[str, Any]]):
        """
        Atualiza configuração de múltiplos pares
        
        Args:
            pairs_config: Dict com símbolo -> configurações
        """
        for symbol, config in pairs_config.items():
            self.update_pair_config(symbol, **config)
    
    # ==================== PERSISTÊNCIA ====================
    
    def export_config(self) -> Dict[str, Any]:
        """Exporta configuração atual dos pares"""
        config = {
            'pairs': {},
            'exported_at': datetime.now().isoformat(),
            'total_pairs': len(self.pairs)
        }
        
        for symbol, pair in self.pairs.items():
            config['pairs'][symbol] = {
                'display_name': pair.display_name,
                'enabled': pair.enabled,
                'color': pair.color,
                'icon': pair.icon,
                'update_interval': pair.update_interval,
                'max_errors': pair.max_errors,
                'retry_delay': pair.retry_delay
            }
        
        return config
    
    def import_config(self, config: Dict[str, Any]) -> bool:
        """
        Importa configuração de pares
        
        Args:
            config: Configuração a ser importada
            
        Returns:
            True se importado com sucesso
        """
        try:
            pairs_config = config.get('pairs', {})
            
            for symbol, pair_config in pairs_config.items():
                self.add_pair(
                    symbol=symbol,
                    display_name=pair_config.get('display_name', symbol),
                    enabled=pair_config.get('enabled', True),
                    color=pair_config.get('color', '#007bff'),
                    icon=pair_config.get('icon', 'fas fa-coins')
                )
                
                # Atualiza configurações adicionais
                if symbol in self.pairs:
                    pair = self.pairs[symbol]
                    pair.update_interval = pair_config.get('update_interval', 5)
                    pair.max_errors = pair_config.get('max_errors', 10)
                    pair.retry_delay = pair_config.get('retry_delay', 30)
            
            logger.info(f"Configuração importada: {len(pairs_config)} pares")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao importar configuração: {e}")
            return False
    
    def __str__(self) -> str:
        """Representação string do gerenciador"""
        return f"TradingPairManager({len(self.pairs)} pares, {len(self.get_enabled_pairs())} habilitados)"


# Instância global do gerenciador
trading_pair_manager = TradingPairManager()