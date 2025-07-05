# config/__init__.py
"""
Módulo de configuração
Centraliza todas as configurações do sistema
"""

from .settings import Config, get_config
from .trading_pairs import trading_pair_manager

__all__ = ['Config', 'get_config', 'trading_pair_manager']
