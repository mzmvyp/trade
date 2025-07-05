# services/system_service.py
from .base_service import BaseService
from typing import Dict, Any

class SystemService(BaseService):
    """Serviço para operações do sistema"""
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtém status completo do sistema"""
        try:
            status = self.system_manager.get_status()
            return self.create_response(data=status)
        except Exception as e:
            return self.handle_exception("get_system_status", e)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do sistema"""
        try:
            stats = self.system_manager.get_stats()
            return self.create_response(data=stats)
        except Exception as e:
            return self.handle_exception("get_system_stats", e)
    
    def start_system(self) -> Dict[str, Any]:
        """Inicia o sistema"""
        try:
            self.log_operation("Iniciando sistema")
            result = self.system_manager.start()
            
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
            return self.handle_exception("start_system", e)
    
    def stop_system(self) -> Dict[str, Any]:
        """Para o sistema"""
        try:
            self.log_operation("Parando sistema")
            result = self.system_manager.stop()
            
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
            return self.handle_exception("stop_system", e)
    
    def restart_system(self) -> Dict[str, Any]:
        """Reinicia o sistema"""
        try:
            self.log_operation("Reiniciando sistema")
            result = self.system_manager.restart()
            
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
            return self.handle_exception("restart_system", e)
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do sistema"""
        try:
            health = self.system_manager.health_check()
            
            success = health['status'] in ['healthy', 'degraded']
            return self.create_response(
                success=success,
                data=health,
                message="Sistema saudável" if success else "Sistema com problemas"
            )
        except Exception as e:
            return self.handle_exception("health_check", e)
