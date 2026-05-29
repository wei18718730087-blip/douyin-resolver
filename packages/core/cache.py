"""SQLite-based cache for resolve results."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from packages.core.schemas import ResolveResult

# Default cache TTL: 1 hour
DEFAULT_TTL = 3600

# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "douyin-resolver"


class ResolveCache:
    """SQLite-backed cache for Douyin resolve results.

    Args:
        db_path: Path to SQLite database file.
        ttl: Cache time-to-live in seconds.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ttl: int = DEFAULT_TTL,
    ):
        if db_path is None:
            db_path = DEFAULT_CACHE_DIR / "cache.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.ttl = ttl
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create cache table if not exists."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS resolve_cache (
                aweme_id TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON resolve_cache(expires_at)
        """)
        self._conn.commit()

    def get(self, aweme_id: str) -> Optional[ResolveResult]:
        """Get cached result for an aweme_id.

        Returns None if not cached or expired.
        """
        now = time.time()
        row = self._conn.execute(
            "SELECT result_json FROM resolve_cache WHERE aweme_id = ? AND expires_at > ?",
            (aweme_id, now),
        ).fetchone()

        if row is None:
            return None

        try:
            data = json.loads(row[0])
            return ResolveResult(**data)
        except (json.JSONDecodeError, Exception):
            return None

    def set(self, aweme_id: str, result: ResolveResult) -> None:
        """Cache a resolve result."""
        now = time.time()
        expires_at = now + self.ttl

        self._conn.execute(
            """
            INSERT OR REPLACE INTO resolve_cache
            (aweme_id, result_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (aweme_id, result.model_dump_json(), now, expires_at),
        )
        self._conn.commit()

    def delete(self, aweme_id: str) -> None:
        """Remove a cached result."""
        self._conn.execute(
            "DELETE FROM resolve_cache WHERE aweme_id = ?",
            (aweme_id,),
        )
        self._conn.commit()

    def clear_expired(self) -> int:
        """Remove all expired entries. Returns number of deleted rows."""
        now = time.time()
        cursor = self._conn.execute(
            "DELETE FROM resolve_cache WHERE expires_at <= ?",
            (now,),
        )
        self._conn.commit()
        return cursor.rowcount

    def stats(self) -> dict:
        """Get cache statistics."""
        now = time.time()
        total = self._conn.execute("SELECT COUNT(*) FROM resolve_cache").fetchone()[0]
        active = self._conn.execute(
            "SELECT COUNT(*) FROM resolve_cache WHERE expires_at > ?",
            (now,),
        ).fetchone()[0]

        return {
            "total_entries": total,
            "active_entries": active,
            "expired_entries": total - active,
            "ttl_seconds": self.ttl,
            "db_path": str(self.db_path),
        }

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
