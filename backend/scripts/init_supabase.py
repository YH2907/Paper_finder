#!/usr/bin/env python3
"""
Initialize Supabase schema.

For REST API projects, the schema must be executed manually via Supabase Dashboard.
This script provides instructions and validates the connection.

Usage:
    export SUPABASE_URL=https://zxgzbwjipwhmcznuxrvu.supabase.co
    export SUPABASE_SECRET_KEY=sb_secret_...
    python scripts/init_supabase.py
"""
import os
import sys
from pathlib import Path

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zxgzbwjipwhmcznuxrvu.supabase.co")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

SCHEMA_PATH = Path(__file__).parent.parent / "supabase_schema.sql"


def check_connection():
    """Verify Supabase REST API connection."""
    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }
    
    with httpx.Client(timeout=30) as client:
        # Try to access the OpenAPI spec
        resp = client.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
        if resp.status_code == 200:
            print("✓ Supabase REST API connection successful")
            return True
        else:
            print(f"✗ Connection failed: {resp.status_code}")
            return False


def check_tables():
    """Check if tables already exist."""
    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }
    
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/users",
            params={"select": "id", "limit": 1},
            headers=headers
        )
        if resp.status_code == 404:
            print("✗ Tables not found - schema needs to be initialized")
            return False
        elif resp.status_code == 200:
            print("✓ Tables exist - schema already initialized")
            return True
        else:
            print(f"? Unexpected response: {resp.status_code}")
            return None


def init_schema():
    if not SUPABASE_SECRET_KEY:
        print("ERROR: SUPABASE_SECRET_KEY env var is required")
        sys.exit(1)

    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema file not found: {SCHEMA_PATH}")
        sys.exit(1)

    print("=" * 70)
    print("Supabase Schema Initialization")
    print("=" * 70)
    print()
    
    # Check connection
    if not check_connection():
        print("\nFailed to connect to Supabase. Check your credentials.")
        sys.exit(1)
    
    # Check if tables exist
    tables_exist = check_tables()
    
    if tables_exist:
        print("\n✓ Schema is already initialized. Nothing to do.")
        return
    
    print()
    print("=" * 70)
    print("MANUAL INITIALIZATION REQUIRED")
    print("=" * 70)
    print()
    print("Supabase REST API does not support executing arbitrary SQL.")
    print("Please initialize the schema manually:")
    print()
    print("1. Open Supabase Dashboard SQL Editor:")
    print(f"   https://supabase.com/dashboard/project/zxgzbwjipwhmcznuxrvu/sql")
    print()
    print("2. Click 'New query'")
    print()
    print(f"3. Open and copy the contents of: {SCHEMA_PATH}")
    print()
    print("4. Paste into the SQL Editor and click 'Run'")
    print()
    print("=" * 70)
    print()
    print("Schema file preview (first 30 lines):")
    print("-" * 70)
    
    sql = SCHEMA_PATH.read_text()
    lines = sql.split('\n')[:30]
    for line in lines:
        print(line)
    
    if len(sql.split('\n')) > 30:
        print("... (truncated)")
    print("-" * 70)


if __name__ == "__main__":
    init_schema()
