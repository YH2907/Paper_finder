"""
Minimal Supabase REST (PostgREST) client using httpx.
"""
from typing import Any, Optional

import httpx

from app.config import settings


# PostgREST endpoint derived from settings
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_SECRET_KEY = settings.SUPABASE_SECRET_KEY

# PostgREST endpoint
REST_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""
# SQL endpoint (for schema init)
SQL_URL = f"{SUPABASE_URL}/rest/v1/rpc" if SUPABASE_URL else ""


class SupabaseError(Exception):
    pass


class SupabaseClient:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.base_url = (url or SUPABASE_URL).rstrip("/")
        self.key = key or SUPABASE_SECRET_KEY
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

    # ── CRUD ──────────────────────────────────────────────

    def insert(self, table: str, data: dict | list[dict], on_conflict: Optional[str] = None) -> list[dict]:
        """Insert row(s). Returns inserted rows."""
        params = {}
        if on_conflict:
            params["on_conflict"] = on_conflict
        resp = self._client.post(f"/{table}", json=data, params=params)
        return self._handle(resp)

    def select(self, table: str, columns: str = "*", **filters) -> list[dict]:
        """Select rows. Pass column=value for eq filters, or use PostgREST syntax."""
        params = {"select": columns}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        resp = self._client.get(f"/{table}", params=params)
        return self._handle(resp)

    def update(self, table: str, data: dict, **filters) -> list[dict]:
        """Update rows matching filters. Returns updated rows."""
        params = {}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        resp = self._client.patch(f"/{table}", json=data, params=params)
        return self._handle(resp)

    def delete(self, table: str, **filters) -> list[dict]:
        """Delete rows matching filters. Returns deleted rows."""
        params = {}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        resp = self._client.delete(f"/{table}", params=params)
        return self._handle(resp)

    def upsert(self, table: str, data: dict | list[dict], on_conflict: str) -> list[dict]:
        """Upsert (insert or update on conflict)."""
        headers = {**self.headers, "Prefer": "return=representation,resolution=merge-duplicates"}
        params = {"on_conflict": on_conflict}
        resp = self._client.post(f"/{table}", json=data, params=params, headers=headers)
        return self._handle(resp)

    # ── Raw SQL (via /rest/v1/rpc won't work; use Management API) ──

    def execute_sql(self, sql: str) -> dict:
        """Execute raw SQL via Supabase SQL endpoint (requires service role key)."""
        # Supabase doesn't expose a public SQL endpoint via PostgREST.
        # We use the pg REST API workaround or the management API.
        # For init, we'll use the /rest/v1/ with a custom RPC function,
        # but simpler: just use the Supabase SQL API if available.
        # Fallback: use httpx to call the Supabase platform API.
        url = f"{self.base_url}/rest/v1/"
        # Actually, the simplest way is to use supabase-py or direct pg connection.
        # For this minimal client, we'll raise - use init script with supabase-py instead.
        raise SupabaseError("execute_sql not supported via REST. Use init script with direct SQL.")

    # ── Internal ──────────────────────────────────────────

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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Module-level singleton
_client: Optional[SupabaseClient] = None


def get_client() -> SupabaseClient:
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client
