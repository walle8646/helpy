#!/usr/bin/env python3
"""
Script per applicare le migration al database SQLite
"""
import sqlite3
import sys
from pathlib import Path

# Percorsi
DB_PATH = Path("dev.db")
MIGRATION_FILE = Path("migration_add_is_principal_sqlite.sql")

def apply_migration():
    """Applica la migration al database SQLite"""
    
    if not DB_PATH.exists():
        print(f"❌ Database non trovato: {DB_PATH}")
        return False
    
    if not MIGRATION_FILE.exists():
        print(f"❌ File migration non trovato: {MIGRATION_FILE}")
        return False
    
    try:
        # Leggi il file SQL
        with open(MIGRATION_FILE, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        # Connetti al database
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Abilita foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Esegui gli script SQL
        print(f"🔄 Applicando migration da {MIGRATION_FILE}...")
        cursor.executescript(sql_commands)
        conn.commit()
        
        # Verifica che la colonna sia stata aggiunta
        cursor.execute("PRAGMA table_info(category)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'is_principal' in columns:
            print(f"✅ Migration applicata con successo!")
            print(f"   - Colonna 'is_principal' aggiunta")
            
            # Verifica i dati
            cursor.execute("SELECT COUNT(*) FROM category WHERE is_principal = 1")
            principal_count = cursor.fetchone()[0]
            print(f"   - Categorie principali: {principal_count}")
        else:
            print(f"❌ Errore: colonna 'is_principal' non trovata")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Errore durante l'applicazione della migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
