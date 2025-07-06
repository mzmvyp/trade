# core/database_manager.py - Gerenciador de Banco de Dados
import logging
import sqlite3
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import time

from .trading_pair import PriceData

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gerenciador de banco de dados SQLite para o sistema de trading
    Responsável por persistir dados históricos, sinais e configurações
    """
    
    def __init__(self, db_path: str = "data/trading_system.db"):
        """
        Inicializa o gerenciador de banco de dados
        
        Args:
            db_path: Caminho para o arquivo do banco de dados
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.Lock()
        self._local = threading.local()
        
        # Configurações
        self.connection_timeout = 30
        self.max_retries = 3
        self.retry_delay = 1
        
        # Estatísticas
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'connections_created': 0,
            'last_error': None,
            'start_time': datetime.now()
        }
        
        # Inicializa banco de dados
        self._initialize_database()
        
        logger.info(f"DatabaseManager inicializado: {self.db_path}")
    
    # ==================== CONEXÃO ====================
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtém conexão thread-local com o banco"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                self._local.connection = sqlite3.connect(
                    str(self.db_path),
                    timeout=self.connection_timeout,
                    check_same_thread=False
                )
                
                # Configurações de performance e integridade
                self._local.connection.execute("PRAGMA journal_mode=WAL")
                self._local.connection.execute("PRAGMA synchronous=NORMAL")
                self._local.connection.execute("PRAGMA cache_size=10000")
                self._local.connection.execute("PRAGMA temp_store=MEMORY")
                
                # Row factory para resultados como dict
                self._local.connection.row_factory = sqlite3.Row
                
                self.stats['connections_created'] += 1
                logger.debug("Nova conexão de banco criada")
                
            except sqlite3.Error as e:
                logger.error(f"Erro ao conectar ao banco: {e}")
                raise
        
        return self._local.connection
    
    def _execute_with_retry(self, query: str, params: tuple = (), 
                           fetch: str = None) -> Optional[Union[List[sqlite3.Row], sqlite3.Row, int]]:
        """
        Executa query com retry automático
        
        Args:
            query: Query SQL
            params: Parâmetros da query
            fetch: Tipo de fetch ('all', 'one', None para operações sem retorno)
            
        Returns:
            Resultado da query ou None em caso de erro
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                with self._lock:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute(query, params)
                    
                    # Determina tipo de retorno
                    if fetch == 'all':
                        result = cursor.fetchall()
                    elif fetch == 'one':
                        result = cursor.fetchone()
                    else:
                        result = cursor.rowcount
                    
                    conn.commit()
                    
                    self.stats['successful_queries'] += 1
                    self.stats['total_queries'] += 1
                    
                    return result
                    
            except sqlite3.Error as e:
                last_error = e
                self.stats['failed_queries'] += 1
                self.stats['last_error'] = str(e)
                
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                
                # Reconecta em caso de erro de conexão
                if hasattr(self._local, 'connection'):
                    try:
                        self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        # Se chegou até aqui, todas as tentativas falharam
        logger.error(f"Query falhou após {self.max_retries} tentativas: {last_error}")
        self.stats['total_queries'] += 1
        return None
    
    # ==================== INICIALIZAÇÃO ====================
    
    def _initialize_database(self):
        """Inicializa estrutura do banco de dados"""
        # Tabela de dados de preço
        price_data_table = """
        CREATE TABLE IF NOT EXISTS price_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume REAL,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX(symbol, timestamp),
            INDEX(timestamp),
            INDEX(symbol)
        )
        """
        
        # Tabela de sinais de trading
        trading_signals_table = """
        CREATE TABLE IF NOT EXISTS trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            entry_price REAL NOT NULL,
            target_price REAL,
            stop_loss REAL,
            confidence REAL,
            status TEXT DEFAULT 'ACTIVE',
            current_price REAL,
            profit_loss REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            closed_at DATETIME,
            close_reason TEXT,
            metadata TEXT,
            INDEX(symbol),
            INDEX(status),
            INDEX(created_at),
            INDEX(signal_type)
        )
        """
        
        # Tabela de indicadores técnicos
        technical_indicators_table = """
        CREATE TABLE IF NOT EXISTS technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            symbol TEXT NOT NULL,
            indicator_name TEXT NOT NULL,
            indicator_value REAL,
            timeframe TEXT DEFAULT '5m',
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX(symbol, timestamp),
            INDEX(indicator_name),
            INDEX(timestamp)
        )
        """
        
        # Tabela de configurações
        configurations_table = """
        CREATE TABLE IF NOT EXISTS configurations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            config_type TEXT DEFAULT 'string',
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Tabela de logs do sistema
        system_logs_table = """
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            level TEXT NOT NULL,
            component TEXT,
            message TEXT NOT NULL,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX(timestamp),
            INDEX(level),
            INDEX(component)
        )
        """
        
        # Executa criação das tabelas
        tables = [
            price_data_table,
            trading_signals_table,
            technical_indicators_table,
            configurations_table,
            system_logs_table
        ]
        
        for table in tables:
            result = self._execute_with_retry(table)
            if result is None:
                raise Exception("Falha ao inicializar estrutura do banco")
        
        logger.info("Estrutura do banco de dados inicializada")
    
    # ==================== DADOS DE PREÇO ====================
    
    def save_price_data(self, price_data: PriceData) -> bool:
        """
        Salva dados de preço no banco
        
        Args:
            price_data: Dados de preço a serem salvos
            
        Returns:
            True se salvo com sucesso
        """
        query = """
        INSERT INTO price_data 
        (timestamp, symbol, price, open_price, high_price, low_price, 
         close_price, volume, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            price_data.timestamp,
            price_data.symbol,
            price_data.price,
            price_data.open,
            price_data.high,
            price_data.low,
            price_data.close,
            price_data.volume,
            price_data.source
        )
        
        result = self._execute_with_retry(query, params)
        return result is not None
    
    def save_price_data_batch(self, price_data_list: List[PriceData]) -> int:
        """
        Salva múltiplos dados de preço em lote
        
        Args:
            price_data_list: Lista de dados de preço
            
        Returns:
            Número de registros salvos
        """
        if not price_data_list:
            return 0
        
        query = """
        INSERT INTO price_data 
        (timestamp, symbol, price, open_price, high_price, low_price, 
         close_price, volume, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = [
            (
                data.timestamp, data.symbol, data.price, data.open,
                data.high, data.low, data.close, data.volume, data.source
            )
            for data in price_data_list
        ]
        
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.executemany(query, params_list)
                conn.commit()
                
                saved_count = cursor.rowcount
                self.stats['successful_queries'] += 1
                self.stats['total_queries'] += 1
                
                logger.debug(f"Salvos {saved_count} pontos de dados em lote")
                return saved_count
                
        except sqlite3.Error as e:
            logger.error(f"Erro ao salvar dados em lote: {e}")
            self.stats['failed_queries'] += 1
            self.stats['last_error'] = str(e)
            return 0
    
    def get_price_data(self, symbol: str, limit: int = 100, 
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Obtém dados históricos de preço
        
        Args:
            symbol: Símbolo do par
            limit: Número máximo de registros
            start_time: Data/hora inicial
            end_time: Data/hora final
            
        Returns:
            Lista de dados de preço
        """
        query = "SELECT * FROM price_data WHERE symbol = ?"
        params = [symbol]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        result = self._execute_with_retry(query, tuple(params), 'all')
        
        if result is None:
            return []
        
        return [dict(row) for row in result]
    
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtém preço mais recente de um símbolo
        
        Args:
            symbol: Símbolo do par
            
        Returns:
            Dados do preço mais recente ou None
        """
        query = """
        SELECT * FROM price_data 
        WHERE symbol = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        
        result = self._execute_with_retry(query, (symbol,), 'one')
        
        if result:
            return dict(result)
        return None
    
    # ==================== SINAIS DE TRADING ====================
    
    def save_trading_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Salva sinal de trading
        
        Args:
            signal_data: Dados do sinal
            
        Returns:
            True se salvo com sucesso
        """
        query = """
        INSERT INTO trading_signals 
        (signal_id, symbol, pattern_type, signal_type, entry_price, 
         target_price, stop_loss, confidence, status, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            signal_data.get('signal_id'),
            signal_data.get('symbol'),
            signal_data.get('pattern_type'),
            signal_data.get('signal_type'),
            signal_data.get('entry_price'),
            signal_data.get('target_price'),
            signal_data.get('stop_loss'),
            signal_data.get('confidence'),
            signal_data.get('status', 'ACTIVE'),
            json.dumps(signal_data.get('metadata', {}))
        )
        
        result = self._execute_with_retry(query, params)
        return result is not None
    
    def update_trading_signal(self, signal_id: str, updates: Dict[str, Any]) -> bool:
        """
        Atualiza sinal de trading
        
        Args:
            signal_id: ID do sinal
            updates: Campos a serem atualizados
            
        Returns:
            True se atualizado com sucesso
        """
        if not updates:
            return False
        
        # Constrói query dinamicamente
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key == 'metadata':
                set_clauses.append(f"{key} = ?")
                params.append(json.dumps(value))
            else:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"UPDATE trading_signals SET {', '.join(set_clauses)} WHERE signal_id = ?"
        params.append(signal_id)
        
        result = self._execute_with_retry(query, tuple(params))
        return result is not None and result > 0
    
    def get_trading_signals(self, symbol: Optional[str] = None, 
                           status: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém sinais de trading
        
        Args:
            symbol: Filtrar por símbolo (opcional)
            status: Filtrar por status (opcional)
            limit: Número máximo de registros
            
        Returns:
            Lista de sinais
        """
        query = "SELECT * FROM trading_signals WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        result = self._execute_with_retry(query, tuple(params), 'all')
        
        if result is None:
            return []
        
        signals = []
        for row in result:
            signal = dict(row)
            # Decodifica metadata JSON
            if signal.get('metadata'):
                try:
                    signal['metadata'] = json.loads(signal['metadata'])
                except json.JSONDecodeError:
                    signal['metadata'] = {}
            
            signals.append(signal)
        
        return signals
    
    # ==================== INDICADORES TÉCNICOS ====================
    
    def save_technical_indicator(self, symbol: str, indicator_name: str, 
                                value: float, timeframe: str = '5m',
                                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Salva indicador técnico
        
        Args:
            symbol: Símbolo do par
            indicator_name: Nome do indicador
            value: Valor do indicador
            timeframe: Timeframe do indicador
            metadata: Metadados adicionais
            
        Returns:
            True se salvo com sucesso
        """
        query = """
        INSERT INTO technical_indicators 
        (timestamp, symbol, indicator_name, indicator_value, timeframe, metadata)
        VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
        """
        
        params = (
            symbol,
            indicator_name,
            value,
            timeframe,
            json.dumps(metadata or {})
        )
        
        result = self._execute_with_retry(query, params)
        return result is not None
    
    def get_technical_indicators(self, symbol: str, indicator_name: Optional[str] = None,
                               timeframe: str = '5m', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém indicadores técnicos
        
        Args:
            symbol: Símbolo do par
            indicator_name: Nome específico do indicador (opcional)
            timeframe: Timeframe dos indicadores
            limit: Número máximo de registros
            
        Returns:
            Lista de indicadores
        """
        query = "SELECT * FROM technical_indicators WHERE symbol = ? AND timeframe = ?"
        params = [symbol, timeframe]
        
        if indicator_name:
            query += " AND indicator_name = ?"
            params.append(indicator_name)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        result = self._execute_with_retry(query, tuple(params), 'all')
        
        if result is None:
            return []
        
        indicators = []
        for row in result:
            indicator = dict(row)
            # Decodifica metadata JSON
            if indicator.get('metadata'):
                try:
                    indicator['metadata'] = json.loads(indicator['metadata'])
                except json.JSONDecodeError:
                    indicator['metadata'] = {}
            
            indicators.append(indicator)
        
        return indicators
    
    # ==================== CONFIGURAÇÕES ====================
    
    def save_configuration(self, key: str, value: Any, 
                          config_type: str = 'string',
                          description: str = None) -> bool:
        """
        Salva configuração do sistema
        
        Args:
            key: Chave da configuração
            value: Valor da configuração
            config_type: Tipo da configuração
            description: Descrição da configuração
            
        Returns:
            True se salvo com sucesso
        """
        # Converte valor para string JSON se necessário
        if config_type == 'json':
            value_str = json.dumps(value)
        else:
            value_str = str(value)
        
        query = """
        INSERT OR REPLACE INTO configurations 
        (config_key, config_value, config_type, description, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        params = (key, value_str, config_type, description)
        
        result = self._execute_with_retry(query, params)
        return result is not None
    
    def get_configuration(self, key: str, default: Any = None) -> Any:
        """
        Obtém configuração do sistema
        
        Args:
            key: Chave da configuração
            default: Valor padrão se não encontrado
            
        Returns:
            Valor da configuração ou valor padrão
        """
        query = "SELECT config_value, config_type FROM configurations WHERE config_key = ?"
        
        result = self._execute_with_retry(query, (key,), 'one')
        
        if not result:
            return default
        
        value_str = result['config_value']
        config_type = result['config_type']
        
        # Converte valor baseado no tipo
        try:
            if config_type == 'json':
                return json.loads(value_str)
            elif config_type == 'int':
                return int(value_str)
            elif config_type == 'float':
                return float(value_str)
            elif config_type == 'bool':
                return value_str.lower() in ('true', '1', 'yes')
            else:
                return value_str
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Erro ao converter configuração {key}, retornando padrão")
            return default
    
    def get_all_configurations(self) -> Dict[str, Any]:
        """
        Obtém todas as configurações
        
        Returns:
            Dicionário com todas as configurações
        """
        query = "SELECT config_key, config_value, config_type FROM configurations"
        
        result = self._execute_with_retry(query, (), 'all')
        
        if result is None:
            return {}
        
        configs = {}
        for row in result:
            key = row['config_key']
            value_str = row['config_value']
            config_type = row['config_type']
            
            # Converte valor baseado no tipo
            try:
                if config_type == 'json':
                    configs[key] = json.loads(value_str)
                elif config_type == 'int':
                    configs[key] = int(value_str)
                elif config_type == 'float':
                    configs[key] = float(value_str)
                elif config_type == 'bool':
                    configs[key] = value_str.lower() in ('true', '1', 'yes')
                else:
                    configs[key] = value_str
            except (json.JSONDecodeError, ValueError):
                configs[key] = value_str
        
        return configs
    
    # ==================== LOGS DO SISTEMA ====================
    
    def save_system_log(self, level: str, component: str, message: str,
                       details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Salva log do sistema
        
        Args:
            level: Nível do log (DEBUG, INFO, WARNING, ERROR)
            component: Componente que gerou o log
            message: Mensagem do log
            details: Detalhes adicionais
            
        Returns:
            True se salvo com sucesso
        """
        query = """
        INSERT INTO system_logs 
        (timestamp, level, component, message, details)
        VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)
        """
        
        params = (
            level.upper(),
            component,
            message,
            json.dumps(details or {})
        )
        
        result = self._execute_with_retry(query, params)
        return result is not None
    
    def get_system_logs(self, level: Optional[str] = None,
                       component: Optional[str] = None,
                       limit: int = 100,
                       hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtém logs do sistema
        
        Args:
            level: Filtrar por nível (opcional)
            component: Filtrar por componente (opcional)
            limit: Número máximo de registros
            hours: Últimas X horas
            
        Returns:
            Lista de logs
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = "SELECT * FROM system_logs WHERE timestamp >= ?"
        params = [cutoff_time]
        
        if level:
            query += " AND level = ?"
            params.append(level.upper())
        
        if component:
            query += " AND component = ?"
            params.append(component)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        result = self._execute_with_retry(query, tuple(params), 'all')
        
        if result is None:
            return []
        
        logs = []
        for row in result:
            log = dict(row)
            # Decodifica details JSON
            if log.get('details'):
                try:
                    log['details'] = json.loads(log['details'])
                except json.JSONDecodeError:
                    log['details'] = {}
            
            logs.append(log)
        
        return logs
    
    # ==================== LIMPEZA E MANUTENÇÃO ====================
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        Remove dados antigos do banco
        
        Args:
            days: Manter apenas dados dos últimos X dias
            
        Returns:
            Dicionário com contadores de registros removidos
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        removed_counts = {}
        
        # Tabelas e campos de timestamp para limpeza
        cleanup_tables = {
            'price_data': 'timestamp',
            'technical_indicators': 'timestamp',
            'system_logs': 'timestamp'
        }
        
        for table, timestamp_field in cleanup_tables.items():
            query = f"DELETE FROM {table} WHERE {timestamp_field} < ?"
            result = self._execute_with_retry(query, (cutoff_date,))
            
            if result is not None:
                removed_counts[table] = result
                logger.info(f"Removidos {result} registros antigos de {table}")
            else:
                removed_counts[table] = 0
        
        # Executa VACUUM para otimizar banco
        self._execute_with_retry("VACUUM")
        
        logger.info(f"Limpeza concluída: {sum(removed_counts.values())} registros removidos")
        return removed_counts
    
    def optimize_database(self) -> bool:
        """
        Otimiza o banco de dados
        
        Returns:
            True se otimização foi bem-sucedida
        """
        try:
            # Analisa estatísticas das tabelas
            self._execute_with_retry("ANALYZE")
            
            # Recompacta banco
            self._execute_with_retry("VACUUM")
            
            # Atualiza estatísticas novamente
            self._execute_with_retry("ANALYZE")
            
            logger.info("Banco de dados otimizado")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao otimizar banco: {e}")
            return False
    
    # ==================== ESTATÍSTICAS E RELATÓRIOS ====================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do banco de dados
        
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            'file_size_mb': 0,
            'total_records': 0,
            'tables': {},
            'performance': self.stats.copy()
        }
        
        # Tamanho do arquivo
        try:
            stats['file_size_mb'] = round(self.db_path.stat().st_size / (1024 * 1024), 2)
        except:
            pass
        
        # Contagem de registros por tabela
        tables = ['price_data', 'trading_signals', 'technical_indicators', 
                 'configurations', 'system_logs']
        
        for table in tables:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = self._execute_with_retry(query, (), 'one')
            
            if result:
                count = result['count']
                stats['tables'][table] = count
                stats['total_records'] += count
        
        # Calcula uptime
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        stats['performance']['uptime_seconds'] = uptime
        
        # Taxa de sucesso
        total_queries = self.stats['total_queries']
        if total_queries > 0:
            stats['performance']['success_rate'] = (
                self.stats['successful_queries'] / total_queries * 100
            )
        else:
            stats['performance']['success_rate'] = 0
        
        return stats
    
    def get_data_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém resumo dos dados armazenados
        
        Args:
            symbol: Filtrar por símbolo específico (opcional)
            
        Returns:
            Resumo dos dados
        """
        summary = {
            'price_data': {},
            'signals': {},
            'indicators': {}
        }
        
        # Resumo de dados de preço
        if symbol:
            price_query = """
            SELECT 
                COUNT(*) as total,
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price
            FROM price_data 
            WHERE symbol = ?
            """
            params = (symbol,)
        else:
            price_query = """
            SELECT 
                COUNT(*) as total,
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM price_data
            """
            params = ()
        
        result = self._execute_with_retry(price_query, params, 'one')
        if result:
            summary['price_data'] = dict(result)
        
        # Resumo de sinais
        if symbol:
            signals_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active,
                COUNT(CASE WHEN status = 'HIT_TARGET' THEN 1 END) as profitable,
                COUNT(CASE WHEN status = 'HIT_STOP' THEN 1 END) as stopped
            FROM trading_signals 
            WHERE symbol = ?
            """
            params = (symbol,)
        else:
            signals_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active,
                COUNT(CASE WHEN status = 'HIT_TARGET' THEN 1 END) as profitable,
                COUNT(CASE WHEN status = 'HIT_STOP' THEN 1 END) as stopped,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM trading_signals
            """
            params = ()
        
        result = self._execute_with_retry(signals_query, params, 'one')
        if result:
            summary['signals'] = dict(result)
        
        return summary
    
    # ==================== BACKUP E RESTORE ====================
    
    def create_backup(self, backup_path: Optional[str] = None) -> str:
        """
        Cria backup do banco de dados
        
        Args:
            backup_path: Caminho para o backup (opcional)
            
        Returns:
            Caminho do arquivo de backup criado
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/backup_trading_system_{timestamp}.db"
        
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with self._lock:
                conn = self._get_connection()
                
                # Cria backup usando SQLite backup API
                backup_conn = sqlite3.connect(str(backup_path))
                conn.backup(backup_conn)
                backup_conn.close()
            
            logger.info(f"Backup criado: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            raise
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restaura banco de dados de um backup
        
        Args:
            backup_path: Caminho do arquivo de backup
            
        Returns:
            True se restaurado com sucesso
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            logger.error(f"Arquivo de backup não encontrado: {backup_path}")
            return False
        
        try:
            # Fecha conexões existentes
            if hasattr(self._local, 'connection') and self._local.connection:
                self._local.connection.close()
                self._local.connection = None
            
            # Substitui arquivo atual
            import shutil
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"Banco restaurado de: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            return False
    
    # ==================== HEALTH CHECK ====================
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde do banco de dados
        
        Returns:
            Relatório de saúde
        """
        health = {
            'status': 'healthy',
            'issues': [],
            'checks': {}
        }
        
        try:
            # Teste de conectividade
            result = self._execute_with_retry("SELECT 1", (), 'one')
            health['checks']['connectivity'] = 'ok' if result else 'error'
            
            if not result:
                health['issues'].append("Falha na conectividade")
                health['status'] = 'unhealthy'
            
            # Verifica integridade
            result = self._execute_with_retry("PRAGMA integrity_check", (), 'one')
            integrity_ok = result and result[0] == 'ok'
            health['checks']['integrity'] = 'ok' if integrity_ok else 'error'
            
            if not integrity_ok:
                health['issues'].append("Problemas de integridade detectados")
                health['status'] = 'unhealthy'
            
            # Verifica espaço em disco
            try:
                file_size = self.db_path.stat().st_size / (1024 * 1024)  # MB
                if file_size > 1000:  # 1GB
                    health['issues'].append(f"Banco muito grande: {file_size:.1f}MB")
                    if health['status'] == 'healthy':
                        health['status'] = 'warning'
                
                health['checks']['disk_usage'] = f"{file_size:.1f}MB"
            except:
                health['checks']['disk_usage'] = 'unknown'
            
            # Verifica performance
            error_rate = 0
            if self.stats['total_queries'] > 0:
                error_rate = (self.stats['failed_queries'] / self.stats['total_queries']) * 100
            
            health['checks']['error_rate'] = f"{error_rate:.1f}%"
            
            if error_rate > 10:
                health['issues'].append(f"Alta taxa de erro: {error_rate:.1f}%")
                if health['status'] == 'healthy':
                    health['status'] = 'degraded'
            
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"Erro no health check: {e}")
            health['checks']['general'] = 'error'
        
        return health
    
    # ==================== SHUTDOWN ====================
    
    def close(self):
        """Fecha conexões e finaliza gerenciador"""
        try:
            if hasattr(self._local, 'connection') and self._local.connection:
                self._local.connection.close()
                self._local.connection = None
            
            logger.info("DatabaseManager finalizado")
            
        except Exception as e:
            logger.error(f"Erro ao finalizar DatabaseManager: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def __str__(self) -> str:
        """Representação string do gerenciador"""
        return f"DatabaseManager(db_path={self.db_path}, connections={self.stats['connections_created']})"


# Instância global do gerenciador
_database_manager = None

def get_database_manager() -> DatabaseManager:
    """Retorna instância global do DatabaseManager"""
    global _database_manager
    
    if _database_manager is None:
        _database_manager = DatabaseManager()
    
    return _database_manager