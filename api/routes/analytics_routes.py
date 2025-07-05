# api/routes/analytics_routes.py
from flask import jsonify
from ..controllers import AnalyticsController

def register_analytics_routes(app, system_manager):
    """Registra rotas de analytics"""
    
    controller = AnalyticsController(system_manager)
    
    @app.route('/api/analytics/performance', methods=['GET'])
    def get_performance_summary():
        """Resumo de performance"""
        response, status_code = controller.get_performance_summary()
        return jsonify(response), status_code
    
    @app.route('/api/analytics/pairs/<symbol>', methods=['GET'])
    def get_pair_analytics(symbol):
        """Analytics específico de um par"""
        response, status_code = controller.get_pair_analytics(symbol)
        return jsonify(response), status_code
    
    @app.route('/api/analytics/market', methods=['GET'])
    def get_market_overview():
        """Overview de mercado"""
        response, status_code = controller.get_market_overview()
        return jsonify(response), status_code
    
    @app.route('/api/analytics/export', methods=['GET'])
    def export_analytics_data():
        """Exporta dados de analytics"""
        response, status_code = controller.export_data()
        return jsonify(response), status_code
