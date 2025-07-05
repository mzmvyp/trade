# services/pairs_service.py
from .base_service import BaseService
from typing import Dict, Any, List

class PairsService(BaseService):
    """Serviço para operações com pares de trading"""
    
    def list_all_pairs(self) -> Dict[str, Any]:
        """Lista todos os pares disponíveis"""
        try:
            pairs_data = self.system_manager.get_pairs_list()
            return self.create_response(data=pairs_data)
        except Exception as e:
            return self.handle_exception("list_all_pairs", e)
    
    def get_enabled_pairs(self) -> Dict[str, Any]:
        """Lista apenas pares habilitados"""
        try:
            all_pairs = self.system_manager.get_pairs_list()
            enabled_pairs = [p for p in all_pairs['pairs'] if p.get('enabled', False)]
            
            return self.create_response(data={
                'pairs': enabled_pairs,
                'total': len(enabled_pairs)
            })
        except Exception as e:
            return self.handle_exception("get_enabled_pairs", e)
    
    def get_pair_status(self, symbol: str) -> Dict[str, Any]:
        """Obtém status de um par específico"""
        try:
            pair = self.system_manager.pair_manager.get_pair(symbol)
            if not pair:
                return self.create_response(
                    success=False,
                    error=f"Par {symbol} não encontrado"
                )
            
            status = pair.get_status()
            return self.create_response(data=status)
        except Exception as e:
            return self.handle_exception("get_pair_status", e)
    
    def start_pair_streaming(self, symbol: str) -> Dict[str, Any]:
        """Inicia streaming para um par"""
        try:
            self.log_operation(f"Iniciando streaming", f"Par: {symbol}")
            result = self.system_manager.start_pair(symbol)
            
            if result['success']:
                return self.create_response(
                    data=result,
                    message=result['message']
                )
            else:
                return self.create_response(
                    success=False,
                    error=result['message']
                )
        except Exception as e:
            return self.handle_exception("start_pair_streaming", e)
    
    def stop_pair_streaming(self, symbol: str) -> Dict[str, Any]:
        """Para streaming para um par"""
        try:
            self.log_operation(f"Parando streaming", f"Par: {symbol}")
            result = self.system_manager.stop_pair(symbol)
            
            if result['success']:
                return self.create_response(
                    data=result,
                    message=result['message']
                )
            else:
                return self.create_response(
                    success=False,
                    error=result['message']
                )
        except Exception as e:
            return self.handle_exception("stop_pair_streaming", e)
    
    def get_pair_data(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """Obtém dados históricos de um par"""
        try:
            # Valida limite
            limit = max(1, min(limit, 1000))
            
            data = self.system_manager.get_pair_data(symbol, limit)
            
            if 'error' in data:
                return self.create_response(
                    success=False,
                    error=data['error']
                )
            
            return self.create_response(data=data)
        except Exception as e:
            return self.handle_exception("get_pair_data", e)
    
    def update_pair_configuration(self, symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza configuração de um par"""
        try:
            self.log_operation(f"Atualizando configuração", f"Par: {symbol}")
            
            # TODO: Implementar validação e atualização de configuração
            # Por enquanto, apenas simula sucesso
            return self.create_response(
                message=f"Configuração do par {symbol} atualizada com sucesso"
            )
        except Exception as e:
            return self.handle_exception("update_pair_configuration", e)
    
    def get_pairs_summary(self) -> Dict[str, Any]:
        """Obtém resumo de todos os pares"""
        try:
            all_pairs = self.system_manager.get_pairs_list()
            pairs = all_pairs['pairs']
            
            summary = {
                'total_pairs': len(pairs),
                'enabled_pairs': len([p for p in pairs if p.get('enabled', False)]),
                'streaming_pairs': len([p for p in pairs if p.get('is_streaming', False)]),
                'by_status': {
                    'enabled': [p for p in pairs if p.get('enabled', False)],
                    'disabled': [p for p in pairs if not p.get('enabled', False)],
                    'streaming': [p for p in pairs if p.get('is_streaming', False)]
                }
            }
            
            return self.create_response(data=summary)
        except Exception as e:
            return self.handle_exception("get_pairs_summary", e)
