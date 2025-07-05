# api/controllers/__init__.py
"""
Controllers do sistema de trading
Separa a lógica de controle das rotas
"""

from .system_controller import SystemController
from .pairs_controller import PairsController
from .dashboard_controller import DashboardController
from .trading_controller import TradingController
from .analytics_controller import AnalyticsController

__all__ = [
    'SystemController',
    'PairsController', 
    'DashboardController',
    'TradingController',
    'AnalyticsController'
]