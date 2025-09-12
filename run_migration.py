#!/usr/bin/env python3
"""
Script to run database migration for MyNewsletters app.
"""

import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def run_migration():
    """Run the database migration."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    # Read migration SQL
    migration_path = Path(__file__).parent / "backend" / "migrations" / "004_correct_schema.sql"
    with open(migration_path, "r") as f:
        migration_sql = f.read()
    
    print("Connecting to database...")
    
    # Connect to database
    conn = await asyncpg.connect(database_url)
    
    try:
        print("Running migration...")
        # Run migration
        await conn.execute(migration_sql)
        print("Migration completed successfully!")
        
        # Verify tables were created
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table['tablename']}")
            
    except Exception as e:
        print(f"Error running migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())