import os
import re

def find_imports(directory='app'):
    """Trova tutti i file con import errati"""
    wrong_imports = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read()
                        
                        # Cerca import da models_user o models_category
                        if 'models_user' in content or 'models_category' in content:
                            # Trova le righe specifiche
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if 'models_user' in line or 'models_category' in line:
                                    wrong_imports.append({
                                        'file': filepath,
                                        'line': i,
                                        'content': line.strip()
                                    })
                    except Exception as e:
                        print(f"⚠️ Error reading {filepath}: {e}")
    
    return wrong_imports

def fix_imports(directory='app'):
    """Correggi tutti gli import errati"""
    fixed_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original = content
                    
                    # Sostituisci models_user
                    content = re.sub(
                        r'from app\.models_user import',
                        'from app.models import',
                        content
                    )
                    
                    # Sostituisci models_category
                    content = re.sub(
                        r'from app\.models_category import',
                        'from app.models import',
                        content
                    )
                    
                    # Se è cambiato qualcosa, salva
                    if content != original:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        fixed_files.append(filepath)
                        print(f"✅ Fixed: {filepath}")
                
                except Exception as e:
                    print(f"⚠️ Error fixing {filepath}: {e}")
    
    return fixed_files

# Trova tutti gli import errati
imports = find_imports()

if imports:
    print("❌ Trovati import errati:\n")
    for imp in imports:
        print(f"📂 {imp['file']}")
        print(f"   Linea {imp['line']}: {imp['content']}\n")
    print(f"\n🔢 Totale: {len(imports)} import da correggere")
else:
    print("✅ Nessun import errato trovato!")

# Correggi tutti i file
files = fix_imports()

if files:
    print(f"\n🎉 Corretti {len(files)} file!")
else:
    print("\n✅ Nessun file da correggere")