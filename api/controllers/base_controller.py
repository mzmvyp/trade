# api/controllers/base_controller.py - Controlador Base Corrigido
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union
from flask import request

logger = logging.getLogger(__name__)

class BaseController:
    """
    Controlador base com funcionalidades comuns
    Fornece métodos utilitários para todos os controllers
    """
    
    def __init__(self, system_manager):
        """
        Inicializa o controlador base
        
        Args:
            system_manager: Instância do SystemManager
        """
        self.system_manager = system_manager
        self.logger = logger
    
    # ==================== RESPONSE HELPERS ====================
    
    def success_response(self, data: Any = None, message: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Cria resposta de sucesso padronizada
        
        Args:
            data: Dados a serem retornados
            message: Mensagem opcional de sucesso
            
        Returns:
            Tuple contendo (response_dict, status_code)
        """
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
        if message:
            response['message'] = message
        
        if data is not None:
            response['data'] = data
        
        return response, 200
    
    def error_response(self, error: str, status_code: int = 400, 
                      details: Any = None) -> Tuple[Dict[str, Any], int]:
        """
        Cria resposta de erro padronizada
        
        Args:
            error: Mensagem de erro
            status_code: Código de status HTTP
            details: Detalhes adicionais do erro
            
        Returns:
            Tuple contendo (response_dict, status_code)
        """
        response = {
            'success': False,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        if details is not None:
            response['details'] = details
        
        return response, status_code
    
    # ==================== REQUEST HELPERS ====================
    
    def get_query_param(self, param_name: str, default: Any = None, 
                       param_type: type = str) -> Any:
        """
        Obtém parâmetro de query string com tipo e valor padrão
        
        Args:
            param_name: Nome do parâmetro
            default: Valor padrão se não encontrado
            param_type: Tipo esperado do parâmetro
            
        Returns:
            Valor convertido ou valor padrão
        """
        try:
            value = request.args.get(param_name)
            
            if value is None:
                return default
            
            # Conversão de tipo
            if param_type == int:
                return int(value)
            elif param_type == float:
                return float(value)
            elif param_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            else:
                return str(value)
                
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Erro ao converter parâmetro {param_name}: {e}")
            return default
    
    def validate_json(self, required_fields: Optional[list] = None) -> Optional[Dict[str, Any]]:
        """
        Valida e retorna dados JSON da requisição
        
        Args:
            required_fields: Lista de campos obrigatórios
            
        Returns:
            Dados JSON validados ou None se inválido
        """
        try:
            if not request.is_json:
                self.logger.warning("Requisição não contém JSON válido")
                return None
            
            data = request.get_json()
            
            if data is None:
                self.logger.warning("Falha ao decodificar JSON")
                return None
            
            # Valida campos obrigatórios
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.logger.warning(f"Campos obrigatórios ausentes: {missing_fields}")
                    return None
            
            return data
            
        except Exception as e:
            self.logger.error(f"Erro ao validar JSON: {e}")
            return None
    
    def get_request_info(self) -> Dict[str, Any]:
        """
        Obtém informações detalhadas da requisição
        
        Returns:
            Dicionário com informações da requisição
        """
        return {
            'method': request.method,
            'path': request.path,
            'url': request.url,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_type': request.headers.get('Content-Type', ''),
            'content_length': request.headers.get('Content-Length', '0'),
            'timestamp': datetime.now().isoformat()
        }
    
    # ==================== VALIDATION HELPERS ====================
    
    def validate_number_range(self, value: Union[int, float], min_val: Optional[float] = None, 
                             max_val: Optional[float] = None) -> bool:
        """
        Valida se número está dentro de um range
        
        Args:
            value: Valor a ser validado
            min_val: Valor mínimo
            max_val: Valor máximo
            
        Returns:
            True se válido, False caso contrário
        """
        try:
            num_value = float(value)
            
            if min_val is not None and num_value < min_val:
                return False
            
            if max_val is not None and num_value > max_val:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Valida se símbolo de par existe
        
        Args:
            symbol: Símbolo do par de trading
            
        Returns:
            True se válido, False caso contrário
        """
        if not symbol or not isinstance(symbol, str):
            return False
        
        # Verifica se par existe no sistema
        pair = self.system_manager.pair_manager.get_pair(symbol.upper())
        return pair is not None
    
    def validate_date_range(self, start_date: str, end_date: str) -> bool:
        """
        Valida range de datas
        
        Args:
            start_date: Data de início (ISO format)
            end_date: Data de fim (ISO format)
            
        Returns:
            True se válido, False caso contrário
        """
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            return start <= end
            
        except (ValueError, TypeError):
            return False
    
    # ==================== LOGGING HELPERS ====================
    
    def log_action(self, action: str, details: str = None, level: str = 'info'):
        """
        Log padronizado de ações do controller
        
        Args:
            action: Ação sendo executada
            details: Detalhes adicionais
            level: Nível de log (debug, info, warning, error)
        """
        log_msg = f"Controller Action: {action}"
        
        if details:
            log_msg += f" - {details}"
        
        # Adiciona informações da requisição
        req_info = f" [{request.method} {request.path}]"
        log_msg += req_info
        
        # Log no nível apropriado
        if level == 'debug':
            self.logger.debug(log_msg)
        elif level == 'warning':
            self.logger.warning(log_msg)
        elif level == 'error':
            self.logger.error(log_msg)
        else:
            self.logger.info(log_msg)
    
    def log_request_summary(self):
        """Log resumido da requisição para debug"""
        req_info = self.get_request_info()
        self.logger.debug(f"Request: {req_info['method']} {req_info['path']} from {req_info['remote_addr']}")
    
    # ==================== UTILITY METHODS ====================
    
    def format_response_data(self, data: Any) -> Any:
        """
        Formata dados para resposta JSON
        
        Args:
            data: Dados a serem formatados
            
        Returns:
            Dados formatados para JSON
        """
        if data is None:
            return None
        
        # Se for lista, formata cada item
        if isinstance(data, list):
            return [self.format_response_data(item) for item in data]
        
        # Se for dict, formata valores
        if isinstance(data, dict):
            return {key: self.format_response_data(value) for key, value in data.items()}
        
        # Se for datetime, converte para ISO string
        if isinstance(data, datetime):
            return data.isoformat()
        
        # Outros tipos retornam como estão
        return data
    
    def sanitize_input(self, input_data: Any) -> Any:
        """
        Sanitiza dados de entrada
        
        Args:
            input_data: Dados a serem sanitizados
            
        Returns:
            Dados sanitizados
        """
        if isinstance(input_data, str):
            # Remove caracteres perigosos
            return input_data.strip()
        
        if isinstance(input_data, dict):
            return {key: self.sanitize_input(value) for key, value in input_data.items()}
        
        if isinstance(input_data, list):
            return [self.sanitize_input(item) for item in input_data]
        
        return input_data
    
    def handle_controller_exception(self, operation: str, exception: Exception) -> Tuple[Dict[str, Any], int]:
        """
        Tratamento padrão de exceções em controllers
        
        Args:
            operation: Nome da operação que falhou
            exception: Exceção capturada
            
        Returns:
            Response de erro padronizada
        """
        error_msg = f"Erro interno em {operation}"
        
        # Log detalhado do erro
        self.logger.error(f"{error_msg}: {exception}", exc_info=True)
        
        # Em desenvolvimento, inclui detalhes do erro
        details = None
        if self.system_manager.config.DEBUG:
            details = {
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'operation': operation
            }
        
        return self.error_response(error_msg, 500, details)
    
    # ==================== PERMISSION HELPERS ====================
    
    def check_system_permissions(self, action: str) -> bool:
        """
        Verifica permissões para ações do sistema
        
        Args:
            action: Ação a ser verificada (start, stop, restart, etc.)
            
        Returns:
            True se permitido, False caso contrário
        """
        # TODO: Implementar sistema de permissões quando necessário
        # Por enquanto, todas as ações são permitidas
        return True
    
    def require_system_permission(self, action: str) -> Optional[Tuple[Dict[str, Any], int]]:
        """
        Verifica permissão e retorna erro se não autorizado
        
        Args:
            action: Ação a ser verificada
            
        Returns:
            Response de erro se não autorizado, None se autorizado
        """
        if not self.check_system_permissions(action):
            return self.error_response(f"Não autorizado para ação: {action}", 403)
        
        return None
    
    # ==================== PAGINATION HELPERS ====================
    
    def get_pagination_params(self, default_limit: int = 50, max_limit: int = 1000) -> Dict[str, int]:
        """
        Obtém parâmetros de paginação
        
        Args:
            default_limit: Limite padrão de itens
            max_limit: Limite máximo de itens
            
        Returns:
            Dicionário com parâmetros de paginação
        """
        page = self.get_query_param('page', 1, int)
        limit = self.get_query_param('limit', default_limit, int)
        offset = self.get_query_param('offset', 0, int)
        
        # Validações
        page = max(1, page)
        limit = max(1, min(limit, max_limit))
        offset = max(0, offset)
        
        # Calcula offset baseado na página se não fornecido explicitamente
        if offset == 0 and page > 1:
            offset = (page - 1) * limit
        
        return {
            'page': page,
            'limit': limit,
            'offset': offset
        }
    
    def create_paginated_response(self, data: list, total: int, pagination: Dict[str, int]) -> Dict[str, Any]:
        """
        Cria resposta paginada padronizada
        
        Args:
            data: Lista de dados
            total: Total de itens disponíveis
            pagination: Parâmetros de paginação
            
        Returns:
            Resposta com dados paginados e metadados
        """
        page = pagination['page']
        limit = pagination['limit']
        
        total_pages = (total + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            'data': data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev,
                'next_page': page + 1 if has_next else None,
                'prev_page': page - 1 if has_prev else None
            }
        }
    
    # ==================== CACHE HELPERS ====================
    
    def get_cache_key(self, prefix: str, *args) -> str:
        """
        Gera chave de cache padronizada
        
        Args:
            prefix: Prefixo da chave
            *args: Argumentos adicionais para formar a chave
            
        Returns:
            Chave de cache formatada
        """
        key_parts = [prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    def should_use_cache(self) -> bool:
        """
        Verifica se deve usar cache baseado nos parâmetros da requisição
        
        Returns:
            True se deve usar cache, False caso contrário
        """
        # Não usa cache se parâmetro no_cache estiver presente
        if self.get_query_param('no_cache', False, bool):
            return False
        
        # Não usa cache para métodos que não sejam GET
        if request.method != 'GET':
            return False
        
        return True