# web/template_helpers.py - Corrigido
from datetime import datetime, timedelta
import json
from flask import request

def register_template_helpers(app):
    """Registra helpers e filtros para templates"""
    
    @app.template_filter('datetime')
    def datetime_filter(value, format='%d/%m/%Y %H:%M'):
        """Formata datetime para template"""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        
        if isinstance(value, datetime):
            return value.strftime(format)
        return value
    
    @app.template_filter('timeago')
    def timeago_filter(value):
        """Retorna tempo relativo (ex: '5 minutos atrás')"""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        
        if not isinstance(value, datetime):
            return value
        
        now = datetime.now()
        if value.tzinfo:
            now = now.replace(tzinfo=value.tzinfo)
        
        diff = now - value
        
        if diff.days > 0:
            return f"{diff.days} dia{'s' if diff.days > 1 else ''} atrás"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hora{'s' if hours > 1 else ''} atrás"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minuto{'s' if minutes > 1 else ''} atrás"
        else:
            return "Agora mesmo"
    
    @app.template_filter('currency')
    def currency_filter(value, symbol='$', decimals=2):
        """Formata valor como moeda"""
        try:
            if isinstance(value, str):
                value = float(value)
            return f"{symbol}{value:,.{decimals}f}"
        except (ValueError, TypeError):
            return value
    
    @app.template_filter('percentage')
    def percentage_filter(value, decimals=2):
        """Formata valor como porcentagem"""
        try:
            if isinstance(value, str):
                value = float(value)
            return f"{value:.{decimals}f}%"
        except (ValueError, TypeError):
            return value
    
    @app.template_filter('number')
    def number_filter(value, decimals=0):
        """Formata número com separadores"""
        try:
            if isinstance(value, str):
                value = float(value)
            if decimals == 0:
                return f"{int(value):,}"
            return f"{value:,.{decimals}f}"
        except (ValueError, TypeError):
            return value
    
    @app.template_filter('volume')
    def volume_filter(value):
        """Formata volume de forma legível"""
        try:
            if isinstance(value, str):
                value = float(value)
            
            if value >= 1_000_000_000:
                return f"{value/1_000_000_000:.2f}B"
            elif value >= 1_000_000:
                return f"{value/1_000_000:.2f}M"
            elif value >= 1_000:
                return f"{value/1_000:.2f}K"
            else:
                return f"{value:.2f}"
        except (ValueError, TypeError):
            return value
    
    @app.template_filter('json_pretty')
    def json_pretty_filter(value):
        """Formata JSON de forma legível"""
        try:
            if isinstance(value, str):
                value = json.loads(value)
            return json.dumps(value, indent=2, ensure_ascii=False)
        except:
            return value
    
    @app.template_filter('status_badge')
    def status_badge_filter(status):
        """Retorna classe CSS para badge de status"""
        status_map = {
            'active': 'badge-success',
            'inactive': 'badge-secondary',
            'error': 'badge-danger',
            'warning': 'badge-warning',
            'running': 'badge-success',
            'stopped': 'badge-danger',
            'streaming': 'badge-primary',
            'enabled': 'badge-success',
            'disabled': 'badge-secondary',
            'online': 'badge-success',
            'offline': 'badge-danger'
        }
        return status_map.get(status.lower() if isinstance(status, str) else '', 'badge-secondary')
    
    @app.template_filter('signal_class')
    def signal_class_filter(signal_type):
        """Retorna classe CSS para tipo de sinal"""
        signal_map = {
            'buy': 'text-success',
            'strong_buy': 'text-success font-weight-bold',
            'sell': 'text-danger',
            'strong_sell': 'text-danger font-weight-bold',
            'hold': 'text-muted',
            'bullish': 'text-success',
            'bearish': 'text-danger',
            'neutral': 'text-muted'
        }
        return signal_map.get(signal_type.lower() if isinstance(signal_type, str) else '', 'text-muted')
    
    @app.template_filter('truncate_text')
    def truncate_text_filter(text, length=50):
        """Trunca texto para exibição"""
        if not isinstance(text, str):
            return text
        
        if len(text) <= length:
            return text
        
        return text[:length] + '...'
    
    @app.template_global()
    def get_system_time():
        """Retorna timestamp atual do sistema"""
        return datetime.now().isoformat()
    
    @app.template_global()
    def format_uptime(seconds):
        """Formata uptime em formato legível"""
        if not isinstance(seconds, (int, float)):
            return "0s"
        
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    @app.template_global()
    def get_pair_color(symbol):
        """Retorna cor do par de trading"""
        color_map = {
            'BTCUSDT': '#f7931a',
            'ETHUSDT': '#627eea',
            'SOLUSDT': '#9945ff',
            'BNBUSDT': '#f3ba2f',
            'ADAUSDT': '#0033ad',
            'DOTUSDT': '#e6007a',
            'LINKUSDT': '#2a5ada'
        }
        return color_map.get(symbol, '#007bff')
    
    @app.template_global()
    def get_pair_icon(symbol):
        """Retorna ícone do par de trading"""
        icon_map = {
            'BTCUSDT': 'fab fa-bitcoin',
            'ETHUSDT': 'fab fa-ethereum',
            'SOLUSDT': 'fas fa-sun',
            'BNBUSDT': 'fas fa-coins',
            'ADAUSDT': 'fas fa-heart',
            'DOTUSDT': 'fas fa-circle',
            'LINKUSDT': 'fas fa-link'
        }
        return icon_map.get(symbol, 'fas fa-coins')
    
    @app.template_global()
    def format_pattern_name(pattern_type):
        """Formata nome do padrão para exibição"""
        if not isinstance(pattern_type, str):
            return pattern_type
        
        # Remove underscores e capitaliza
        return pattern_type.replace('_', ' ').title()
    
    @app.template_global()
    def get_indicator_description(indicator_name):
        """Retorna descrição do indicador"""
        descriptions = {
            'RSI': 'Índice de Força Relativa',
            'MACD': 'MACD - Convergência/Divergência de Médias Móveis',
            'SMA': 'Média Móvel Simples',
            'EMA': 'Média Móvel Exponencial',
            'BB': 'Bandas de Bollinger',
            'STOCH': 'Oscilador Estocástico',
            'WILLIAMS': 'Williams %R',
            'ATR': 'Average True Range',
            'VOLUME': 'Volume'
        }
        
        # Extrai o nome base do indicador
        base_name = indicator_name.split('_')[0] if '_' in indicator_name else indicator_name
        return descriptions.get(base_name, indicator_name)
    
    @app.template_global()
    def is_mobile_device():
        """Detecta se é dispositivo móvel"""
        user_agent = request.headers.get('User-Agent', '').lower()
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
        return any(keyword in user_agent for keyword in mobile_keywords)
    
    @app.template_global()
    def get_chart_config():
        """Retorna configuração padrão para gráficos"""
        return {
            'responsive': True,
            'maintainAspectRatio': False,
            'animation': {
                'duration': 750
            },
            'plugins': {
                'legend': {
                    'display': True,
                    'position': 'top'
                }
            }
        }