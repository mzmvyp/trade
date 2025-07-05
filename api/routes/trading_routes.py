# api/routes/trading_routes.py
from flask import jsonify
from ..controllers import TradingController

def register_trading_routes(app, system_manager):
    """Registra rotas de trading"""
    
    controller = TradingController(system_manager)
    
    @app.route('/api/trading/signals', methods=['GET'])
    def get_trading_signals():
        """Obtém sinais de trading"""
        response, status_code = controller.get_signals()
        return jsonify(response), status_code
    
    @app.route('/api/trading/signals', methods=['POST'])
    def create_manual_signal():
        """Cria sinal manual"""
        response, status_code = controller.create_manual_signal()
        return jsonify(response), status_code
    
    @app.route('/api/trading/signals/<signal_id>/close', methods=['POST'])
    def close_signal(signal_id):
        """Fecha sinal específico"""
        response, status_code = controller.close_signal(signal_id)
        return jsonify(response), status_code
    
    @app.route('/api/trading/indicators', methods=['GET'])
    def get_trading_indicators():
        """Obtém indicadores técnicos"""
        response, status_code = controller.get_indicators()
        return jsonify(response), status_code
    
    @app.route('/api/trading/pattern-stats', methods=['GET'])
    def get_pattern_stats():
        """Obtém estatísticas de padrões"""
        response, status_code = controller.get_pattern_stats()
        return jsonify(response), status_code
