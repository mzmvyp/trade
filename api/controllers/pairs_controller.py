# api/controllers/pairs_controller.py
from .base_controller import BaseController

class PairsController(BaseController):
    """Controller para operações com pares de trading"""
    
    def list_pairs(self):
        """GET /api/pairs/list"""
        try:
            pairs_data = self.system_manager.get_pairs_list()
            return self.success_response(pairs_data)
            
        except Exception as e:
            self.logger.error(f"Erro ao listar pares: {e}")
            return self.error_response("Erro ao listar pares", 500)
    
    def get_pair_status(self, symbol: str):
        """GET /api/pairs/<symbol>/status"""
        try:
            pair = self.system_manager.pair_manager.get_pair(symbol)
            if not pair:
                return self.error_response(f"Par {symbol} não encontrado", 404)
            
            status = pair.get_status()
            return self.success_response(status)
            
        except Exception as e:
            self.logger.error(f"Erro ao obter status do par {symbol}: {e}")
            return self.error_response("Erro ao obter status do par", 500)
    
    def start_pair(self, symbol: str):
        """POST /api/pairs/<symbol>/start"""
        try:
            self.log_action(f"Iniciando par {symbol}")
            result = self.system_manager.start_pair(symbol)
            
            if result['success']:
                return self.success_response(result, result['message'])
            else:
                return self.error_response(result['message'], 400)
                
        except Exception as e:
            self.logger.error(f"Erro ao iniciar par {symbol}: {e}")
            return self.error_response("Erro ao iniciar par", 500)
    
    def stop_pair(self, symbol: str):
        """POST /api/pairs/<symbol>/stop"""
        try:
            self.log_action(f"Parando par {symbol}")
            result = self.system_manager.stop_pair(symbol)
            
            if result['success']:
                return self.success_response(result, result['message'])
            else:
                return self.error_response(result['message'], 400)
                
        except Exception as e:
            self.logger.error(f"Erro ao parar par {symbol}: {e}")
            return self.error_response("Erro ao parar par", 500)
    
    def get_pair_data(self, symbol: str):
        """GET /api/pairs/<symbol>/data"""
        try:
            limit = self.get_query_param('limit', 50, int)
            limit = min(max(limit, 1), 1000)  # Entre 1 e 1000
            
            data = self.system_manager.get_pair_data(symbol, limit)
            
            if 'error' in data:
                return self.error_response(data['error'], 500)
            
            return self.success_response(data)
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados do par {symbol}: {e}")
            return self.error_response("Erro ao obter dados do par", 500)
    
    def update_pair_config(self, symbol: str):
        """PUT /api/pairs/<symbol>/config"""
        try:
            data = self.validate_json()
            if not data:
                return self.error_response("JSON inválido", 400)
            
            # TODO: Implementar atualização de configuração do par
            self.log_action(f"Atualizando configuração do par {symbol}")
            
            return self.success_response(None, "Configuração atualizada com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar configuração do par {symbol}: {e}")
            return self.error_response("Erro ao atualizar configuração", 500)
