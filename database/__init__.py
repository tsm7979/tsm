"""
Database Persistence Layer
===========================

SQLite-based persistence for production deployment.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import sqlite3
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TableName(str, Enum):
    """Database table names."""
    REQUESTS = "requests"
    MODELS = "models"
    CACHE_ENTRIES = "cache_entries"
    TASKS = "tasks"
    WEBHOOKS = "webhooks"
    PLUGINS = "plugins"
    DOCUMENTS = "documents"
    METRICS = "metrics"
    AUDIT_LOG = "audit_log"


@dataclass
class RequestRecord:
    """Request record."""
    request_id: str
    input_text: str
    output_text: Optional[str]
    model: str
    provider: str
    status: str
    tokens: int
    cost: float
    latency_ms: float
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class CacheRecord:
    """Cache entry record."""
    cache_key: str
    value: str
    model: str
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: int


@dataclass
class TaskRecord:
    """Task queue record."""
    task_id: str
    function_name: str
    status: str
    priority: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[str]
    error: Optional[str]


class Database:
    """
    SQLite database for persistence.

    Provides simple ORM-like interface for TSM data.
    """

    def __init__(self, db_path: str = "tsm.db"):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

        logger.info(f"Database initialized: {db_path}")

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = sqlite3.Row

        logger.info(f"Connected to database: {self.db_path}")

    def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Disconnected from database")

    def create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()

        # Requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                request_id TEXT PRIMARY KEY,
                input_text TEXT NOT NULL,
                output_text TEXT,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                latency_ms REAL NOT NULL,
                created_at TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)

        # Models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                cost_per_1k_input REAL,
                cost_per_1k_output REAL,
                max_tokens INTEGER,
                metadata TEXT
            )
        """)

        # Cache entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_accessed TIMESTAMP NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                ttl_seconds INTEGER NOT NULL
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                function_name TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result TEXT,
                error TEXT,
                metadata TEXT
            )
        """)

        # Webhooks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                endpoint_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                events TEXT NOT NULL,
                secret TEXT,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL,
                last_delivery TIMESTAMP,
                delivery_count INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                metadata TEXT
            )
        """)

        # Plugins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plugins (
                plugin_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                plugin_type TEXT NOT NULL,
                status TEXT NOT NULL,
                loaded_at TIMESTAMP NOT NULL,
                config TEXT,
                metadata TEXT
            )
        """)

        # Documents table (for RAG)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding BLOB,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)

        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                labels TEXT
            )
        """)

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT NOT NULL,
                result TEXT,
                timestamp TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_created ON requests(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_model ON requests(model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_model ON cache_entries(model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")

        self.conn.commit()
        logger.info("Database tables created")

    # Request operations
    def save_request(self, record: RequestRecord):
        """Save request record."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.request_id,
            record.input_text,
            record.output_text,
            record.model,
            record.provider,
            record.status,
            record.tokens,
            record.cost,
            record.latency_ms,
            record.created_at,
            json.dumps(record.metadata)
        ))

        self.conn.commit()

    def get_request(self, request_id: str) -> Optional[RequestRecord]:
        """Get request by ID."""
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT * FROM requests WHERE request_id = ?",
            (request_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return RequestRecord(
            request_id=row['request_id'],
            input_text=row['input_text'],
            output_text=row['output_text'],
            model=row['model'],
            provider=row['provider'],
            status=row['status'],
            tokens=row['tokens'],
            cost=row['cost'],
            latency_ms=row['latency_ms'],
            created_at=row['created_at'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )

    def query_requests(
        self,
        model: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[RequestRecord]:
        """Query requests with filters."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM requests WHERE 1=1"
        params = []

        if model:
            query += " AND model = ?"
            params.append(model)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        records = []
        for row in cursor.fetchall():
            records.append(RequestRecord(
                request_id=row['request_id'],
                input_text=row['input_text'],
                output_text=row['output_text'],
                model=row['model'],
                provider=row['provider'],
                status=row['status'],
                tokens=row['tokens'],
                cost=row['cost'],
                latency_ms=row['latency_ms'],
                created_at=row['created_at'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {}
            ))

        return records

    # Cache operations
    def save_cache_entry(self, record: CacheRecord):
        """Save cache entry."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO cache_entries VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.cache_key,
            record.value,
            record.model,
            record.created_at,
            record.last_accessed,
            record.access_count,
            record.ttl_seconds
        ))

        self.conn.commit()

    def get_cache_entry(self, cache_key: str) -> Optional[CacheRecord]:
        """Get cache entry."""
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT * FROM cache_entries WHERE cache_key = ?",
            (cache_key,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return CacheRecord(
            cache_key=row['cache_key'],
            value=row['value'],
            model=row['model'],
            created_at=row['created_at'],
            last_accessed=row['last_accessed'],
            access_count=row['access_count'],
            ttl_seconds=row['ttl_seconds']
        )

    def delete_cache_entry(self, cache_key: str):
        """Delete cache entry."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,))
        self.conn.commit()

    def clear_cache(self, model: Optional[str] = None):
        """Clear cache entries."""
        cursor = self.conn.cursor()

        if model:
            cursor.execute("DELETE FROM cache_entries WHERE model = ?", (model,))
        else:
            cursor.execute("DELETE FROM cache_entries")

        self.conn.commit()

    # Task operations
    def save_task(self, record: TaskRecord):
        """Save task record."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.task_id,
            record.function_name,
            record.status,
            record.priority,
            record.created_at,
            record.started_at,
            record.completed_at,
            record.result,
            record.error,
            None  # metadata
        ))

        self.conn.commit()

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Get task by ID."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return TaskRecord(
            task_id=row['task_id'],
            function_name=row['function_name'],
            status=row['status'],
            priority=row['priority'],
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            result=row['result'],
            error=row['error']
        )

    def query_tasks(self, status: Optional[str] = None, limit: int = 100) -> List[TaskRecord]:
        """Query tasks."""
        cursor = self.conn.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )

        records = []
        for row in cursor.fetchall():
            records.append(TaskRecord(
                task_id=row['task_id'],
                function_name=row['function_name'],
                status=row['status'],
                priority=row['priority'],
                created_at=row['created_at'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                result=row['result'],
                error=row['error']
            ))

        return records

    # Metrics operations
    def save_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Save metric."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO metrics (metric_name, value, timestamp, labels)
            VALUES (?, ?, ?, ?)
        """, (
            metric_name,
            value,
            datetime.utcnow(),
            json.dumps(labels) if labels else None
        ))

        self.conn.commit()

    def query_metrics(
        self,
        metric_name: str,
        since: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Tuple[datetime, float]]:
        """Query metrics."""
        cursor = self.conn.cursor()

        if since:
            cursor.execute("""
                SELECT timestamp, value FROM metrics
                WHERE metric_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (metric_name, since, limit))
        else:
            cursor.execute("""
                SELECT timestamp, value FROM metrics
                WHERE metric_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (metric_name, limit))

        return [(row['timestamp'], row['value']) for row in cursor.fetchall()]

    # Audit log operations
    def log_audit_event(
        self,
        event_type: str,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log audit event."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO audit_log (event_type, user_id, resource_type, resource_id, action, result, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type,
            user_id,
            resource_type,
            resource_id,
            action,
            result,
            datetime.utcnow(),
            json.dumps(metadata) if metadata else None
        ))

        self.conn.commit()

    def query_audit_log(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit log."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if since:
            query += " AND timestamp >= ?"
            params.append(since)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        logs = []
        for row in cursor.fetchall():
            logs.append({
                'log_id': row['log_id'],
                'event_type': row['event_type'],
                'user_id': row['user_id'],
                'resource_type': row['resource_type'],
                'resource_id': row['resource_id'],
                'action': row['action'],
                'result': row['result'],
                'timestamp': row['timestamp'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })

        return logs

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor()

        stats = {}

        # Count records in each table
        tables = ['requests', 'cache_entries', 'tasks', 'webhooks', 'plugins', 'documents', 'audit_log']

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']

        # Get database size
        db_path = Path(self.db_path)
        if db_path.exists():
            stats['db_size_mb'] = db_path.stat().st_size / (1024 * 1024)

        return stats


# Global database instance
db = Database("tsm.db")
