# api/controllers/system_controller.py - Atualizado
from .base_controller import BaseController
from services import SystemService

class SystemController(BaseController):
    """Controller para operações do sistema - usando services"""
    
    def __init__(self, system_manager):
        super().__init__(system_manager)
        self.service = SystemService(system_manager)
    
    def get_status(self):
        """GET /api/system/status"""
        result = self.service.get_system_status()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_stats(self):
        """GET /api/system/stats"""
        result = self.service.get_system_stats()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def start_system(self):
        """POST /api/system/start"""
        result = self.service.start_system()
        
        if result['success']:
            return self.success_response(result['data'], result.get('message'))
        else:
            return self.error_response(result['error'], 400)
    
    def stop_system(self):
        """POST /api/system/stop"""
        result = self.service.stop_system()
        
        if result['success']:
            return self.success_response(result['data'], result.get('message'))
        else:
            return self.error_response(result['error'], 400)
    
    def restart_system(self):
        """POST /api/system/restart"""
        result = self.service.restart_system()
        
        if result['success']:
            return self.success_response(result['data'], result.get('message'))
        else:
            return self.error_response(result['error'], 400)
    
    def health_check(self):
        """GET /api/system/health"""
        result = self.service.health_check()
        
        if result['success']:
            return self.success_response(result['data'], result.get('message'))
        else:
            return self.error_response(result['error'], 503, result.get('data'))

# api/controllers/pairs_controller.py - Atualizado
from .base_controller import BaseController
from services import PairsService

class PairsController(BaseController):
    """Controller para operações com pares - usando services"""
    
    def __init__(self, system_manager):
        super().__init__(system_manager)
        self.service = PairsService(system_manager)
    
    def list_pairs(self):
        """GET /api/pairs/list"""
        result = self.service.list_all_pairs()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_enabled_pairs(self):
        """GET /api/pairs/enabled"""
        result = self.service.get_enabled_pairs()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_pair_status(self, symbol: str):
        """GET /api/pairs/<symbol>/status"""
        result = self.service.get_pair_status(symbol)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 404 if 'não encontrado' in result['error'] else 500)
    
    def start_pair(self, symbol: str):
        """POST /api/pairs/<symbol>/start"""
        result = self.service.start_pair_streaming(symbol)
        
        if result['success']:
            return self.success_response(result['data'], result.get('message'))
        else:
            return self.error_response(result['error'], 400)
    
    def stop_pair(self, symbol: str):
        """POST /api/pairs/<symbol>/stop"""
        result = self.service.stop_pair_streaming(symbol)
        
        if result['success']:
            return self.success_response(result['data'], result.get('message'))
        else:
            return self.error_response(result['error'], 400)
    
    def get_pair_data(self, symbol: str):
        """GET /api/pairs/<symbol>/data"""
        limit = self.get_query_param('limit', 50, int)
        result = self.service.get_pair_data(symbol, limit)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def update_pair_config(self, symbol: str):
        """PUT /api/pairs/<symbol>/config"""
        data = self.validate_json()
        if not data:
            return self.error_response("JSON inválido", 400)
        
        result = self.service.update_pair_configuration(symbol, data)
        
        if result['success']:
            return self.success_response(None, result.get('message'))
        else:
            return self.error_response(result['error'], 500)
    
    def get_pairs_summary(self):
        """GET /api/pairs/summary"""
        result = self.service.get_pairs_summary()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)

# api/controllers/dashboard_controller.py - Atualizado
from .base_controller import BaseController
from services import DashboardService

class DashboardController(BaseController):
    """Controller para dados do dashboard - usando services"""
    
    def __init__(self, system_manager):
        super().__init__(system_manager)
        self.service = DashboardService(system_manager)
    
    def get_dashboard_data(self):
        """GET /api/dashboard/data"""
        result = self.service.get_dashboard_overview()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_dashboard_metrics(self):
        """GET /api/dashboard/metrics"""
        result = self.service.get_dashboard_metrics()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_quick_stats(self):
        """GET /api/dashboard/quick-stats"""
        result = self.service.get_quick_statistics()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_real_time_data(self):
        """GET /api/dashboard/realtime"""
        result = self.service.get_real_time_data()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)

# api/controllers/trading_controller.py - Atualizado
from .base_controller import BaseController
from services import TradingService

class TradingController(BaseController):
    """Controller para operações de trading - usando services"""
    
    def __init__(self, system_manager):
        super().__init__(system_manager)
        self.service = TradingService(system_manager)
    
    def get_signals(self):
        """GET /api/trading/signals"""
        limit = self.get_query_param('limit', 50, int)
        status = self.get_query_param('status', None, str)
        
        result = self.service.get_trading_signals(limit, status)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_indicators(self):
        """GET /api/trading/indicators"""
        symbol = self.get_query_param('symbol', None, str)
        
        result = self.service.get_technical_indicators(symbol)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_pattern_stats(self):
        """GET /api/trading/pattern-stats"""
        result = self.service.get_pattern_statistics()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def create_manual_signal(self):
        """POST /api/trading/signals"""
        data = self.validate_json(['pair_symbol', 'signal_type', 'entry_price', 'target_price', 'stop_loss'])
        if not data:
            return self.error_response("Dados inválidos para criação de sinal", 400)
        
        result = self.service.create_manual_signal(data)
        
        if result['success']:
            return self.success_response(result.get('data'), result.get('message'))
        else:
            return self.error_response(result['error'], 400)
    
    def close_signal(self, signal_id: str):
        """POST /api/trading/signals/<signal_id>/close"""
        data = self.validate_json()
        reason = data.get('reason', 'Manual') if data else 'Manual'
        
        result = self.service.close_signal(signal_id, reason)
        
        if result['success']:
            return self.success_response(None, result.get('message'))
        else:
            return self.error_response(result['error'], 500)
    
    def get_trading_summary(self):
        """GET /api/trading/summary"""
        result = self.service.get_trading_summary()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_risk_metrics(self):
        """GET /api/trading/risk"""
        result = self.service.get_risk_metrics()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)

# api/controllers/analytics_controller.py - Atualizado
from .base_controller import BaseController
from services import AnalyticsService

class AnalyticsController(BaseController):
    """Controller para analytics e relatórios - usando services"""
    
    def __init__(self, system_manager):
        super().__init__(system_manager)
        self.service = AnalyticsService(system_manager)
    
    def get_performance_summary(self):
        """GET /api/analytics/performance"""
        period = self.get_query_param('period', '24h', str)
        
        result = self.service.get_performance_summary(period)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_pair_analytics(self, symbol: str):
        """GET /api/analytics/pairs/<symbol>"""
        days = self.get_query_param('days', 7, int)
        
        result = self.service.get_pair_analytics(symbol, days)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 404 if 'não encontrado' in result['error'] else 500)
    
    def get_market_overview(self):
        """GET /api/analytics/market"""
        result = self.service.get_market_overview()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def export_data(self):
        """GET /api/analytics/export"""
        format_type = self.get_query_param('format', 'json', str)
        start_date = self.get_query_param('start_date', None, str)
        end_date = self.get_query_param('end_date', None, str)
        
        result = self.service.export_trading_data(format_type, start_date, end_date)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 400)
    
    def get_backtesting_results(self):
        """GET /api/analytics/backtest"""
        strategy = self.get_query_param('strategy', 'default', str)
        period = self.get_query_param('period', '30d', str)
        
        result = self.service.get_backtesting_results(strategy, period)
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def generate_report(self):
        """POST /api/analytics/reports"""
        data = self.validate_json(['report_type'])
        if not data:
            return self.error_response("Tipo de relatório obrigatório", 400)
        
        result = self.service.generate_report(data['report_type'], data.get('params', {}))
        
        if result['success']:
            return self.success_response(result['data'], result.get('message'))
        else:
            return self.error_response(result['error'], 500)
    
    def get_portfolio_analysis(self):
        """GET /api/analytics/portfolio"""
        result = self.service.get_portfolio_analysis()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)