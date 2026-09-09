# Supabase REST API Data Layer

This module provides a REST API client for Supabase, replacing the SQLAlchemy/SQLite implementation to avoid Render's persistent disk issues.

## Files Created

1. **`app/core/supabase_client.py`** - HTTP client using httpx
   - CRUD operations: insert, select, update, delete, upsert
   - Authentication with service role key
   - Error handling via SupabaseError exception

2. **`supabase_schema.sql`** - PostgreSQL DDL for all tables
   - users, topics, papers, chats, messages, notifications, user_papers
   - Proper foreign keys, indexes, and constraints
   - JSONB columns for arrays (keywords, authors, etc.)

3. **`scripts/init_supabase.py`** - Schema initialization helper
   - Validates Supabase connection
   - Checks if tables exist
   - Provides instructions for manual initialization

4. **`scripts/test_supabase_client.py`** - Client test script
   - Tests all CRUD operations
   - Creates, retrieves, updates, and deletes a test user

## Setup Instructions

### 1. Environment Variables

Add to your `.env` file:

```bash
SUPABASE_URL=https://zxgzbwjipwhmcznuxrvu.supabase.co
SUPABASE_SECRET_KEY=your_supabase_secret_key_here
```

### 2. Initialize Schema

Supabase REST API does not support executing arbitrary SQL. You must initialize the schema manually:

**Option A: Supabase Dashboard (Recommended)**
1. Go to: https://supabase.com/dashboard/project/zxgzbwjipwhmcznuxrvu/sql/new
2. Open `backend/supabase_schema.sql`
3. Copy all contents
4. Paste into the SQL Editor
5. Click "Run" (or Ctrl+Enter)

**Option B: Supabase CLI**
```bash
npx supabase db push --linked
```

### 3. Verify Initialization

```bash
cd backend
source venv/bin/activate
export SUPABASE_URL="https://zxgzbwjipwhmcznuxrvu.supabase.co"
export SUPABASE_SECRET_KEY="your_supabase_secret_key_here"

# Check if tables exist
python scripts/init_supabase.py

# Run tests (requires schema to be initialized)
python scripts/test_supabase_client.py
```

## Usage Example

```python
from app.core.supabase_client import get_client

# Get client instance
client = get_client()

# Insert
user = client.insert("users", {
    "email": "user@example.com",
    "name": "John Doe",
    "password_hash": "hashed_pw",
})

# Select
users = client.select("users", email="user@example.com")

# Update
updated = client.update("users", {"name": "Jane Doe"}, id="uuid-here")

# Delete
deleted = client.delete("users", id="uuid-here")

# Upsert (insert or update on conflict)
client.upsert("users", {"email": "user@example.com", "name": "John"}, on_conflict="email")
```

## Migration Notes

This is a **parallel implementation** - the existing SQLAlchemy code remains unchanged. Future work will:
1. Replace SQLAlchemy models with Supabase client calls
2. Update repository/service layers to use the new client
3. Remove SQLite dependencies

## Dependencies

Added to venv:
- `httpx` - HTTP client for REST API calls
- `psycopg2-binary` - (optional, for future direct DB access if needed)
