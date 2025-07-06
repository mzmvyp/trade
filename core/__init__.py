# core/__init__.py  
"""
Módulo core - Componentes principais do sistema
"""

# Imports condicionais para evitar circular imports
try:
    from .trading_pair import TradingPair, PriceData, trading_pair_manager
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Import warning trading_pair: {e}")
    TradingPair = None
    PriceData = None
    trading_pair_manager = None

try:
    from .data_streamer import multi_pair_streamer
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Import warning data_streamer: {e}")
    multi_pair_streamer = None

try:
    from .database_manager import get_database_manager
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Import warning database_manager: {e}")
    get_database_manager = None

try:
    from .system_manager import SystemManager, get_system_manager
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Import warning system_manager: {e}")
    SystemManager = None
    get_system_manager = None

__all__ = [
    'TradingPair',
    'PriceData', 
    'trading_pair_manager',
    'multi_pair_streamer',
    'get_database_manager',
    'SystemManager',
    'get_system_manager'
]
