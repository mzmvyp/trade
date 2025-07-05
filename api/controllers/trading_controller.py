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
