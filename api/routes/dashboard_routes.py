# api/routes/dashboard_routes.py
from flask import jsonify
from ..controllers import DashboardController

def register_dashboard_routes(app, system_manager):
    """Registra rotas do dashboard"""
    
    controller = DashboardController(system_manager)
    
    @app.route('/api/dashboard/data', methods=['GET'])
    def dashboard_data():
        """Dados completos do dashboard"""
        response, status_code = controller.get_dashboard_data()
        return jsonify(response), status_code
    
    @app.route('/api/dashboard/metrics', methods=['GET'])
    def dashboard_metrics():
        """Métricas do dashboard"""
        response, status_code = controller.get_dashboard_metrics()
        return jsonify(response), status_code
    
    @app.route('/api/dashboard/quick-stats', methods=['GET'])
    def quick_stats():
        """Estatísticas rápidas"""
        response, status_code = controller.get_quick_stats()
        return jsonify(response), status_code
