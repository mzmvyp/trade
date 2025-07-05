# app.py - Aplicação Principal Modularizada (VERSÃO FINAL)
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Adiciona diretórios ao path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask
from utils.logging_config import setup_logging
from config.settings import Config
from api.routes import register_all_routes
from core.system_manager import SystemManager
from web.error_handlers import register_error_handlers
from web.template_helpers import register_template_helpers
from web.middleware import register_middleware

logger = setup_logging()

class TradingSystemApp:
    """
    Aplicação principal do sistema de trading
    Arquitetura modular e escalável
    
    Responsabilidades:
    - Configuração da aplicação Flask
    - Registro de componentes (controllers, rotas, middlewares)
    - Orquestração dos serviços
    """
    
    def __init__(self):
        self.app = self._create_app()
        self.config = Config()
        self.system_manager = SystemManager()
        
        self._setup_app()
        self._register_components()
    
    def _create_app(self):
        """Cria e configura aplicação Flask básica"""
        app = Flask(__name__)
        
        # Configurações Flask essenciais
        app.config.update({
            'SECRET_KEY': os.getenv('SECRET_KEY', 'trading-system-secret-key'),
            'DEBUG': os.getenv('DEBUG', 'false').lower() == 'true',
            'TESTING': False,
            'JSON_SORT_KEYS': False,
            'JSONIFY_PRETTYPRINT_REGULAR': True,
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file upload
        })
        
        return app
    
    def _setup_app(self):
        """Configura aplicação com context processors e hooks"""
        
        # Context processor global para templates
        @self.app.context_processor
        def inject_globals():
            return {
                'current_year': datetime.now().year,
                'version': self.config.VERSION,
                'debug': self.app.config['DEBUG'],
                'system_name': 'Bitcoin Trading System',
                'system_manager': self.system_manager
            }
        
        # Request logging middleware
        @self.app.before_request
        def log_request():
            from flask import request
            if not request.path.startswith('/static/'):
                logger.debug(f"{request.method} {request.path} - {request.remote_addr}")
        
        # CORS headers
        @self.app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response
    
    def _register_components(self):
        """Registra todos os componentes da aplicação de forma modular"""
        
        # 1. Registra handlers de erro personalizados
        register_error_handlers(self.app)
        logger.info("✅ Error handlers registrados")
        
        # 2. Registra helpers e filtros para templates
        register_template_helpers(self.app)
        logger.info("✅ Template helpers registrados")
        
        # 3. Registra middlewares customizados
        register_middleware(self.app)
        logger.info("✅ Middlewares registrados")
        
        # 4. Registra todas as rotas (API + Web)
        register_all_routes(self.app, self.system_manager)
        logger.info("✅ Rotas registradas")
        
        logger.info("🎯 Todos os componentes registrados com sucesso")
    
    def run(self, host='0.0.0.0', port=5000, debug=None):
        """Executa aplicação com informações detalhadas"""
        if debug is None:
            debug = self.app.config['DEBUG']
        
        self._show_startup_banner(host, port)
        
        try:
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                use_reloader=False  # Evita problemas com threads
            )
        except KeyboardInterrupt:
            logger.info("\n🛑 Aplicação interrompida pelo usuário")
            self.shutdown()
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar aplicação: {e}")
            raise
    
    def _show_startup_banner(self, host, port):
        """Exibe banner detalhado de inicialização"""
        logger.info("=" * 80)
        logger.info("🚀 BITCOIN TRADING SYSTEM - SISTEMA MODULAR INICIADO")
        logger.info("=" * 80)
        logger.info(f"📊 Versão: {self.config.VERSION}")
        logger.info(f"🏗️  Arquitetura: Modular (Controllers + Services + Core)")
        logger.info(f"🌐 Endereço: http://{host}:{port}")
        logger.info("")
        logger.info("📱 PÁGINAS WEB:")
        logger.info(f"   • Dashboard: http://localhost:{port}/")
        logger.info(f"   • Trading: http://localhost:{port}/trading")
        logger.info(f"   • Analytics: http://localhost:{port}/analytics")
        logger.info(f"   • Configurações: http://localhost:{port}/settings")
        logger.info("")
        logger.info("🔗 APIS PRINCIPAIS:")
        logger.info(f"   • Sistema: http://localhost:{port}/api/system/status")
        logger.info(f"   • Pares: http://localhost:{port}/api/pairs/list")
        logger.info(f"   • Dashboard: http://localhost:{port}/api/dashboard/data")
        logger.info(f"   • Trading: http://localhost:{port}/api/trading/signals")
        logger.info(f"   • Analytics: http://localhost:{port}/api/analytics/performance")
        logger.info("")
        logger.info("⌨️  CONTROLES:")
        logger.info("   • Ctrl+C para parar")
        logger.info("   • POST /api/system/start para iniciar")
        logger.info("   • POST /api/system/stop para parar")
        logger.info("   • GET /api/system/health para health check")
        logger.info("=" * 80)
        
        # Mostra informações dos pares
        self.system_manager.show_available_pairs()
        
        # Mostra estrutura modular
        self._show_modular_structure()
        logger.info("")
    
    def _show_modular_structure(self):
        """Mostra estrutura modular carregada"""
        logger.info("🏗️  ESTRUTURA MODULAR CARREGADA:")
        logger.info("   📁 Controllers: System, Pairs, Dashboard, Trading, Analytics")
        logger.info("   📁 Services: System, Pairs, Dashboard, Trading, Analytics")
        logger.info("   📁 Routes: API + Web routes registradas")
        logger.info("   📁 Core: SystemManager, DataStreamer, TradingPairs")
        logger.info("   📁 Web: ErrorHandlers, TemplateHelpers, Middleware")
    
    def shutdown(self):
        """Finaliza aplicação de forma limpa"""
        logger.info("🔧 Finalizando aplicação...")
        
        try:
            # Finaliza SystemManager
            self.system_manager.shutdown()
            logger.info("✅ SystemManager finalizado")
            
            # Cleanup adicional se necessário
            logger.info("✅ Aplicação finalizada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro durante finalização: {e}")
    
    def get_app(self):
        """Retorna instância Flask para uso externo (ex: WSGI)"""
        return self.app


def create_directories():
    """Cria estrutura de diretórios necessária"""
    directories = [
        'data',
        'logs', 
        'static/css',
        'static/js', 
        'static/images',
        'templates',
        'templates/errors',
        'config',
        'api/controllers',
        'api/routes',
        'services',
        'web',
        'core',
        'utils'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    logger.info("📁 Estrutura de diretórios criada")


def validate_environment():
    """Valida configurações e ambiente"""
    try:
        # Valida configurações
        config = Config()
        errors = config.validate()
        
        if errors:
            logger.warning("⚠️  Avisos de configuração:")
            for error in errors:
                logger.warning(f"   • {error}")
        
        # Verifica dependências críticas
        try:
            import flask, requests, numpy, pandas
            logger.info("✅ Dependências críticas OK")
        except ImportError as e:
            logger.error(f"❌ Dependência ausente: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação do ambiente: {e}")
        return False


def main():
    """Função principal com tratamento robusto de erros"""
    try:
        logger.info("🚀 Iniciando Bitcoin Trading System...")
        
        # 1. Cria estrutura de diretórios
        create_directories()
        
        # 2. Valida ambiente
        if not validate_environment():
            logger.error("❌ Falha na validação do ambiente")
            return 1
        
        # 3. Cria e configura aplicação
        logger.info("🏗️  Criando aplicação modular...")
        app = TradingSystemApp()
        
        # 4. Configurações de execução
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # 5. Executa aplicação
        logger.info("🎯 Iniciando servidor Flask...")
        app.run(host=host, port=port, debug=debug)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n👋 Aplicação interrompida pelo usuário")
        return 0
    except Exception as e:
        logger.error(f"💥 Erro crítico: {e}")
        import traceback
        logger.error(f"📋 Traceback completo:\n{traceback.format_exc()}")
        return 1


# Factory function para uso em WSGI/deployment
def create_app():
    """Factory function para criar app Flask (para WSGI)"""
    create_directories()
    trading_app = TradingSystemApp()
    return trading_app.get_app()


if __name__ == "__main__":
    # Configura exit code
    exit_code = main()
    
    # Log final
    if exit_code == 0:
        logger.info("✅ Aplicação finalizada com sucesso")
    else:
        logger.error("❌ Aplicação finalizada com erro")
    
    sys.exit(exit_code)