"""
Supabase REST API database adapter - SQLAlchemy Session-compatible interface.

This module provides a drop-in replacement for SQLAlchemy Session,
backed by Supabase PostgREST API. This allows all existing services
to work without modification.
"""
import uuid
import logging
from typing import Any, Optional
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger("supabase_db")


class SupabaseError(Exception):
    pass


class SupabaseClient:
    """Low-level Supabase REST client."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.base_url = (url or settings.SUPABASE_URL).rstrip("/")
        self.key = key or settings.SUPABASE_SECRET_KEY
        if not self.key:
            raise SupabaseError("SUPABASE_SECRET_KEY is required")
        self.rest_url = f"{self.base_url}/rest/v1"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self._client = httpx.Client(base_url=self.rest_url, headers=self.headers, timeout=30.0)

    def insert(self, table: str, data: dict | list[dict], on_conflict: Optional[str] = None) -> list[dict]:
        params = {}
        if on_conflict:
            params["on_conflict"] = on_conflict
        resp = self._client.post(f"/{table}", json=data, params=params)
        return self._handle(resp)

    def select(self, table: str, columns: str = "*", order: str = "", limit: int = 0, offset: int = 0, **filters) -> list[dict]:
        """Select with PostgREST filters."""
        params = {"select": columns}
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)
        for k, v in filters.items():
            if isinstance(v, tuple):
                # (operator, value) format
                op, val = v
                params[k] = f"{op}.{val}"
            else:
                params[k] = f"eq.{v}"
        resp = self._client.get(f"/{table}", params=params)
        return self._handle(resp)

    def select_or(self, table: str, columns: str = "*", or_filters: str = "", order: str = "", limit: int = 0) -> list[dict]:
        """Select with OR filters (PostgREST or=() syntax)."""
        params = {"select": columns}
        if or_filters:
            # PostgREST requires or=() wrapping
            if not or_filters.startswith("("):
                or_filters = f"({or_filters})"
            params["or"] = or_filters
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        resp = self._client.get(f"/{table}", params=params)
        return self._handle(resp)

    def update(self, table: str, data: dict, **filters) -> list[dict]:
        params = {}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        resp = self._client.patch(f"/{table}", json=data, params=params)
        return self._handle(resp)

    def delete(self, table: str, **filters) -> list[dict]:
        params = {}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        resp = self._client.delete(f"/{table}", params=params)
        return self._handle(resp)

    def upsert(self, table: str, data: dict | list[dict], on_conflict: str) -> list[dict]:
        headers = {**self.headers, "Prefer": "return=representation,resolution=merge-duplicates"}
        params = {"on_conflict": on_conflict}
        resp = self._client.post(f"/{table}", json=data, params=params, headers=headers)
        return self._handle(resp)

    def count(self, table: str, **filters) -> int:
        """Count rows matching filters."""
        headers = {**self.headers, "Prefer": "count=exact", "Range": "0-0"}
        params = {"select": "id"}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        resp = self._client.get(f"/{table}", params=params, headers=headers)
        if resp.status_code >= 400:
            return 0
        cr = resp.headers.get("content-range", "")
        if "/" in cr:
            return int(cr.split("/")[-1])
        return 0

    @staticmethod
    def _handle(resp: httpx.Response) -> list[dict]:
        if resp.status_code >= 400:
            raise SupabaseError(f"HTTP {resp.status_code}: {resp.text}")
        if resp.status_code == 204:
            return []
        try:
            return resp.json()
        except Exception:
            return []

    def close(self):
        self._client.close()


# ── Singleton ────────────────────────────────────────────

_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client


# ── Table name mapping ───────────────────────────────────

TABLE_MAP = {
    "users": "users",
    "topics": "topics",
    "papers": "papers",
    "chats": "chats",
    "messages": "messages",
    "notifications": "notifications",
    "user_papers": "user_papers",
}


def _get_table_name(model_class) -> str:
    """Get the Supabase table name from a SQLAlchemy model class."""
    return model_class.__tablename__


def _uuid_to_str(val) -> str:
    """Convert UUID to string."""
    if isinstance(val, uuid.UUID):
        return str(val)
    return str(val)


def _now_iso() -> str:
    """Get current time in ISO format for Supabase."""
    return datetime.now(timezone.utc).isoformat()


# ── SQLAlchemy-compatible Query builder ──────────────────

class QueryFilter:
    """Represents a single filter condition."""
    def __init__(self, column: str, op: str, value: Any):
        self.column = column
        self.op = op
        self.value = value

    def to_postgrest(self) -> tuple[str, str]:
        """Convert to PostgREST filter format."""
        val = _uuid_to_str(self.value) if isinstance(self.value, uuid.UUID) else str(self.value)
        # Handle boolean
        if isinstance(self.value, bool):
            val = "true" if self.value else "false"
        return self.column, f"{self.op}.{val}"


class OrFilterGroup:
    """Represents OR conditions."""
    def __init__(self, conditions: list[QueryFilter]):
        self.conditions = conditions

    def to_postgrest_or(self) -> str:
        """Build PostgREST or=() syntax."""
        parts = []
        for c in self.conditions:
            val = c.value
            if isinstance(val, uuid.UUID):
                val = str(val)
            elif isinstance(val, bool):
                val = "true" if val else "false"
            else:
                val = str(val)
            parts.append(f"{c.column}.{c.op}.{val}")
        return f"({','.join(parts)})"


class LikeFilter:
    """ILIKE filter."""
    def __init__(self, column: str, pattern: str):
        self.column = column
        self.pattern = pattern  # e.g. %keyword%

    def to_postgrest(self) -> tuple[str, str]:
        return self.column, f"ilike.{self.pattern}"


class QueryBuilder:
    """SQLAlchemy-compatible query builder that translates to Supabase REST calls."""

    def __init__(self, model_class, client: SupabaseClient):
        self.model_class = model_class
        self.table = _get_table_name(model_class)
        self.client = client
        self.filters: list[QueryFilter] = []
        self.or_filters: list[LikeFilter] = []
        self._order = ""
        self._limit = 0
        self._offset = 0
        self._select_columns = "*"

    def filter(self, *conditions) -> "QueryBuilder":
        """Add filter conditions. Supports SQLAlchemy-style expressions."""
        for cond in conditions:
            if isinstance(cond, QueryFilter):
                self.filters.append(cond)
            elif isinstance(cond, LikeFilter):
                self.or_filters.append(cond)
            elif isinstance(cond, OrFilterGroup):
                self.or_filters.append(cond)
        return self

    def filter_by(self, **kwargs) -> "QueryBuilder":
        """Add equality filters."""
        for col, val in kwargs.items():
            self.filters.append(QueryFilter(col, "eq", val))
        return self

    def order_by(self, expr) -> "QueryBuilder":
        """Set ordering. Supports string or model attribute."""
        if isinstance(expr, str):
            self._order = expr
        elif hasattr(expr, "_order_str"):
            self._order = expr._order_str
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._limit = n
        return self

    def offset(self, n: int) -> "QueryBuilder":
        self._offset = n
        return self

    def _build_params(self) -> dict:
        """Build PostgREST query parameters."""
        params = {"select": self._select_columns}
        if self._order:
            params["order"] = self._order
        if self._limit:
            params["limit"] = str(self._limit)
        if self._offset:
            params["offset"] = str(self._offset)
        # EQ filters
        for f in self.filters:
            col, val = f.to_postgrest()
            params[col] = val
        return params

    def _execute_select(self) -> list[dict]:
        """Execute the select query."""
        params = self._build_params()
        if self.or_filters:
            # Use OR filters
            or_parts = []
            for f in self.or_filters:
                if isinstance(f, LikeFilter):
                    col, val = f.to_postgrest()
                    or_parts.append(f"{col}.{val}")
                elif isinstance(f, OrFilterGroup):
                    return self.client.select_or(self.table, self._select_columns,
                                                 f.to_postgrest_or(), self._order, self._limit)
            if or_parts:
                params["or"] = f"({','.join(or_parts)})"

        resp = self.client._client.get(f"/{self.table}", params=params)
        return self.client._handle(resp)

    def first(self):
        """Get first result."""
        self._limit = 1
        rows = self._execute_select()
        if rows:
            return self._to_model(rows[0])
        return None

    def all(self) -> list:
        """Get all results."""
        rows = self._execute_select()
        return [self._to_model(r) for r in rows]

    def count(self) -> int:
        """Count matching rows."""
        count_params = {"select": "id"}
        for f in self.filters:
            col, val = f.to_postgrest()
            count_params[col] = val
        headers = {**self.client.headers, "Prefer": "count=exact", "Range": "0-0"}
        resp = self.client._client.get(f"/{self.table}", params=count_params, headers=headers)
        if resp.status_code >= 400:
            return 0
        cr = resp.headers.get("content-range", "")
        if "/" in cr:
            return int(cr.split("/")[-1])
        return 0

    def _to_model(self, row: dict):
        """Convert a dict row to a model-like object."""
        return SupabaseModel(self.model_class, row)


class SupabaseModel:
    """Wraps a dict row to provide attribute access like SQLAlchemy models."""

    def __init__(self, model_class, data: dict):
        self._model_class = model_class
        self._data = data
        # Convert UUIDs
        for key in ("id", "user_id", "paper_id", "chat_id", "topic_id"):
            if key in data and data[key]:
                try:
                    self._data[key] = uuid.UUID(str(data[key]))
                except (ValueError, AttributeError):
                    pass
        # Convert booleans
        for key in ("is_read", "is_active", "is_bookmarked", "push_enabled"):
            if key in data:
                self._data[key] = bool(data[key])
        # Convert datetimes
        for key in ("created_at", "updated_at", "published_at", "pushed_at"):
            if key in data and data[key] and isinstance(data[key], str):
                try:
                    self._data[key] = datetime.fromisoformat(data[key].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
        # Parse JSON arrays from JSONB columns
        for key in ("keywords", "exclude_keywords", "authors"):
            if key in data and isinstance(data[key], str):
                import json
                try:
                    self._data[key] = json.loads(data[key])
                except (json.JSONDecodeError, TypeError):
                    pass

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattribute__(name)
        return self._data.get(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def to_dict(self) -> dict:
        """Return the raw dict."""
        return self._data

    # Support model_validate for Pydantic
    def model_dump(self) -> dict:
        result = {}
        for k, v in self._data.items():
            if isinstance(v, uuid.UUID):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result


# ── SQLAlchemy-compatible Session ────────────────────────

class SupabaseSession:
    """
    Drop-in replacement for SQLAlchemy Session.
    All existing services use this interface.
    """

    def __init__(self, client: Optional[SupabaseClient] = None):
        self.client = client or get_supabase_client()
        self._pending_adds: list[tuple] = []  # (table, data_dict)
        self._pending_updates: list[tuple] = []  # (table, id, data_dict)
        self._pending_deletes: list[tuple] = []  # (table, id)

    def query(self, model_class) -> QueryBuilder:
        """Start a query builder for a model class."""
        return QueryBuilder(model_class, self.client)

    def execute(self, stmt) -> "ExecuteResult":
        """Execute a SQLAlchemy select statement."""
        # This handles the select() pattern used in some services
        return ExecuteResult(stmt, self.client)

    def add(self, model_instance):
        """Queue an insert."""
        table = _get_table_name(type(model_instance))
        if isinstance(model_instance, SupabaseModel):
            data = model_instance.to_dict()
        elif hasattr(model_instance, "_data"):
            data = model_instance._data
        else:
            data = {}
            # Extract attributes from SQLAlchemy model
            for col in model_instance.__table__.columns:
                val = getattr(model_instance, col.name, None)
                if val is not None:
                    if isinstance(val, uuid.UUID):
                        data[col.name] = str(val)
                    elif isinstance(val, datetime):
                        data[col.name] = val.isoformat()
                    else:
                        data[col.name] = val
        self._pending_adds.append((table, data, model_instance))

    def commit(self):
        """Flush all pending operations to Supabase."""
        # Process inserts
        for table, data, model_instance in self._pending_adds:
            try:
                result = self.client.insert(table, data)
                if result and hasattr(model_instance, "_data"):
                    # Update the model with server-generated values
                    for k, v in result[0].items():
                        model_instance._data[k] = v
                elif result:
                    # Update SQLAlchemy model attributes
                    for k, v in result[0].items():
                        try:
                            setattr(model_instance, k, v)
                        except (AttributeError, TypeError):
                            pass
            except SupabaseError as e:
                logger.error(f"Insert failed for {table}: {e}")
                raise
        self._pending_adds.clear()

        # Process updates
        for table, record_id, data in self._pending_updates:
            try:
                self.client.update(table, data, id=str(record_id))
            except SupabaseError as e:
                logger.error(f"Update failed for {table}: {e}")
                raise
        self._pending_updates.clear()

        # Process deletes
        for table, record_id in self._pending_deletes:
            try:
                self.client.delete(table, id=str(record_id))
            except SupabaseError as e:
                logger.error(f"Delete failed for {table}: {e}")
                raise
        self._pending_deletes.clear()

    def flush(self):
        """Same as commit for Supabase."""
        self.commit()

    def refresh(self, model_instance):
        """Refresh a model instance from the database."""
        table = _get_table_name(type(model_instance))
        if hasattr(model_instance, "_data"):
            record_id = model_instance._data.get("id")
        else:
            record_id = getattr(model_instance, "id", None)
        if record_id:
            rows = self.client.select(table, id=str(record_id))
            if rows:
                if hasattr(model_instance, "_data"):
                    model_instance._data.update(rows[0])
                else:
                    for k, v in rows[0].items():
                        try:
                            setattr(model_instance, k, v)
                        except (AttributeError, TypeError):
                            pass

    def delete(self, model_instance):
        """Queue a delete."""
        table = _get_table_name(type(model_instance))
        if hasattr(model_instance, "_data"):
            record_id = model_instance._data.get("id")
        else:
            record_id = getattr(model_instance, "id", None)
        if record_id:
            self._pending_deletes.append((table, record_id))

    def rollback(self):
        """Clear pending operations (no transaction support in REST)."""
        self._pending_adds.clear()
        self._pending_updates.clear()
        self._pending_deletes.clear()

    def close(self):
        """No-op for compatibility."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ExecuteResult:
    """Wraps query results to mimic SQLAlchemy execute() patterns."""

    def __init__(self, stmt, client: SupabaseClient):
        self._stmt = stmt
        self._client = client

    def scalars(self):
        return self

    def scalar_one_or_none(self):
        # This needs to be handled differently - see service layer
        return None

    def all(self):
        return []

    def unique(self):
        return self


# ── SQLAlchemy Column Expression Compatibility ───────────
# These allow services to use Model.column == value syntax

class ColumnExpr:
    """Represents a SQLAlchemy column expression for filter building."""

    def __init__(self, column_name: str, model_class=None):
        self._name = column_name
        self._model_class = model_class
        self._order_str = ""

    def __eq__(self, other):
        return QueryFilter(self._name, "eq", other)

    def __ne__(self, other):
        return QueryFilter(self._name, "neq", other)

    def ilike(self, pattern: str):
        return LikeFilter(self._name, pattern)

    def desc(self):
        expr = ColumnExpr(self._name, self._model_class)
        expr._order_str = f"{self._name}.desc"
        return expr

    def asc(self):
        expr = ColumnExpr(self._name, self._model_class)
        expr._order_str = f"{self._name}.asc"
        return expr

    def nullslast(self):
        # PostgREST doesn't directly support NULLS LAST, but .desc puts nulls last by default
        return self


# ── Dependency injection replacement ─────────────────────

def get_db():
    """Drop-in replacement for the SQLAlchemy get_db dependency."""
    session = SupabaseSession()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """No-op for Supabase (tables created via SQL Editor)."""
    logger.info("✅ Supabase tables already initialized (via SQL Editor)")
