# config/settings.py - Configurações do Sistema
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Configurações do banco de dados"""
    path: str = "data/trading_system.db"
    connection_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1
    cleanup_days: int = 30
    backup_enabled: bool = True
    backup_interval_hours: int = 24

@dataclass
class StreamingConfig:
    """Configurações de streaming de dados"""
    update_interval: int = 5  # segundos
    max_workers: int = 5
    connection_timeout: int = 10
    max_retries: int = 3
    retry_delay: int = 1
    rate_limit_binance: float = 0.5
    rate_limit_coingecko: float = 1.0
    rate_limit_simulated: float = 0.1
    fallback_to_simulated: bool = True

@dataclass
class TradingConfig:
    """Configurações de trading"""
    default_stop_loss_pct: float = 2.0
    default_take_profit_pct: float = 4.0
    max_concurrent_signals: int = 10
    signal_expiry_hours: int = 24
    min_confidence_threshold: float = 0.6
    risk_per_trade_pct: float = 1.0
    max_daily_trades: int = 20

@dataclass
class AnalyticsConfig:
    """Configurações de analytics"""
    indicators_enabled: List[str] = field(default_factory=lambda: [
        'RSI', 'MACD', 'SMA_12', 'SMA_30', 'EMA_12', 'EMA_30',
        'BB_UPPER', 'BB_LOWER', 'BB_MIDDLE', 'STOCH_K', 'STOCH_D'
    ])
    timeframes: List[str] = field(default_factory=lambda: ['5m', '15m', '1h', '4h', '1d'])
    history_days: int = 30
    pattern_detection_enabled: bool = True
    technical_analysis_enabled: bool = True

@dataclass
class WebConfig:
    """Configurações da interface web"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    secret_key: str = "trading-system-secret-key"
    max_content_length: int = 16 * 1024 * 1024  # 16MB
    session_timeout: int = 3600  # 1 hour
    cors_enabled: bool = True

@dataclass
class LoggingConfig:
    """Configurações de logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "logs/trading_system.log"
    file_max_size: int = 10 * 1024 * 1024  # 10MB
    file_backup_count: int = 5
    console_enabled: bool = True

class Config:
    """
    Classe principal de configuração do sistema
    Centraliza todas as configurações e fornece validação
    """
    
    # Versão do sistema
    VERSION = "1.0.0"
    
    def __init__(self):
        """Inicializa configurações com valores padrão e variáveis de ambiente"""
        
        # Configurações gerais
        self.DEBUG = self._get_bool_env('DEBUG', False)
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'trading-system-secret-key-change-in-production')
        
        # Diretórios base
        self.BASE_DIR = Path(__file__).parent.parent
        self.DATA_DIR = self.BASE_DIR / 'data'
        self.LOGS_DIR = self.BASE_DIR / 'logs'
        self.STATIC_DIR = self.BASE_DIR / 'static'
        self.TEMPLATES_DIR = self.BASE_DIR / 'templates'
        
        # Cria diretórios se não existem
        self._ensure_directories()
        
        # Configurações específicas
        self.database = DatabaseConfig(
            path=os.getenv('DATABASE_PATH', str(self.DATA_DIR / 'trading_system.db')),
            connection_timeout=self._get_int_env('DB_CONNECTION_TIMEOUT', 30),
            max_retries=self._get_int_env('DB_MAX_RETRIES', 3),
            cleanup_days=self._get_int_env('DB_CLEANUP_DAYS', 30),
            backup_enabled=self._get_bool_env('DB_BACKUP_ENABLED', True),
            backup_interval_hours=self._get_int_env('DB_BACKUP_INTERVAL', 24)
        )
        
        self.streaming = StreamingConfig(
            update_interval=self._get_int_env('STREAMING_INTERVAL', 5),
            max_workers=self._get_int_env('STREAMING_MAX_WORKERS', 5),
            connection_timeout=self._get_int_env('STREAMING_TIMEOUT', 10),
            max_retries=self._get_int_env('STREAMING_MAX_RETRIES', 3),
            rate_limit_binance=self._get_float_env('RATE_LIMIT_BINANCE', 0.5),
            rate_limit_coingecko=self._get_float_env('RATE_LIMIT_COINGECKO', 1.0),
            fallback_to_simulated=self._get_bool_env('FALLBACK_SIMULATED', True)
        )
        
        self.trading = TradingConfig(
            default_stop_loss_pct=self._get_float_env('DEFAULT_STOP_LOSS', 2.0),
            default_take_profit_pct=self._get_float_env('DEFAULT_TAKE_PROFIT', 4.0),
            max_concurrent_signals=self._get_int_env('MAX_CONCURRENT_SIGNALS', 10),
            signal_expiry_hours=self._get_int_env('SIGNAL_EXPIRY_HOURS', 24),
            min_confidence_threshold=self._get_float_env('MIN_CONFIDENCE', 0.6),
            risk_per_trade_pct=self._get_float_env('RISK_PER_TRADE', 1.0),
            max_daily_trades=self._get_int_env('MAX_DAILY_TRADES', 20)
        )
        
        self.analytics = AnalyticsConfig(
            history_days=self._get_int_env('ANALYTICS_HISTORY_DAYS', 30),
            pattern_detection_enabled=self._get_bool_env('PATTERN_DETECTION', True),
            technical_analysis_enabled=self._get_bool_env('TECHNICAL_ANALYSIS', True)
        )
        
        self.web = WebConfig(
            host=os.getenv('HOST', '0.0.0.0'),
            port=self._get_int_env('PORT', 5000),
            debug=self.DEBUG,
            secret_key=self.SECRET_KEY,
            cors_enabled=self._get_bool_env('CORS_ENABLED', True)
        )
        
        self.logging = LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            file_enabled=self._get_bool_env('LOG_FILE_ENABLED', True),
            file_path=os.getenv('LOG_FILE_PATH', str(self.LOGS_DIR / 'trading_system.log')),
            console_enabled=self._get_bool_env('LOG_CONSOLE_ENABLED', True)
        )
        
        logger.info("Configurações carregadas")
    
    # ==================== HELPERS PARA VARIÁVEIS DE AMBIENTE ====================
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Obtém variável de ambiente como boolean"""
        value = os.getenv(key, '').lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        else:
            return default
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Obtém variável de ambiente como inteiro"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Valor inválido para {key}, usando padrão: {default}")
            return default
    
    def _get_float_env(self, key: str, default: float) -> float:
        """Obtém variável de ambiente como float"""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Valor inválido para {key}, usando padrão: {default}")
            return default
    
    def _get_list_env(self, key: str, default: List[str], separator: str = ',') -> List[str]:
        """Obtém variável de ambiente como lista"""
        value = os.getenv(key, '')
        if value:
            return [item.strip() for item in value.split(separator) if item.strip()]
        return default
    
    def _ensure_directories(self):
        """Cria diretórios necessários"""
        directories = [
            self.DATA_DIR,
            self.LOGS_DIR,
            self.STATIC_DIR / 'css',
            self.STATIC_DIR / 'js',
            self.STATIC_DIR / 'images',
            self.TEMPLATES_DIR,
            self.TEMPLATES_DIR / 'errors'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    # ==================== VALIDAÇÃO ====================
    
    def validate(self) -> List[str]:
        """
        Valida configurações e retorna lista de erros/avisos
        
        Returns:
            Lista de mensagens de erro ou aviso
        """
        issues = []
        
        # Validação de diretórios
        if not self.DATA_DIR.exists():
            issues.append(f"Diretório de dados não existe: {self.DATA_DIR}")
        
        if not self.LOGS_DIR.exists():
            issues.append(f"Diretório de logs não existe: {self.LOGS_DIR}")
        
        # Validação de banco de dados
        if not self.database.path:
            issues.append("Caminho do banco de dados não configurado")
        
        if self.database.connection_timeout < 5:
            issues.append("Timeout de conexão muito baixo (< 5s)")
        
        if self.database.cleanup_days < 1:
            issues.append("Dias de cleanup deve ser >= 1")
        
        # Validação de streaming
        if self.streaming.update_interval < 1:
            issues.append("Intervalo de atualização deve ser >= 1 segundo")
        
        if self.streaming.max_workers < 1:
            issues.append("Número de workers deve ser >= 1")
        
        if self.streaming.max_workers > 20:
            issues.append("Muitos workers podem causar problemas de performance")
        
        # Validação de trading
        if self.trading.default_stop_loss_pct <= 0:
            issues.append("Stop loss deve ser > 0%")
        
        if self.trading.default_take_profit_pct <= 0:
            issues.append("Take profit deve ser > 0%")
        
        if self.trading.min_confidence_threshold < 0 or self.trading.min_confidence_threshold > 1:
            issues.append("Threshold de confiança deve estar entre 0 e 1")
        
        if self.trading.risk_per_trade_pct > 10:
            issues.append("Risco por trade muito alto (> 10%)")
        
        # Validação de web
        if self.web.port < 1024 and not self._is_privileged_user():
            issues.append("Porta < 1024 requer privilégios administrativos")
        
        if self.web.port > 65535:
            issues.append("Porta inválida (> 65535)")
        
        # Validação de logging
        if self.logging.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            issues.append(f"Nível de log inválido: {self.logging.level}")
        
        return issues
    
    def _is_privileged_user(self) -> bool:
        """Verifica se usuário tem privilégios administrativos"""
        try:
            import os
            return os.getuid() == 0  # Unix/Linux
        except AttributeError:
            # Windows
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    # ==================== CONFIGURAÇÕES DINÂMICAS ====================
    
    def update_config(self, section: str, **kwargs):
        """
        Atualiza configurações dinamicamente
        
        Args:
            section: Seção da configuração (database, streaming, etc.)
            **kwargs: Novos valores de configuração
        """
        if not hasattr(self, section):
            raise ValueError(f"Seção de configuração inválida: {section}")
        
        config_obj = getattr(self, section)
        
        for key, value in kwargs.items():
            if hasattr(config_obj, key):
                old_value = getattr(config_obj, key)
                setattr(config_obj, key, value)
                logger.info(f"Configuração atualizada: {section}.{key} = {value} (anterior: {old_value})")
            else:
                logger.warning(f"Configuração desconhecida ignorada: {section}.{key}")
    
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Retorna todas as configurações como dicionário
        
        Returns:
            Dicionário com todas as configurações
        """
        return {
            'version': self.VERSION,
            'environment': self.ENVIRONMENT,
            'debug': self.DEBUG,
            'database': {
                'path': self.database.path,
                'connection_timeout': self.database.connection_timeout,
                'max_retries': self.database.max_retries,
                'cleanup_days': self.database.cleanup_days,
                'backup_enabled': self.database.backup_enabled,
                'backup_interval_hours': self.database.backup_interval_hours
            },
            'streaming': {
                'update_interval': self.streaming.update_interval,
                'max_workers': self.streaming.max_workers,
                'connection_timeout': self.streaming.connection_timeout,
                'max_retries': self.streaming.max_retries,
                'rate_limit_binance': self.streaming.rate_limit_binance,
                'rate_limit_coingecko': self.streaming.rate_limit_coingecko,
                'fallback_to_simulated': self.streaming.fallback_to_simulated
            },
            'trading': {
                'default_stop_loss_pct': self.trading.default_stop_loss_pct,
                'default_take_profit_pct': self.trading.default_take_profit_pct,
                'max_concurrent_signals': self.trading.max_concurrent_signals,
                'signal_expiry_hours': self.trading.signal_expiry_hours,
                'min_confidence_threshold': self.trading.min_confidence_threshold,
                'risk_per_trade_pct': self.trading.risk_per_trade_pct,
                'max_daily_trades': self.trading.max_daily_trades
            },
            'analytics': {
                'indicators_enabled': self.analytics.indicators_enabled,
                'timeframes': self.analytics.timeframes,
                'history_days': self.analytics.history_days,
                'pattern_detection_enabled': self.analytics.pattern_detection_enabled,
                'technical_analysis_enabled': self.analytics.technical_analysis_enabled
            },
            'web': {
                'host': self.web.host,
                'port': self.web.port,
                'debug': self.web.debug,
                'cors_enabled': self.web.cors_enabled,
                'max_content_length': self.web.max_content_length,
                'session_timeout': self.web.session_timeout
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file_enabled': self.logging.file_enabled,
                'file_path': self.logging.file_path,
                'console_enabled': self.logging.console_enabled
            }
        }
    
    # ==================== CONFIGURAÇÕES ESPECÍFICAS ====================
    
    def get_database_url(self) -> str:
        """Retorna URL de conexão do banco de dados"""
        return f"sqlite:///{self.database.path}"
    
    def get_api_endpoints(self) -> Dict[str, str]:
        """Retorna endpoints das APIs externas"""
        return {
            'binance': 'https://api.binance.com',
            'coingecko': 'https://api.coingecko.com',
            'alternative_me': 'https://api.alternative.me'  # Fear & Greed Index
        }
    
    def get_enabled_pairs(self) -> List[str]:
        """Retorna lista de pares habilitados por padrão"""
        return [
            'BTCUSDT',  # Bitcoin sempre habilitado
            'ETHUSDT'   # Ethereum sempre habilitado
        ]
    
    def get_technical_indicators_config(self) -> Dict[str, Dict[str, Any]]:
        """Retorna configuração dos indicadores técnicos"""
        return {
            'RSI': {
                'period': 14,
                'overbought': 70,
                'oversold': 30
            },
            'MACD': {
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9
            },
            'SMA': {
                'periods': [12, 30, 50, 200]
            },
            'EMA': {
                'periods': [12, 30, 50, 200]
            },
            'BB': {  # Bollinger Bands
                'period': 20,
                'std_dev': 2
            },
            'STOCH': {  # Stochastic
                'k_period': 14,
                'd_period': 3,
                'overbought': 80,
                'oversold': 20
            }
        }
    
    def get_pattern_detection_config(self) -> Dict[str, Any]:
        """Retorna configuração de detecção de padrões"""
        return {
            'enabled_patterns': [
                'DOUBLE_BOTTOM',
                'HEAD_AND_SHOULDERS',
                'TRIANGLE_BREAKOUT_UP',
                'TRIANGLE_BREAKOUT_DOWN',
                'SUPPORT_RESISTANCE',
                'TREND_REVERSAL'
            ],
            'min_candles': 20,
            'max_candles': 100,
            'tolerance_pct': 2.0,
            'volume_confirmation': True
        }
    
    def get_risk_management_config(self) -> Dict[str, Any]:
        """Retorna configuração de gerenciamento de risco"""
        return {
            'max_portfolio_risk': 10.0,  # % do portfólio
            'max_correlation': 0.7,      # Correlação máxima entre posições
            'position_sizing': 'fixed',   # fixed, kelly, optimal_f
            'stop_loss_trailing': True,
            'profit_taking_strategy': 'scaled',  # full, scaled, trailing
            'daily_loss_limit': 5.0,    # % de perda diária máxima
            'drawdown_limit': 15.0      # % de drawdown máximo
        }
    
    # ==================== PERSISTÊNCIA ====================
    
    def save_to_file(self, file_path: Optional[str] = None):
        """
        Salva configurações em arquivo
        
        Args:
            file_path: Caminho do arquivo (opcional)
        """
        if file_path is None:
            file_path = self.DATA_DIR / 'config_backup.json'
        
        import json
        
        config_dict = self.get_config_dict()
        
        # Remove informações sensíveis
        config_dict.pop('secret_key', None)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            logger.info(f"Configurações salvas em: {file_path}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            raise
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Carrega configurações de arquivo
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se carregado com sucesso
        """
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # Atualiza configurações por seção
            for section, values in config_dict.items():
                if section in ['version', 'environment', 'debug']:
                    continue  # Pula configurações de sistema
                
                if isinstance(values, dict):
                    try:
                        self.update_config(section, **values)
                    except ValueError as e:
                        logger.warning(f"Seção ignorada: {e}")
            
            logger.info(f"Configurações carregadas de: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            return False
    
    # ==================== AMBIENTE DE DESENVOLVIMENTO ====================
    
    def setup_development_mode(self):
        """Configura modo de desenvolvimento"""
        self.DEBUG = True
        self.web.debug = True
        self.logging.level = 'DEBUG'
        self.logging.console_enabled = True
        
        # Configurações mais permissivas para desenvolvimento
        self.streaming.fallback_to_simulated = True
        self.database.backup_enabled = False
        
        logger.info("Modo de desenvolvimento ativado")
    
    def setup_production_mode(self):
        """Configura modo de produção"""
        self.DEBUG = False
        self.web.debug = False
        self.logging.level = 'INFO'
        
        # Configurações mais restritivas para produção
        self.streaming.fallback_to_simulated = False
        self.database.backup_enabled = True
        
        # Valida configurações críticas
        if self.SECRET_KEY == 'trading-system-secret-key-change-in-production':
            raise ValueError("SECRET_KEY deve ser alterada em produção!")
        
        logger.info("Modo de produção ativado")
    
    # ==================== UTILITÁRIOS ====================
    
    def get_system_info(self) -> Dict[str, Any]:
        """Retorna informações do sistema"""
        import platform
        import sys
        
        return {
            'version': self.VERSION,
            'python_version': sys.version,
            'platform': platform.platform(),
            'environment': self.ENVIRONMENT,
            'debug_mode': self.DEBUG,
            'config_validation': len(self.validate()) == 0
        }
    
    def print_config_summary(self):
        """Imprime resumo das configurações"""
        print("\n" + "="*60)
        print("BITCOIN TRADING SYSTEM - CONFIGURAÇÕES")
        print("="*60)
        print(f"Versão: {self.VERSION}")
        print(f"Ambiente: {self.ENVIRONMENT}")
        print(f"Debug: {self.DEBUG}")
        print(f"")
        print(f"🗄️  Banco de Dados: {self.database.path}")
        print(f"🌐 Web Server: {self.web.host}:{self.web.port}")
        print(f"📊 Streaming: {self.streaming.update_interval}s interval, {self.streaming.max_workers} workers")
        print(f"💰 Trading: {self.trading.default_stop_loss_pct}% SL, {self.trading.default_take_profit_pct}% TP")
        print(f"📝 Logs: {self.logging.level} level -> {self.logging.file_path}")
        print("")
        
        # Validação
        issues = self.validate()
        if issues:
            print("⚠️  AVISOS DE CONFIGURAÇÃO:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ Todas as configurações válidas")
        
        print("="*60 + "\n")
    
    def __str__(self) -> str:
        """Representação string da configuração"""
        return f"Config(version={self.VERSION}, env={self.ENVIRONMENT}, debug={self.DEBUG})"


# Instância global de configuração
_config = None

def get_config() -> Config:
    """
    Retorna instância global de configuração
    
    Returns:
        Instância do Config
    """
    global _config
    
    if _config is None:
        _config = Config()
    
    return _config


# Configuração para diferentes ambientes
def setup_environment(env: str = None):
    """
    Configura ambiente específico
    
    Args:
        env: Nome do ambiente (development, production, testing)
    """
    if env is None:
        env = os.getenv('ENVIRONMENT', 'development')
    
    config = get_config()
    
    if env.lower() == 'development':
        config.setup_development_mode()
    elif env.lower() == 'production':
        config.setup_production_mode()
    elif env.lower() == 'testing':
        # Configurações específicas para testes
        config.DEBUG = True
        config.database.path = ':memory:'  # Banco em memória para testes
        config.logging.level = 'WARNING'
        config.streaming.fallback_to_simulated = True
    
    logger.info(f"Ambiente configurado: {env}")


if __name__ == "__main__":
    # Script para testar configurações
    config = get_config()
    config.print_config_summary()
    
    # Salva configuração de exemplo
    config.save_to_file('config_example.json')