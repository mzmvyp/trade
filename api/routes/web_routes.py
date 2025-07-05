# api/routes/web_routes.py
from flask import render_template, redirect, url_for
from ..controllers import DashboardController

def register_web_routes(app, system_manager):
    """Registra rotas web (páginas HTML)"""
    
    dashboard_controller = DashboardController(system_manager)
    
    @app.route('/')
    def dashboard():
        """Dashboard principal"""
        try:
            # Obtém dados iniciais para o template
            pairs_data, _ = dashboard_controller.list_pairs()
            enabled_pairs = pairs_data.get('data', {}).get('pairs', [])
            enabled_pairs = [p for p in enabled_pairs if p.get('enabled', False)]
            
            return render_template('dashboard.html', 
                                 enabled_pairs=enabled_pairs,
                                 nav_dashboard='active',
                                 system_manager=system_manager)
        except Exception as e:
            app.logger.error(f"Erro ao carregar dashboard: {e}")
            return render_template('errors/500.html'), 500
    
    @app.route('/trading')
    def trading_dashboard():
        """Dashboard de trading"""
        try:
            return render_template('trading.html',
                                 nav_trading='active',
                                 system_manager=system_manager)
        except Exception as e:
            app.logger.error(f"Erro ao carregar trading: {e}")
            return render_template('errors/500.html'), 500
    
    @app.route('/analytics')
    def analytics_dashboard():
        """Dashboard de analytics"""
        try:
            return render_template('analytics.html',
                                 nav_analytics='active',
                                 system_manager=system_manager)
        except Exception as e:
            app.logger.error(f"Erro ao carregar analytics: {e}")
            return render_template('errors/500.html'), 500
    
    @app.route('/settings')
    def settings_page():
        """Página de configurações"""
        try:
            return render_template('settings.html',
                                 nav_settings='active',
                                 system_manager=system_manager)
        except Exception as e:
            app.logger.error(f"Erro ao carregar settings: {e}")
            return render_template('errors/500.html'), 500
    
    @app.route('/help')
    def help_page():
        """Página de ajuda"""
        try:
            return render_template('help.html',
                                 system_manager=system_manager)
        except Exception as e:
            app.logger.error(f"Erro ao carregar ajuda: {e}")
            return render_template('errors/500.html'), 500
    
    @app.route('/profile')
    def profile_page():
        """Página de perfil do usuário"""
        try:
            return render_template('profile.html',
                                 system_manager=system_manager)
        except Exception as e:
            app.logger.error(f"Erro ao carregar perfil: {e}")
            return render_template('errors/500.html'), 500
    
    @app.route('/logout')
    def logout():
        """Logout (placeholder)"""
        # TODO: Implementar sistema de autenticação
        return redirect(url_for('dashboard'))