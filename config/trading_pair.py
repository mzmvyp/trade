# config/trading_pairs.py - Configuração dos Pares de Trading
import logging
from typing import Dict, List, Any
from core.trading_pair import trading_pair_manager

logger = logging.getLogger(__name__)

def initialize_trading_pairs():
    """Inicializa pares de trading com configurações padrão"""
    
    logger.info("Inicializando configurações de pares de trading...")
    
    # Pares já são inicializados automaticamente no TradingPairManager
    # Esta função serve para configurações adicionais se necessário
    
    pairs_config = get_default_pairs_config()
    
    for symbol, config in pairs_config.items():
        pair = trading_pair_manager.get_pair(symbol)
        if pair:
            # Atualiza configurações específicas
            pair.update_config(**config.get('settings', {}))
            logger.debug(f"Configurações aplicadas para {symbol}")
    
    logger.info(f"Pares de trading inicializados: {len(trading_pair_manager.get_all_pairs())} pares")

def get_default_pairs_config() -> Dict[str, Dict[str, Any]]:
    """Retorna configuração padrão dos pares"""
    
    return {
        'BTCUSDT': {
            'display_name': 'Bitcoin/USDT',
            'enabled': True,
            'color': '#f7931a',
            'icon': 'fab fa-bitcoin',
            'settings': {
                'update_interval': 5,
                'max_errors': 10,
                'retry_delay': 30
            }
        },
        'ETHUSDT': {
            'display_name': 'Ethereum/USDT',
            'enabled': True,
            'color': '#627eea',
            'icon': 'fab fa-ethereum',
            'settings': {
                'update_interval': 5,
                'max_errors': 10,
                'retry_delay': 30
            }
        },
        'SOLUSDT': {
            'display_name': 'Solana/USDT',
            'enabled': False,
            'color': '#9945ff',
            'icon': 'fas fa-sun',
            'settings': {
                'update_interval': 5,
                'max_errors': 10,
                'retry_delay': 30
            }
        }
    }

# Exporta o trading_pair_manager para compatibilidade
__all__ = ['trading_pair_manager', 'initialize_trading_pairs', 'get_default_pairs_config']