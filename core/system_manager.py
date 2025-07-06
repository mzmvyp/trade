# core/system_manager.py - Gerenciador Central do Sistema (COMPLETO)
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from .trading_pair import trading_pair_manager
from .data_streamer import multi_pair_streamer
from .data_manager import get_database_manager
from config.settings import Config

logger = logging.getLogger(__name__)

class SystemManager:
    """
    Gerenciador central do sistema de trading
    Coordena todos os componentes principais
    """
    
    def __init__(self):
        self.config = Config()
        self.is_running = False
        self.start_time = None
        
        # Componentes principais
        self.pair_manager = trading_pair_manager
        self.data_streamer = multi_pair_streamer
        self.database = get_database_manager()
        
        # Estado do sistema
        self.system_stats = {
            'total_pairs': 0,
            'enabled_pairs': 0,
            'active_streams': 0,
            'total_data_points': 0,
            'active_signals': 0,
            'last_update': None
        }
        
        logger.info("SystemManager inicializado")
    
    # ==================== CONTROLE DO SISTEMA ====================
    
    def start(self) -> Dict[str, Any]:
        """Inicia sistema completo"""
        try:
            if self.is_running:
                return {
                    'success': False,
                    'message': 'Sistema já está em execução'
                }
            
            logger.info("Iniciando sistema...")
            
            # Inicia streaming para pares habilitados
            self.data_streamer.start_all_enabled()
            
            # Marca sistema como ativo
            self.is_running = True
            self.start_time = datetime.now()
            
            # Atualiza estatísticas
            self._update_system_stats()
            
            logger.info("Sistema iniciado com sucesso")
            
            return {
                'success': True,
                'message': 'Sistema iniciado com sucesso',
                'started_at': self.start_time.isoformat(),
                'enabled_pairs': len(self.pair_manager.get_enabled_pairs())
            }
            
        except Exception as e:
            logger.error(f"Erro ao iniciar sistema: {e}")
            return {
                'success': False,
                'message': f'Erro ao iniciar sistema: {str(e)}'
            }
    
    def stop(self) -> Dict[str, Any]:
        """Para sistema completo"""
        try:
            if not self.is_running:
                return {
                    'success': False,
                    'message': 'Sistema não está em execução'
                }
            
            logger.info("Parando sistema...")
            
            # Para todos os streamings
            self.data_streamer.stop_all()
            
            # Marca sistema como parado
            self.is_running = False
            
            # Atualiza estatísticas
            self._update_system_stats()
            
            logger.info("Sistema parado com sucesso")
            
            return {
                'success': True,
                'message': 'Sistema parado com sucesso'
            }
            
        except Exception as e:
            logger.error(f"Erro ao parar sistema: {e}")
            return {
                'success': False,
                'message': f'Erro ao parar sistema: {str(e)}'
            }
    
    def restart(self) -> Dict[str, Any]:
        """Reinicia sistema"""
        try:
            logger.info("Reiniciando sistema...")
            
            # Para sistema
            stop_result = self.stop()
            if not stop_result['success']:
                return stop_result
            
            # Aguarda um pouco
            import time
            time.sleep(2)
            
            # Inicia sistema
            start_result = self.start()
            
            if start_result['success']:
                logger.info("Sistema reiniciado com sucesso")
                return {
                    'success': True,
                    'message': 'Sistema reiniciado com sucesso'
                }
            else:
                return start_result
                
        except Exception as e:
            logger.error(f"Erro ao reiniciar sistema: {e}")
            return {
                'success': False,
                'message': f'Erro ao reiniciar sistema: {str(e)}'
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema"""
        enabled_pairs = self.pair_manager.get_enabled_pairs()
        streaming_stats = self.data_streamer.get_all_statistics()
        
        uptime = 0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'system_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': uptime,
            'enabled_pairs': len(enabled_pairs),
            'active_streams': streaming_stats['summary']['active_streams'],
            'total_data_points': streaming_stats['summary']['total_data_points'],
            'pair_manager_summary': self.pair_manager.get_summary(),
            'streaming_stats': streaming_stats,
            'version': self.config.VERSION,
            'debug_mode': self.config.DEBUG,
            'database_stats': self.database.get_database_stats()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas resumidas"""
        self._update_system_stats()
        return self.system_stats
    
    # ==================== GERENCIAMENTO DE PARES ====================
    
    def get_pairs_list(self) -> Dict[str, Any]:
        """Lista todos os pares"""
        pairs = self.pair_manager.get_all_pairs()
        return {
            'pairs': [pair.get_status() for pair in pairs],
            'total': len(pairs),
            'enabled': len([p for p in pairs if p.enabled])
        }
    
    def start_pair(self, symbol: str) -> Dict[str, Any]:
        """Inicia streaming para par específico"""
        try:
            pair = self.pair_manager.get_pair(symbol)
            if not pair:
                return {
                    'success': False,
                    'message': f'Par {symbol} não encontrado'
                }
            
            if not pair.enabled:
                return {
                    'success': False,
                    'message': f'Par {symbol} está desabilitado'
                }
            
            success = self.data_streamer.start_pair(symbol)
            
            if success:
                logger.info(f"Streaming iniciado para {symbol}")
                self._update_system_stats()
                return {
                    'success': True,
                    'message': f'Streaming iniciado para {symbol}'
                }
            else:
                return {
                    'success': False,
                    'message': f'Erro ao iniciar streaming para {symbol}'
                }
                
        except Exception as e:
            logger.error(f"Erro ao iniciar par {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def stop_pair(self, symbol: str) -> Dict[str, Any]:
        """Para streaming para par específico"""
        try:
            success = self.data_streamer.stop_pair(symbol)
            
            if success:
                logger.info(f"Streaming parado para {symbol}")
                self._update_system_stats()
                return {
                    'success': True,
                    'message': f'Streaming parado para {symbol}'
                }
            else:
                return {
                    'success': False,
                    'message': f'Par {symbol} não estava em streaming'
                }
                
        except Exception as e:
            logger.error(f"Erro ao parar par {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_pair_data(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """Obtém dados recentes de um par"""
        try:
            limit = min(limit, 1000)  # Máximo 1000 pontos
            data = self.data_streamer.get_pair_data(symbol, limit)
            
            return {
                'symbol': symbol,
                'data': [d.to_dict() for d in data],
                'count': len(data)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter dados do par {symbol}: {e}")
            return {
                'error': str(e)
            }
    
    # ==================== DASHBOARD ====================
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Dados completos do dashboard"""
        try:
            # Dados dos pares
            pairs_data = {}
            for pair in self.pair_manager.get_enabled_pairs():
                recent_data = self.data_streamer.get_pair_data(pair.symbol, 20)
                if recent_data:
                    latest = recent_data[-1]
                    pairs_data[pair.symbol] = {
                        'current_price': latest.close,
                        'volume_24h': latest.volume,
                        'recent_data': [d.to_dict() for d in recent_data],
                        'pair_info': pair.get_status()
                    }
            
            # Status do sistema
            system_status = {
                'is_running': self.is_running,
                'active_pairs': len([p for p in self.pair_manager.get_enabled_pairs() if p.is_streaming]),
                'total_data_points': sum(len(self.data_streamer.get_pair_data(p.symbol)) 
                                       for p in self.pair_manager.get_enabled_pairs())
            }
            
            return {
                'pairs_data': pairs_data,
                'system_status': system_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter dados do dashboard: {e}")
            return {
                'error': str(e)
            }
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Métricas específicas do dashboard"""
        try:
            enabled_pairs = self.pair_manager.get_enabled_pairs()
            streaming_pairs = [p for p in enabled_pairs if p.is_streaming]
            
            # TODO: Implementar contagem de sinais quando signal_manager estiver pronto
            total_signals = 0
            active_signals = 0
            success_rate = 0
            
            return {
                'total_pairs': len(self.pair_manager.get_all_pairs()),
                'enabled_pairs': len(enabled_pairs),
                'active_pairs': len(streaming_pairs),
                'total_signals': total_signals,
                'active_signals': active_signals,
                'success_rate': success_rate,
                'system_running': self.is_running,
                'uptime': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter métricas do dashboard: {e}")
            return {
                'error': str(e)
            }
    
    # ==================== TRADING ====================
    
    def get_trading_signals(self, limit: int = 50, status: str = None) -> Dict[str, Any]:
        """Obtém sinais de trading"""
        try:
            # TODO: Implementar quando signal_manager estiver pronto
            return {
                'signals': [],
                'total': 0,
                'message': 'Signal Manager não implementado ainda'
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter sinais de trading: {e}")
            return {
                'error': str(e)
            }
    
    def get_trading_indicators(self, symbol: str = None) -> Dict[str, Any]:
        """Obtém indicadores técnicos"""
        try:
            # TODO: Implementar quando technical_analyzer estiver pronto
            return {
                'indicators': {},
                'message': 'Technical Analyzer não implementado ainda'
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter indicadores: {e}")
            return {
                'error': str(e)
            }
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas de padrões"""
        try:
            # TODO: Implementar quando pattern detector estiver pronto
            return {
                'stats': [],
                'message': 'Pattern Stats não implementado ainda'
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de padrões: {e}")
            return {
                'error': str(e)
            }
    
    # ==================== UTILITIES ====================
    
    def _update_system_stats(self):
        """Atualiza estatísticas do sistema"""
        try:
            all_pairs = self.pair_manager.get_all_pairs()
            enabled_pairs = self.pair_manager.get_enabled_pairs()
            streaming_stats = self.data_streamer.get_all_statistics()
            
            self.system_stats.update({
                'total_pairs': len(all_pairs),
                'enabled_pairs': len(enabled_pairs),
                'active_streams': streaming_stats['summary']['active_streams'],
                'total_data_points': streaming_stats['summary']['total_data_points'],
                'active_signals': 0,  # TODO: Implementar
                'last_update': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
    
    def show_available_pairs(self):
        """Mostra pares disponíveis no log"""
        enabled_pairs = self.pair_manager.get_enabled_pairs()
        total_pairs = len(self.pair_manager.get_all_pairs())
        
        logger.info(f"💰 Pares de Trading: {len(enabled_pairs)}/{total_pairs} habilitados")
        for pair in enabled_pairs:
            logger.info(f"   • {pair.symbol} ({pair.display_name}) - {pair.color}")
        
        if not enabled_pairs:
            logger.warning("⚠️ Nenhum par habilitado. Habilite pares em /settings")
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do sistema"""
        try:
            health = {
                'status': 'healthy',
                'checks': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Verifica componentes
            health['checks']['pair_manager'] = 'ok' if self.pair_manager else 'error'
            health['checks']['data_streamer'] = 'ok' if self.data_streamer else 'error'
            health['checks']['database'] = 'ok' if self.database else 'error'
            
            # Verifica banco de dados
            try:
                db_health = self.database.health_check()
                health['checks']['database_detail'] = db_health['status']
            except:
                health['checks']['database_detail'] = 'error'
            
            # Determina status geral
            if any(status == 'error' for status in health['checks'].values()):
                health['status'] = 'unhealthy'
            elif any(status == 'warning' for status in health['checks'].values()):
                health['status'] = 'degraded'
            
            return health
            
        except Exception as e:
            logger.error(f"Erro no health check: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def shutdown(self):
        """Finaliza sistema e componentes"""
        try:
            logger.info("Finalizando SystemManager...")
            
            # Para streaming se estiver rodando
            if self.is_running:
                self.data_streamer.stop_all()
                self.is_running = False
            
            # Cleanup dos componentes
            self.data_streamer.shutdown()
            
            logger.info("SystemManager finalizado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro durante finalização do SystemManager: {e}")

# Instância global (singleton)
_system_manager = None

def get_system_manager() -> SystemManager:
    """Retorna instância global do SystemManager"""
    global _system_manager
    
    if _system_manager is None:
        _system_manager = SystemManager()
    
    return _system_manager