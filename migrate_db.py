"""Database migration script to add request_payload and response_payload columns."""
import sqlite3
import os

DB_PATH = "data/tokenrouter.db"

def migrate():
    """Add new columns to request_logs table."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        print("No migration needed - database will be created with new schema on startup.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(request_logs)")
        columns = [row[1] for row in cursor.fetchall()]
        
        needs_migration = False
        
        # Add request_payload column if it doesn't exist
        if "request_payload" not in columns:
            print("Adding request_payload column...")
            cursor.execute("ALTER TABLE request_logs ADD COLUMN request_payload TEXT")
            needs_migration = True
        else:
            print("✓ request_payload column already exists")
        
        # Add response_payload column if it doesn't exist
        if "response_payload" not in columns:
            print("Adding response_payload column...")
            cursor.execute("ALTER TABLE request_logs ADD COLUMN response_payload TEXT")
            needs_migration = True
        else:
            print("✓ response_payload column already exists")
        
        if needs_migration:
            conn.commit()
            print("\n✅ Migration completed successfully!")
            print("Your existing data has been preserved.")
        else:
            print("\n✅ Database is already up to date!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("TokenRouter Database Migration")
    print("=" * 60)
    print("\nThis will add new columns to store request and response data.\n")
    migrate()
    print("\nYou can now start the application.")
    print("=" * 60)
