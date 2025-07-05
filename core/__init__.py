# core/__init__.py  
"""
Módulo core - Componentes principais do sistema
"""

from .trading_pair import TradingPair, PriceData, trading_pair_manager
from .data_streamer import multi_pair_streamer
from .database_manager import get_database_manager
from .system_manager import SystemManager, get_system_manager

__all__ = [
    'TradingPair',
    'PriceData', 
    'trading_pair_manager',
    'multi_pair_streamer',
    'get_database_manager',
    'SystemManager',
    'get_system_manager'
]