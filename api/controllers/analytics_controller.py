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