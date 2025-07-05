# web/utils.py
from flask import current_app, request
import json

def get_client_ip():
    """Obtém IP real do cliente"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def is_api_request():
    """Verifica se é uma requisição de API"""
    return request.path.startswith('/api/')

def is_ajax_request():
    """Verifica se é uma requisição AJAX"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

def get_user_agent_info():
    """Extrai informações do User-Agent"""
    user_agent = request.headers.get('User-Agent', '')
    
    return {
        'is_mobile': any(keyword in user_agent.lower() for keyword in ['mobile', 'android', 'iphone']),
        'is_tablet': any(keyword in user_agent.lower() for keyword in ['tablet', 'ipad']),
        'is_desktop': not any(keyword in user_agent.lower() for keyword in ['mobile', 'android', 'iphone', 'tablet', 'ipad']),
        'browser': extract_browser_info(user_agent),
        'os': extract_os_info(user_agent)
    }

def extract_browser_info(user_agent):
    """Extrai informações do navegador"""
    ua_lower = user_agent.lower()
    
    if 'chrome' in ua_lower:
        return 'Chrome'
    elif 'firefox' in ua_lower:
        return 'Firefox'
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        return 'Safari'
    elif 'edge' in ua_lower:
        return 'Edge'
    elif 'opera' in ua_lower:
        return 'Opera'
    else:
        return 'Unknown'

def extract_os_info(user_agent):
    """Extrai informações do sistema operacional"""
    ua_lower = user_agent.lower()
    
    if 'windows' in ua_lower:
        return 'Windows'
    elif 'mac' in ua_lower:
        return 'macOS'
    elif 'linux' in ua_lower:
        return 'Linux'
    elif 'android' in ua_lower:
        return 'Android'
    elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
        return 'iOS'
    else:
        return 'Unknown'

def safe_json_loads(json_str, default=None):
    """Parse JSON com fallback seguro"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def format_file_size(bytes_size):
    """Formata tamanho de arquivo para leitura humana"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"