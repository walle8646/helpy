#!/usr/bin/env python3
"""
Script per applicare l'aggiornamento completo delle categorie al database SQLite
"""
import sqlite3
import sys
from pathlib import Path

def apply_full_update():
    """Applica l'aggiornamento completo delle categorie"""
    
    DB_PATH = Path("dev.db")
    SQL_FILE = Path("apply_full_update_sqlite.sql")
    
    if not DB_PATH.exists():
        print(f"❌ Database non trovato: {DB_PATH}")
        return False
    
    if not SQL_FILE.exists():
        print(f"❌ File SQL non trovato: {SQL_FILE}")
        return False
    
    try:
        # Leggi il file SQL
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Connetti al database
        conn = sqlite3.connect(str(DB_PATH))
        conn.isolation_level = None  # Autocommit mode
        cursor = conn.cursor()
        
        print("🔄 Applicando aggiornamento categorie...")
        
        # Esegui gli script SQL
        cursor.executescript(sql_content)
        
        # Verifica i risultati
        cursor.execute("SELECT COUNT(*) FROM category")
        total_categories = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM category WHERE is_principal = 1")
        principal_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM category_hierarchy")
        hierarchy_count = cursor.fetchone()[0]
        
        print(f"✅ Aggiornamento completato!")
        print(f"   - Categorie totali: {total_categories}")
        print(f"   - Categorie principali: {principal_count}")
        print(f"   - Relazioni gerarchia: {hierarchy_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = apply_full_update()
    sys.exit(0 if success else 1)
