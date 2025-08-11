#!/usr/bin/env python3
"""
Database migration runner for My Newsletters Voice Assistant
Executes SQL migration files in order
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MigrationRunner:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent
        
    async def get_connection(self) -> asyncpg.Connection:
        """Create database connection"""
        return await asyncpg.connect(self.database_url)
    
    async def create_migrations_table(self, conn: asyncpg.Connection):
        """Create migrations tracking table"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def get_executed_migrations(self, conn: asyncpg.Connection) -> List[str]:
        """Get list of already executed migrations"""
        rows = await conn.fetch("SELECT filename FROM schema_migrations ORDER BY filename")
        return [row['filename'] for row in rows]
    
    def get_migration_files(self) -> List[Path]:
        """Get all SQL migration files in order"""
        files = sorted(self.migrations_dir.glob("*.sql"))
        return [f for f in files if f.name[0].isdigit()]
    
    async def execute_migration(self, conn: asyncpg.Connection, filepath: Path):
        """Execute a single migration file"""
        print(f"Executing migration: {filepath.name}")
        
        with open(filepath, 'r') as f:
            sql = f.read()
        
        # Execute migration in transaction
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES ($1)",
                filepath.name
            )
        
        print(f"✓ Completed: {filepath.name}")
    
    async def run_migrations(self, target: Optional[str] = None):
        """Run all pending migrations"""
        conn = await self.get_connection()
        
        try:
            # Create migrations table
            await self.create_migrations_table(conn)
            
            # Get executed migrations
            executed = await self.get_executed_migrations(conn)
            
            # Get migration files
            migration_files = self.get_migration_files()
            
            # Filter pending migrations
            pending = [f for f in migration_files if f.name not in executed]
            
            if not pending:
                print("No pending migrations")
                return
            
            # Apply target filter if specified
            if target:
                pending = [f for f in pending if f.name <= target]
            
            print(f"Found {len(pending)} pending migration(s)")
            
            # Execute migrations
            for filepath in pending:
                await self.execute_migration(conn, filepath)
            
            print(f"\n✅ Successfully executed {len(pending)} migration(s)")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            await conn.close()
    
    async def rollback_migration(self, migration_name: str):
        """Rollback a specific migration (if rollback file exists)"""
        rollback_file = self.migrations_dir / f"rollback_{migration_name}"
        
        if not rollback_file.exists():
            print(f"No rollback file found for {migration_name}")
            return
        
        conn = await self.get_connection()
        
        try:
            print(f"Rolling back: {migration_name}")
            
            with open(rollback_file, 'r') as f:
                sql = f.read()
            
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE filename = $1",
                    migration_name
                )
            
            print(f"✓ Rolled back: {migration_name}")
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            await conn.close()
    
    async def status(self):
        """Show migration status"""
        conn = await self.get_connection()
        
        try:
            await self.create_migrations_table(conn)
            
            executed = await self.get_executed_migrations(conn)
            all_files = [f.name for f in self.get_migration_files()]
            
            print("Migration Status:")
            print("-" * 50)
            
            for filename in all_files:
                status = "✓" if filename in executed else "○"
                print(f"{status} {filename}")
            
            pending_count = len(all_files) - len(executed)
            print("-" * 50)
            print(f"Total: {len(all_files)} | Executed: {len(executed)} | Pending: {pending_count}")
            
        finally:
            await conn.close()


async def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument("command", choices=["migrate", "rollback", "status"],
                      help="Command to execute")
    parser.add_argument("--target", help="Target migration (for migrate/rollback)")
    parser.add_argument("--database-url", help="Override database URL")
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    
    runner = MigrationRunner(database_url)
    
    if args.command == "migrate":
        await runner.run_migrations(args.target)
    elif args.command == "rollback":
        if not args.target:
            print("Error: --target required for rollback", file=sys.stderr)
            sys.exit(1)
        await runner.rollback_migration(args.target)
    elif args.command == "status":
        await runner.status()


if __name__ == "__main__":
    asyncio.run(main())