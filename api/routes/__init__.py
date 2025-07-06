# api/routes/__init__.py
"""
Módulo de rotas - Registra todas as rotas da aplicação
"""

from .system_routes import register_system_routes
from .pairs_routes import register_pairs_routes
from .dashboard_routes import register_dashboard_routes
from .trading_routes import register_trading_routes
from .analytics_routes import register_analytics_routes
from .web_routes import register_web_routes

def register_all_routes(app, system_manager):
    """Registra todas as rotas da aplicação"""
    
    # Rotas de API
    register_system_routes(app, system_manager)
    register_pairs_routes(app, system_manager)
    register_dashboard_routes(app, system_manager)
    register_trading_routes(app, system_manager)
    register_analytics_routes(app, system_manager)
    
    # Rotas web (páginas HTML)
    register_web_routes(app, system_manager)
    
    app.logger.info("✅ Todas as rotas registradas com sucesso")

__all__ = [
    'register_all_routes',
    'register_system_routes',
    'register_pairs_routes', 
    'register_dashboard_routes',
    'register_trading_routes',
    'register_analytics_routes',
    'register_web_routes'
]
