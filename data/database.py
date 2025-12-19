import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trading:trading@localhost:5432/trading_db")


class DatabaseManager:
    """Manages PostgreSQL database connections using a connection pool."""

    _instance = None
    _pool: pool.ThreadedConnectionPool | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, min_connections: int = 1, max_connections: int = 10):
        if self._pool is None:
            self._pool = pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                DATABASE_URL
            )

    @contextmanager
    def get_connection(self) -> Generator:
        """Get a connection from the pool."""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit: bool = True) -> Generator:
        """Get a cursor with automatic connection management."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results as list of dicts."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchall()
            return []

    def execute_many(self, query: str, params_list: list[tuple]) -> None:
        """Execute a query with multiple parameter sets."""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)

    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None


# Singleton instance
db = DatabaseManager()
