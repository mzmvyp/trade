# api/routes/__init__.py - Registro de Rotas Centralizado
import logging
from flask import Flask

from .system_routes import register_system_routes
from .pairs_routes import register_pairs_routes
from .dashboard_routes import register_dashboard_routes
from .trading_routes import register_trading_routes
from .analytics_routes import register_analytics_routes
from .web_routes import register_web_routes

logger = logging.getLogger(__name__)

def register_all_routes(app: Flask, system_manager):
    """
    Registra todas as rotas da aplicação
    
    Args:
        app: Instância da aplicação Flask
        system_manager: Instância do SystemManager
    """
    try:
        logger.info("Iniciando registro de rotas...")
        
        # Registra rotas de API
        register_api_routes(app, system_manager)
        
        # Registra rotas web (páginas HTML)
        register_web_routes(app, system_manager)
        
        # Registra rotas de utilitários
        register_utility_routes(app, system_manager)
        
        # Log de resumo
        _log_routes_summary(app)
        
        logger.info("✅ Todas as rotas registradas com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar rotas: {e}")
        raise

def register_api_routes(app: Flask, system_manager):
    """Registra todas as rotas de API"""
    
    logger.info("📡 Registrando rotas de API...")
    
    # Rotas do sistema
    register_system_routes(app, system_manager)
    logger.debug("   ✓ System routes registradas")
    
    # Rotas de pares
    register_pairs_routes(app, system_manager)
    logger.debug("   ✓ Pairs routes registradas")
    
    # Rotas do dashboard
    register_dashboard_routes(app, system_manager)
    logger.debug("   ✓ Dashboard routes registradas")
    
    # Rotas de trading
    register_trading_routes(app, system_manager)
    logger.debug("   ✓ Trading routes registradas")
    
    # Rotas de analytics
    register_analytics_routes(app, system_manager)
    logger.debug("   ✓ Analytics routes registradas")
    
    logger.info("📡 Rotas de API registradas")

def register_utility_routes(app: Flask, system_manager):
    """Registra rotas utilitárias"""
    
    logger.info("🔧 Registrando rotas utilitárias...")
    
    @app.route('/ping', methods=['GET'])
    def ping():
        """Endpoint simples para verificar se a aplicação está rodando"""
        return {'status': 'ok', 'message': 'Bitcoin Trading System is running'}, 200
    
    @app.route('/version', methods=['GET'])
    def version():
        """Retorna informações de versão"""
        return {
            'version': system_manager.config.VERSION,
            'environment': system_manager.config.ENVIRONMENT,
            'debug': system_manager.config.DEBUG
        }, 200
    
    @app.route('/routes', methods=['GET'])
    def list_routes():
        """Lista todas as rotas disponíveis"""
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
                    'path': str(rule),
                    'description': _get_route_description(rule.endpoint)
                })
        
        return {
            'total_routes': len(routes),
            'routes': sorted(routes, key=lambda x: x['path'])
        }, 200
    
    logger.info("🔧 Rotas utilitárias registradas")

def _get_route_description(endpoint: str) -> str:
    """Obtém descrição da rota baseada no endpoint"""
    descriptions = {
        # System routes
        'system_status': 'Status geral do sistema',
        'system_stats': 'Estatísticas do sistema',
        'start_system': 'Inicia o sistema',
        'stop_system': 'Para o sistema',
        'restart_system': 'Reinicia o sistema',
        'health_check': 'Verificação de saúde',
        
        # Pairs routes
        'list_pairs': 'Lista todos os pares',
        'get_pair_status': 'Status de um par específico',
        'start_pair': 'Inicia streaming de um par',
        'stop_pair': 'Para streaming de um par',
        'get_pair_data': 'Dados históricos de um par',
        'update_pair_config': 'Atualiza configuração de um par',
        
        # Dashboard routes
        'dashboard_data': 'Dados completos do dashboard',
        'dashboard_metrics': 'Métricas do dashboard',
        'quick_stats': 'Estatísticas rápidas',
        
        # Trading routes
        'get_trading_signals': 'Lista sinais de trading',
        'create_manual_signal': 'Cria sinal manual',
        'close_signal': 'Fecha sinal específico',
        'get_trading_indicators': 'Obtém indicadores técnicos',
        'get_pattern_stats': 'Estatísticas de padrões',
        
        # Analytics routes
        'get_performance_summary': 'Resumo de performance',
        'get_pair_analytics': 'Analytics de um par específico',
        'get_market_overview': 'Overview do mercado',
        'export_analytics_data': 'Exporta dados de analytics',
        
        # Web routes
        'dashboard': 'Dashboard principal (HTML)',
        'trading_dashboard': 'Dashboard de trading (HTML)',
        'analytics_dashboard': 'Dashboard de analytics (HTML)',
        'settings_page': 'Página de configurações (HTML)',
        
        # Utility routes
        'ping': 'Verificação básica de conectividade',
        'version': 'Informações de versão',
        'list_routes': 'Lista todas as rotas disponíveis'
    }
    
    return descriptions.get(endpoint, 'Sem descrição disponível')

def _log_routes_summary(app: Flask):
    """Registra resumo das rotas no log"""
    
    # Contadores por tipo
    api_routes = 0
    web_routes = 0
    utility_routes = 0
    
    # Categoriza rotas
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        
        path = str(rule)
        
        if path.startswith('/api/'):
            api_routes += 1
        elif rule.endpoint in ['ping', 'version', 'list_routes']:
            utility_routes += 1
        else:
            web_routes += 1
    
    total_routes = api_routes + web_routes + utility_routes
    
    logger.info("📊 RESUMO DAS ROTAS:")
    logger.info(f"   🔗 Total: {total_routes}")
    logger.info(f"   📡 API: {api_routes}")
    logger.info(f"   🌐 Web: {web_routes}")
    logger.info(f"   🔧 Utilitárias: {utility_routes}")

def register_error_routes(app: Flask):
    """Registra rotas de tratamento de erro"""
    
    @app.route('/api/test-error', methods=['GET'])
    def test_error():
        """Endpoint para testar tratamento de erros (apenas em debug)"""
        if not app.config.get('DEBUG'):
            return {'error': 'Endpoint disponível apenas em modo debug'}, 403
        
        error_type = app.args.get('type', 'generic')
        
        if error_type == 'database':
            raise Exception("Erro simulado de banco de dados")
        elif error_type == 'network':
            raise ConnectionError("Erro simulado de rede")
        elif error_type == 'validation':
            raise ValueError("Erro simulado de validação")
        else:
            raise Exception("Erro genérico simulado")

def register_development_routes(app: Flask, system_manager):
    """Registra rotas específicas para desenvolvimento"""
    
    if not app.config.get('DEBUG'):
        return
    
    logger.info("🔧 Registrando rotas de desenvolvimento...")
    
    @app.route('/dev/reset-system', methods=['POST'])
    def dev_reset_system():
        """Reseta sistema para estado inicial (apenas debug)"""
        try:
            # Para sistema
            system_manager.stop()
            
            # Reseta erros
            system_manager.data_streamer.reset_all_errors()
            
            # Limpa dados em memória
            for pair in system_manager.pair_manager.get_all_pairs():
                pair.price_history.clear()
                pair.reset_errors()
            
            return {'status': 'success', 'message': 'Sistema resetado'}, 200
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}, 500
    
    @app.route('/dev/simulate-data', methods=['POST'])
    def dev_simulate_data():
        """Gera dados simulados para teste (apenas debug)"""
        try:
            import random
            from datetime import datetime, timedelta
            from core.trading_pair import PriceData
            
            symbol = request.json.get('symbol', 'BTCUSDT')
            count = min(request.json.get('count', 10), 100)  # Máximo 100
            
            pair = system_manager.pair_manager.get_pair(symbol)
            if not pair:
                return {'status': 'error', 'message': f'Par {symbol} não encontrado'}, 404
            
            # Gera dados simulados
            base_price = 45000
            for i in range(count):
                timestamp = datetime.now() - timedelta(minutes=i)
                price = base_price * (1 + random.uniform(-0.02, 0.02))
                
                price_data = PriceData(
                    timestamp=timestamp,
                    symbol=symbol,
                    price=price,
                    open=price,
                    high=price * 1.01,
                    low=price * 0.99,
                    close=price,
                    volume=random.uniform(1000000, 5000000),
                    source='simulated'
                )
                
                pair.add_price_data(price_data)
            
            return {
                'status': 'success', 
                'message': f'{count} dados simulados gerados para {symbol}'
            }, 200
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}, 500
    
    @app.route('/dev/memory-stats', methods=['GET'])
    def dev_memory_stats():
        """Estatísticas de uso de memória (apenas debug)"""
        try:
            import sys
            
            stats = {
                'python_version': sys.version,
                'data_points_in_memory': sum(
                    len(p.price_history) for p in system_manager.pair_manager.get_all_pairs()
                ),
                'pairs_count': len(system_manager.pair_manager.get_all_pairs()),
                'streaming_pairs': len(system_manager.pair_manager.get_streaming_pairs())
            }
            
            # Adiciona estatísticas de memória se psutil disponível
            try:
                import psutil
                import os
                
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                
                stats.update({
                    'memory_rss_mb': memory_info.rss / (1024 * 1024),
                    'memory_vms_mb': memory_info.vms / (1024 * 1024),
                    'cpu_percent': process.cpu_percent(),
                    'threads_count': process.num_threads()
                })
                
            except ImportError:
                stats['psutil_available'] = False
            
            return stats, 200
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}, 500
    
    logger.info("🔧 Rotas de desenvolvimento registradas")

def register_admin_routes(app: Flask, system_manager):
    """Registra rotas administrativas"""
    
    logger.info("👑 Registrando rotas administrativas...")
    
    @app.route('/admin/config', methods=['GET'])
    def admin_get_config():
        """Obtém configuração atual do sistema"""
        try:
            config_dict = system_manager.config.get_config_dict()
            
            # Remove informações sensíveis
            config_dict.pop('secret_key', None)
            
            return config_dict, 200
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}, 500
    
    @app.route('/admin/config', methods=['POST'])
    def admin_update_config():
        """Atualiza configuração do sistema"""
        try:
            from flask import request
            
            data = request.get_json()
            if not data:
                return {'status': 'error', 'message': 'JSON inválido'}, 400
            
            # Atualiza configurações por seção
            updated_sections = []
            for section, values in data.items():
                if isinstance(values, dict):
                    try:
                        system_manager.config.update_config(section, **values)
                        updated_sections.append(section)
                    except ValueError as e:
                        return {'