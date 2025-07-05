# services/base_service.py
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseService:
    """Serviço base com funcionalidades comuns"""
    
    def __init__(self, system_manager):
        self.system_manager = system_manager
        self.logger = logger
    
    def log_operation(self, operation: str, details: str = None):
        """Log de operação do serviço"""
        log_msg = f"Service: {operation}"
        if details:
            log_msg += f" - {details}"
        self.logger.info(log_msg)
    
    def create_response(self, success: bool = True, data: Any = None, 
                       message: str = None, error: str = None) -> Dict[str, Any]:
        """Cria resposta padronizada"""
        response = {
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if success:
            if message:
                response['message'] = message
            if data is not None:
                response['data'] = data
        else:
            if error:
                response['error'] = error
            if data is not None:
                response['details'] = data
        
        return response
    
    def handle_exception(self, operation: str, exception: Exception) -> Dict[str, Any]:
        """Tratamento padrão de exceções"""
        self.logger.error(f"Erro em {operation}: {exception}")
        return self.create_response(
            success=False,
            error=f"Erro interno em {operation}",
            data={'exception_type': type(exception).__name__}
        )
