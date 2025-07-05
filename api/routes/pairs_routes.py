# api/routes/pairs_routes.py
from flask import jsonify
from ..controllers import PairsController

def register_pairs_routes(app, system_manager):
    """Registra rotas de pares de trading"""
    
    controller = PairsController(system_manager)
    
    @app.route('/api/pairs/list', methods=['GET'])
    def list_pairs():
        """Lista todos os pares"""
        response, status_code = controller.list_pairs()
        return jsonify(response), status_code
    
    @app.route('/api/pairs/<symbol>/status', methods=['GET'])
    def get_pair_status(symbol):
        """Status de um par específico"""
        response, status_code = controller.get_pair_status(symbol)
        return jsonify(response), status_code
    
    @app.route('/api/pairs/<symbol>/start', methods=['POST'])
    def start_pair(symbol):
        """Inicia streaming para par específico"""
        response, status_code = controller.start_pair(symbol)
        return jsonify(response), status_code
    
    @app.route('/api/pairs/<symbol>/stop', methods=['POST'])
    def stop_pair(symbol):
        """Para streaming para par específico"""
        response, status_code = controller.stop_pair(symbol)
        return jsonify(response), status_code
    
    @app.route('/api/pairs/<symbol>/data', methods=['GET'])
    def get_pair_data(symbol):
        """Obtém dados recentes de um par"""
        response, status_code = controller.get_pair_data(symbol)
        return jsonify(response), status_code
    
    @app.route('/api/pairs/<symbol>/config', methods=['PUT'])
    def update_pair_config(symbol):
        """Atualiza configuração do par"""
        response, status_code = controller.update_pair_config(symbol)
        return jsonify(response), status_code
