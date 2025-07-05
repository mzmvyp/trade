# web/middleware.py
import time
from flask import request, g
import logging

logger = logging.getLogger(__name__)

def register_middleware(app):
    """Registra middlewares personalizados"""
    
    @app.before_request
    def before_request():
        """Executado antes de cada requisição"""
        g.start_time = time.time()
        
        # Log de requisição (exceto arquivos estáticos)
        if not request.path.startswith('/static/'):
            logger.debug(f"[{request.method}] {request.path} - {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """Executado após cada requisição"""
        
        # Calcula tempo de resposta
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
        
        # Headers de segurança
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Headers CORS (já definidos no app.py, mas reforçando)
        if not response.headers.get('Access-Control-Allow-Origin'):
            response.headers['Access-Control-Allow-Origin'] = '*'
        
        # Log de resposta para debug
        if app.config['DEBUG'] and not request.path.startswith('/static/'):
            logger.debug(f"[{response.status_code}] {request.path} - {response_time:.3f}s")
        
        return response
    
    @app.teardown_request
    def teardown_request(exception):
        """Cleanup após requisição"""
        if exception:
            logger.error(f"Erro na requisição {request.path}: {exception}")
