# api/__init__.py
"""
API módulo - Controllers, rotas e serviços
"""

# Import dos controllers com try/except para evitar falhas
try:
    from .controllers.system_controller import SystemController
    from .controllers.pairs_controller import PairsController
    from .controllers.dashboard_controller import DashboardController
    from .controllers.trading_controller import TradingController
    from .controllers.analytics_controller import AnalyticsController
except ImportError as e:
    # Fallback em caso de import circular
    import logging
    logging.getLogger(__name__).warning(f"Import warning in api/__init__.py: {e}")
    
    # Define classes vazias como fallback
    class SystemController:
        def __init__(self, system_manager): pass
    class PairsController:
        def __init__(self, system_manager): pass
    class DashboardController:
        def __init__(self, system_manager): pass
    class TradingController:
        def __init__(self, system_manager): pass
    class AnalyticsController:
        def __init__(self, system_manager): pass

from .routes import register_all_routes

__all__ = [
    'SystemController',
    'PairsController',
    'DashboardController',
    'TradingController', 
    'AnalyticsController',
    'register_all_routes'
]
