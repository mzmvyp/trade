# utils/logging_config.py - Configuração de Logging (CORRIGIDO)
import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_enabled: bool = True,
    file_enabled: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Configura sistema de logging do projeto
    
    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Caminho do arquivo de log (opcional)
        max_file_size: Tamanho máximo do arquivo em bytes
        backup_count: Número de arquivos de backup
        console_enabled: Se deve logar no console
        file_enabled: Se deve logar em arquivo
        format_string: Formato personalizado de log
        
    Returns:
        Logger configurado
    """
    
    # Remove handlers existentes para reconfiguração
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configura nível
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Formato padrão
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(
        format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para console
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Handler para arquivo
    if file_enabled:
        if log_file is None:
            # Cria diretório de logs se não existir
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "trading_system.log"
        
        # Cria diretório do arquivo se não existir
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handler rotativo
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Logger principal
    logger = logging.getLogger("trading_system")
    
    # Log inicial
    logger.info("="*60)
    logger.info("BITCOIN TRADING SYSTEM - LOGGING INICIADO")
    logger.info(f"Nível de log: {level}")
    logger.info(f"Console: {'Habilitado' if console_enabled else 'Desabilitado'}")
    logger.info(f"Arquivo: {'Habilitado' if file_enabled else 'Desabilitado'}")
    if file_enabled and log_file:
        logger.info(f"Arquivo de log: {log_file}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("="*60)
    
    return logger


def setup_component_loggers():
    """Configura loggers específicos para cada componente"""
    
    # Loggers dos componentes principais
    components = [
        "trading_system.core",
        "trading_system.api",
        "trading_system.services",
        "trading_system.web",
        "trading_system.config",
        "trading_system.utils"
    ]
    
    for component in components:
        logger = logging.getLogger(component)
        logger.info(f"Logger configurado: {component}")


def setup_external_loggers():
    """Configura loggers de bibliotecas externas"""
    
    # Reduz verbosidade de bibliotecas externas
    external_loggers = {
        'requests': logging.WARNING,
        'urllib3': logging.WARNING,
        'requests.packages.urllib3': logging.WARNING,
        'websocket': logging.WARNING,
        'asyncio': logging.WARNING
    }
    
    for logger_name, level in external_loggers.items():
        logging.getLogger(logger_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    Obtém logger com nome específico
    
    Args:
        name: Nome do logger
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(f"trading_system.{name}")


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para console"""
    
    # Códigos de cores ANSI
    COLORS = {
        'DEBUG': '\033[36m',    # Ciano
        'INFO': '\033[32m',     # Verde
        'WARNING': '\033[33m',  # Amarelo
        'ERROR': '\033[31m',    # Vermelho
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Adiciona cor baseada no nível
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Aplica cor apenas ao nível
        original_levelname = record.levelname
        record.levelname = f"{level_color}{record.levelname}{reset_color}"
        
        # Formata mensagem
        formatted = super().format(record)
        
        # Restaura levelname original
        record.levelname = original_levelname
        
        return formatted


def setup_colored_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console_colors: bool = True
) -> logging.Logger:
    """
    Configura logging com cores no console
    
    Args:
        level: Nível de log
        log_file: Arquivo de log (opcional)
        console_colors: Se deve usar cores no console
        
    Returns:
        Logger configurado
    """
    
    # Remove handlers existentes
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configura nível
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Formatter para console (com cores)
    if console_colors and sys.stdout.isatty():  # Terminal suporta cores
        console_formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt='%H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt='%H:%M:%S'
        )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Formatter para arquivo (sem cores)
    if log_file:
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Cria diretório se necessário
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handler para arquivo
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return logging.getLogger("trading_system")


class DatabaseLogHandler(logging.Handler):
    """Handler personalizado para salvar logs no banco de dados"""
    
    def __init__(self, database_manager=None):
        """
        Inicializa handler de banco
        
        Args:
            database_manager: Instância do DatabaseManager
        """
        super().__init__()
        self.database_manager = database_manager
        self.buffer = []
        self.buffer_size = 100
    
    def emit(self, record):
        """Processa record de log"""
        try:
            # Adiciona ao buffer
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created),
                'level': record.levelname,
                'component': record.name,
                'message': record.getMessage(),
                'details': {
                    'filename': record.filename,
                    'lineno': record.lineno,
                    'funcName': record.funcName
                }
            }
            
            if record.exc_info:
                log_entry['details']['exception'] = self.format(record)
            
            self.buffer.append(log_entry)
            
            # Flush buffer se necessário
            if len(self.buffer) >= self.buffer_size:
                self.flush()
                
        except Exception:
            self.handleError(record)
    
    def flush(self):
        """Envia logs do buffer para o banco"""
        if not self.buffer or not self.database_manager:
            return
        
        try:
            for log_entry in self.buffer:
                self.database_manager.save_system_log(
                    level=log_entry['level'],
                    component=log_entry['component'],
                    message=log_entry['message'],
                    details=log_entry['details']
                )
            
            self.buffer.clear()
            
        except Exception as e:
            # Evita logging recursivo
            print(f"Erro ao salvar logs no banco: {e}")
    
    def close(self):
        """Finaliza handler"""
        self.flush()
        super().close()


def setup_database_logging(database_manager, level: str = "INFO"):
    """
    Adiciona handler de banco de dados ao logging
    
    Args:
        database_manager: Instância do DatabaseManager
        level: Nível mínimo para salvar no banco
    """
    
    # Cria handler de banco
    db_handler = DatabaseLogHandler(database_manager)
    db_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Formato simples para banco
    formatter = logging.Formatter("%(message)s")
    db_handler.setFormatter(formatter)
    
    # Adiciona ao root logger
    logging.getLogger().addHandler(db_handler)
    
    logger = logging.getLogger("trading_system")
    logger.info("Handler de banco de dados adicionado ao logging")


def create_performance_logger() -> logging.Logger:
    """
    Cria logger específico para métricas de performance
    
    Returns:
        Logger de performance
    """
    perf_logger = logging.getLogger("trading_system.performance")
    
    # Handler específico para performance
    perf_file = Path("logs") / "performance.log"
    perf_file.parent.mkdir(exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        perf_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    
    # Formato específico para métricas
    formatter = logging.Formatter(
        "%(asctime)s,%(message)s",  # CSV-like format
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    perf_logger.addHandler(handler)
    perf_logger.setLevel(logging.INFO)
    
    # Evita propagação para root logger
    perf_logger.propagate = False
    
    return perf_logger


def create_audit_logger() -> logging.Logger:
    """
    Cria logger específico para auditoria
    
    Returns:
        Logger de auditoria
    """
    audit_logger = logging.getLogger("trading_system.audit")
    
    # Handler específico para auditoria
    audit_file = Path("logs") / "audit.log"
    audit_file.parent.mkdir(exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        audit_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10,  # Mais backups para auditoria
        encoding='utf-8'
    )
    
    # Formato detalhado para auditoria
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    
    # Evita propagação para root logger
    audit_logger.propagate = False
    
    return audit_logger


def get_system_memory_usage():
    """
    Obtém uso de memória do sistema (com fallback se psutil não disponível)
    
    Returns:
        Dict com informações de memória ou None se não disponível
    """
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'memory_rss_mb': memory_info.rss / (1024 * 1024),
            'memory_vms_mb': memory_info.vms / (1024 * 1024),
            'cpu_percent': process.cpu_percent(),
            'threads_count': process.num_threads(),
            'psutil_available': True
        }
        
    except ImportError:
        # psutil não está disponível
        return {
            'psutil_available': False,
            'message': 'psutil não instalado - estatísticas de memória indisponíveis'
        }
    except Exception as e:
        return {
            'psutil_available': False,
            'error': str(e)
        }


# Configuração padrão para desenvolvimento
def setup_development_logging():
    """Configura logging para ambiente de desenvolvimento"""
    return setup_colored_logging(
        level="DEBUG",
        log_file="logs/development.log",
        console_colors=True
    )


# Configuração padrão para produção
def setup_production_logging():
    """Configura logging para ambiente de produção"""
    return setup_logging(
        level="INFO",
        log_file="logs/production.log",
        console_enabled=True,
        file_enabled=True
    )