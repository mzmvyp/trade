# services/dashboard_service.py - Corrigido
from .base_service import BaseService
from typing import Dict, Any
from datetime import datetime

class DashboardService(BaseService):
    """Serviço para dados do dashboard"""
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Obtém dados completos do dashboard"""
        try:
            data = self.system_manager.get_dashboard_data()
            
            if 'error' in data:
                return self.create_response(
                    success=False,
                    error=data['error']
                )
            
            return self.create_response(data=data)
        except Exception as e:
            return self.handle_exception("get_dashboard_overview", e)
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Obtém métricas específicas do dashboard"""
        try:
            metrics = self.system_manager.get_dashboard_metrics()
            
            if 'error' in metrics:
                return self.create_response(
                    success=False,
                    error=metrics['error']
                )
            
            return self.create_response(data=metrics)
        except Exception as e:
            return self.handle_exception("get_dashboard_metrics", e)
    
    def get_quick_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas rápidas para exibição"""
        try:
            stats = self.system_manager.get_stats()
            
            # Formata estatísticas para cards do dashboard
            quick_stats = {
                'system_status': {
                    'is_running': self.system_manager.is_running,
                    'uptime': self._calculate_uptime(),
                    'status_text': 'Online' if self.system_manager.is_running else 'Offline'
                },
                'pairs_stats': {
                    'total': stats.get('total_pairs', 0),
                    'enabled': stats.get('enabled_pairs', 0),
                    'streaming': stats.get('active_streams', 0)
                },
                'data_stats': {
                    'total_points': stats.get('total_data_points', 0),
                    'last_update': stats.get('last_update')
                },
                'trading_stats': {
                    'active_signals': stats.get('active_signals', 0),
                    'total_signals': 0  # TODO: Implementar
                }
            }
            
            return self.create_response(data=quick_stats)
        except Exception as e:
            return self.handle_exception("get_quick_statistics", e)
    
    def get_real_time_data(self) -> Dict[str, Any]:
        """Obtém dados em tempo real para o dashboard"""
        try:
            # Coleta dados de todos os pares ativos
            enabled_pairs = self.system_manager.pair_manager.get_enabled_pairs()
            real_time_data = {}
            
            for pair in enabled_pairs:
                if pair.is_streaming:
                    recent_data = self.system_manager.data_streamer.get_pair_data(pair.symbol, 1)
                    if recent_data:
                        latest = recent_data[-1]
                        real_time_data[pair.symbol] = {
                            'symbol': pair.symbol,
                            'display_name': pair.display_name,
                            'current_price': latest.close,
                            'timestamp': latest.timestamp.isoformat(),
                            'volume': latest.volume,
                            'source': latest.source,
                            'color': pair.color,
                            'icon': pair.icon
                        }
            
            return self.create_response(data={
                'pairs': real_time_data,
                'timestamp': datetime.now().isoformat(),
                'active_count': len(real_time_data)
            })
        except Exception as e:
            return self.handle_exception("get_real_time_data", e)
    
    def _calculate_uptime(self) -> int:
        """Calcula uptime do sistema em segundos"""
        if not self.system_manager.start_time:
            return 0
        return int((datetime.now() - self.system_manager.start_time).total_seconds())
    