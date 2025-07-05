# api/__init__.py
"""
API módulo - Controllers, rotas e serviços
"""

from .controllers import (
    SystemController,
    PairsController,
    DashboardController, 
    TradingController,
    AnalyticsController
)

from .routes import register_all_routes

__all__ = [
    'SystemController',
    'PairsController',
    'DashboardController',
    'TradingController', 
    'AnalyticsController',
    'register_all_routes'
]