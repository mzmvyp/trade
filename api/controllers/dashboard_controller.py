# api/controllers/dashboard_controller.py - Atualizado
from .base_controller import BaseController
from services import DashboardService

class DashboardController(BaseController):
    """Controller para dados do dashboard - usando services"""
    
    def __init__(self, system_manager):
        super().__init__(system_manager)
        self.service = DashboardService(system_manager)
    
    def get_dashboard_data(self):
        """GET /api/dashboard/data"""
        result = self.service.get_dashboard_overview()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_dashboard_metrics(self):
        """GET /api/dashboard/metrics"""
        result = self.service.get_dashboard_metrics()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_quick_stats(self):
        """GET /api/dashboard/quick-stats"""
        result = self.service.get_quick_statistics()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
    
    def get_real_time_data(self):
        """GET /api/dashboard/realtime"""
        result = self.service.get_real_time_data()
        
        if result['success']:
            return self.success_response(result['data'])
        else:
            return self.error_response(result['error'], 500)
