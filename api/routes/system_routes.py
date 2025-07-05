# api/routes/system_routes.py
from flask import jsonify
from ..controllers import SystemController

def register_system_routes(app, system_manager):
    """Registra rotas do sistema"""
    
    controller = SystemController(system_manager)
    
    @app.route('/api/system/status', methods=['GET'])
    def system_status():
        """Status do sistema"""
        response, status_code = controller.get_status()
        return jsonify(response), status_code
    
    @app.route('/api/system/stats', methods=['GET'])
    def system_stats():
        """Estatísticas do sistema"""
        response, status_code = controller.get_stats()
        return jsonify(response), status_code
    
    @app.route('/api/system/start', methods=['POST'])
    def start_system():
        """Inicia sistema"""
        response, status_code = controller.start_system()
        return jsonify(response), status_code
    
    @app.route('/api/system/stop', methods=['POST'])
    def stop_system():
        """Para sistema"""
        response, status_code = controller.stop_system()
        return jsonify(response), status_code
    
    @app.route('/api/system/restart', methods=['POST'])
    def restart_system():
        """Reinicia sistema"""
        response, status_code = controller.restart_system()
        return jsonify(response), status_code
    
    @app.route('/api/system/health', methods=['GET'])
    def health_check():
        """Health check"""
        response, status_code = controller.health_check()
        return jsonify(response), status_code
