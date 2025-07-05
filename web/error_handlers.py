# web/error_handlers.py
import logging
from flask import jsonify, render_template, request
from datetime import datetime

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Registra handlers de erro personalizados"""
    
    @app.errorhandler(404)
    def not_found(error):
        """Handler para erro 404"""
        logger.warning(f"404 - Página não encontrada: {request.path}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Endpoint não encontrado',
                'path': request.path,
                'timestamp': datetime.now().isoformat()
            }), 404
        
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handler para erro 500"""
        logger.error(f"500 - Erro interno: {error}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Erro interno do servidor',
                'message': str(error) if app.config['DEBUG'] else 'Erro interno',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handler para erro 400"""
        logger.warning(f"400 - Requisição inválida: {error}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Requisição inválida',
                'message': str(error),
                'timestamp': datetime.now().isoformat()
            }), 400
        
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handler para erro 403"""
        logger.warning(f"403 - Acesso negado: {request.path}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Acesso negado',
                'path': request.path,
                'timestamp': datetime.now().isoformat()
            }), 403
        
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handler para erro 429 - Rate limit"""
        logger.warning(f"429 - Rate limit excedido: {request.remote_addr}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Rate limit excedido',
                'message': 'Muitas requisições. Tente novamente em alguns minutos.',
                'timestamp': datetime.now().isoformat()
            }), 429
        
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(503)
    def service_unavailable(error):
        """Handler para erro 503"""
        logger.error(f"503 - Serviço indisponível: {error}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Serviço temporariamente indisponível',
                'message': 'Sistema em manutenção ou sobregregado',
                'timestamp': datetime.now().isoformat()
            }), 503
        
        return render_template('errors/503.html'), 503
