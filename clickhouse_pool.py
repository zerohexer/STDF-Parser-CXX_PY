"""
ClickHouse connection pool implementation

This module provides thread-safe connection management for ClickHouse
"""

import queue
import threading
import time
from clickhouse_driver import Client


class ClickHouseConnectionPool:
    """
    A thread-safe connection pool for ClickHouse
    
    This class manages a pool of ClickHouse connections for multi-threaded use,
    ensuring each thread gets its own dedicated connection.
    """
    
    def __init__(self, host='localhost', port=9000, database='default', 
                user='default', password='', max_connections=10, **kwargs):
        """
        Initialize the connection pool with customizable settings
        
        Parameters:
        - host: ClickHouse server hostname
        - port: ClickHouse server port
        - database: Database name
        - user: Username for authentication
        - password: Password for authentication
        - max_connections: Maximum number of connections to create
        - **kwargs: Additional parameters to override default connection settings
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.max_connections = max_connections
        
        # Connection pool and management
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.Lock()
        
        # Default settings for connections
        self.connection_settings = {
            'max_insert_block_size': 1000000,
            'min_insert_block_size_rows': 100000,        # Increased from 10000
            'min_insert_block_size_bytes': 52428800,     # 50MB (increased from 10MB)
            'max_threads': 32,                           # Increased from 8 to 32
            'max_insert_threads': 32,                    # Increased from 8 to 32
            'max_execution_time': 600,                   # Increased from 300 to 600
            'receive_timeout': 600,                      # Increased from 300 to 600
            'send_timeout': 600,                         # Increased from 300 to 600
            'socket_timeout': 600,                       # Added socket timeout
            'connect_timeout': 30,                       # Increased from 10 to 30
            'max_memory_usage': 20000000000,             # 20GB (increased from 10GB)
            'max_bytes_before_external_sort': 10000000000, # 10GB before using external sort
            'join_algorithm': 'hash'                     # Use hash join algorithm
        }
        
        # Override with any provided settings
        if 'settings' in kwargs and kwargs['settings']:
            self.connection_settings.update(kwargs['settings'])
        
        # Pre-fill the pool with some connections
        self._fill_pool(min(3, max_connections))
    
    def _create_connection(self):
        """Create a new ClickHouse connection"""
        try:
            client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                settings=self.connection_settings
            )
            # Test the connection
            result = client.execute("SELECT 1")
            if result and result[0][0] == 1:
                return client
            else:
                raise Exception("Connection test failed")
        except Exception as e:
            print(f"Error creating connection: {e}")
            raise
    
    def _fill_pool(self, num_connections):
        """Fill the pool with connections"""
        for _ in range(num_connections):
            try:
                with self.lock:
                    if self.active_connections < self.max_connections:
                        connection = self._create_connection()
                        self.pool.put(connection)
                        self.active_connections += 1
            except Exception as e:
                print(f"Error filling pool: {e}")
                break
    
    def get_connection(self, timeout=10):
        """
        Get a connection from the pool
        
        If no connection is available, and the pool isn't at capacity,
        a new connection will be created. Otherwise, waits for a connection
        to become available.
        
        Parameters:
        - timeout: How long to wait for a connection, in seconds
        
        Returns:
        - A ClickHouse client connection
        """
        try:
            # Try to get a connection from the pool first
            return self.pool.get(block=False)
        except queue.Empty:
            # If the pool is empty but not at capacity, create a new connection
            with self.lock:
                if self.active_connections < self.max_connections:
                    try:
                        connection = self._create_connection()
                        self.active_connections += 1
                        return connection
                    except Exception as e:
                        print(f"Error creating new connection: {e}")
                        # Fall back to waiting for a connection from the pool
                        pass
            
            # Wait for a connection to become available
            try:
                print("Connection pool exhausted, waiting for an available connection...")
                return self.pool.get(timeout=timeout)
            except queue.Empty:
                raise Exception("Timed out waiting for a connection")
    
    def return_connection(self, connection):
        """
        Return a connection to the pool
        
        Parameters:
        - connection: The connection to return
        """
        if connection is None:
            return
            
        # Check if connection is still valid
        try:
            # Test connection with a simple query
            result = connection.execute("SELECT 1")
            if result and result[0][0] == 1:
                # Connection is still good, return it to the pool
                self.pool.put(connection, block=False)
            else:
                # Connection is not valid, close it and decrease count
                self._close_connection(connection)
        except Exception as e:
            # Connection is not valid, close it and decrease count
            print(f"Connection error, removing from pool: {e}")
            self._close_connection(connection)
    
    def _close_connection(self, connection):
        """Close a connection and decrease the active count"""
        try:
            connection.disconnect()
        except Exception:
            pass
        finally:
            with self.lock:
                self.active_connections -= 1
    
    def close_all(self):
        """Close all connections in the pool"""
        while True:
            try:
                connection = self.pool.get(block=False)
                self._close_connection(connection)
            except queue.Empty:
                break
        
        with self.lock:
            self.active_connections = 0
    
    def __enter__(self):
        """Support for with statement"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close all connections when exiting the context"""
        self.close_all()


class ConnectionManager:
    """
    A context manager for safely using a connection from the pool
    
    Usage:
    with ConnectionManager(pool) as client:
        client.execute("SELECT 1")
    """
    
    def __init__(self, pool):
        self.pool = pool
        self.connection = None
    
    def __enter__(self):
        self.connection = self.pool.get_connection()
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pool.return_connection(self.connection)
