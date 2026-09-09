#!/usr/bin/env python3
"""
Test the Supabase REST client by creating and querying a test user.

Run this AFTER initializing the schema via Supabase Dashboard SQL Editor.

Usage:
    export SUPABASE_URL=https://zxgzbwjipwhmcznuxrvu.supabase.co
    export SUPABASE_SECRET_KEY=sb_secret_...
    python scripts/test_supabase_client.py
"""
import os
import sys
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.supabase_client import SupabaseClient, SupabaseError


def test_client():
    print("=" * 70)
    print("Supabase REST Client Test")
    print("=" * 70)
    print()

    # Initialize client
    try:
        client = SupabaseClient()
        print("✓ Client initialized successfully")
    except SupabaseError as e:
        print(f"✗ Failed to initialize client: {e}")
        sys.exit(1)

    # Test 1: Insert a test user
    print("\n[Test 1] Creating test user...")
    test_user = {
        "id": str(uuid.uuid4()),
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "name": "Test User",
        "password_hash": "hashed_password_123",
        "push_enabled": True,
        "push_frequency": "daily",
        "push_time": "09:00",
        "push_count": 10,
    }

    try:
        result = client.insert("users", test_user)
        print(f"✓ User created: {result[0]['id']}")
        user_id = result[0]["id"]
    except SupabaseError as e:
        print(f"✗ Failed to create user: {e}")
        print("\nHint: Make sure the schema is initialized via Supabase Dashboard SQL Editor")
        print("Run: python scripts/init_supabase.py")
        sys.exit(1)

    # Test 2: Select the user
    print("\n[Test 2] Retrieving user...")
    try:
        users = client.select("users", id=user_id)
        if users:
            print(f"✓ User retrieved: {users[0]['email']}")
            print(f"  - Name: {users[0]['name']}")
            print(f"  - Push frequency: {users[0]['push_frequency']}")
        else:
            print("✗ User not found")
            sys.exit(1)
    except SupabaseError as e:
        print(f"✗ Failed to retrieve user: {e}")
        sys.exit(1)

    # Test 3: Update the user
    print("\n[Test 3] Updating user...")
    try:
        updated = client.update("users", {"name": "Updated Test User", "push_count": 20}, id=user_id)
        print(f"✓ User updated: {updated[0]['name']}, push_count={updated[0]['push_count']}")
    except SupabaseError as e:
        print(f"✗ Failed to update user: {e}")
        sys.exit(1)

    # Test 4: Delete the user
    print("\n[Test 4] Deleting user...")
    try:
        deleted = client.delete("users", id=user_id)
        print(f"✓ User deleted: {deleted[0]['id']}")
    except SupabaseError as e:
        print(f"✗ Failed to delete user: {e}")
        sys.exit(1)

    # Test 5: Verify deletion
    print("\n[Test 5] Verifying deletion...")
    try:
        users = client.select("users", id=user_id)
        if not users:
            print("✓ User successfully removed from database")
        else:
            print("✗ User still exists after deletion")
            sys.exit(1)
    except SupabaseError as e:
        print(f"✗ Failed to verify deletion: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✓ All tests passed!")
    print("=" * 70)

    client.close()


if __name__ == "__main__":
    test_client()
