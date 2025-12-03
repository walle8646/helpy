#!/usr/bin/env python3
"""Script per applicare la migration updated_at a configuration_property"""

import sqlite3
import sys

DB_PATH = '/app/helpy.db'

def apply_migration():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(configuration_property)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'updated_at' in columns:
            print("✅ Colonna updated_at già esiste!")
            conn.close()
            return True
        
        print("🔄 Aggiungendo colonna updated_at...")
        
        # Add the column
        cursor.execute("ALTER TABLE configuration_property ADD COLUMN updated_at DATETIME NULL")
        
        # Update existing rows
        cursor.execute("UPDATE configuration_property SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        
        conn.commit()
        conn.close()
        
        print("✅ Migration completata con successo!")
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la migration: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
