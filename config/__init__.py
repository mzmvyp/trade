# config/__init__.py
"""
Módulo de configuração
Centraliza todas as configurações do sistema
"""

from .settings import Config, get_config

# Import condicional para evitar erro circular
try:
    from core.trading_pair import trading_pair_manager
except ImportError:
    # Se não conseguir importar, será None temporariamente
    trading_pair_manager = None

__all__ = ['Config', 'get_config', 'trading_pair_manager']
