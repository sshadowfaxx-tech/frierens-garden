import os
import re
import shutil
import sys

def fix_postgresql_config():
    """Fix the corrupted postgresql.conf file"""
    
    # Common PostgreSQL paths on Windows
    possible_paths = [
        r"C:\Program Files\PostgreSQL\16\data\postgresql.conf",
        r"C:\ProgramData\PostgreSQL\16\data\postgresql.conf",
    ]
    
    pg_conf_path = None
    for path in possible_paths:
        if os.path.exists(path):
            pg_conf_path = path
            break
    
    if not pg_conf_path:
        print("❌ Could not find postgresql.conf")
        print("Please manually edit the file and add a newline between 'port = 5432' and 'max_connections = 200'")
        return False
    
    print(f"🔧 Found config at: {pg_conf_path}")
    
    # Read the file
    with open(pg_conf_path, 'r') as f:
        content = f.read()
    
    # Check if the corruption exists
    if 'port = 5432max_connections' in content:
        print("🔍 Found corrupted line (missing newline)")
        
        # Create backup
        backup_path = pg_conf_path + '.backup.' + str(int(os.time()))
        shutil.copy2(pg_conf_path, backup_path)
        print(f"💾 Backup created: {backup_path}")
        
        # Fix the corruption - add newline between port and max_connections
        fixed_content = content.replace(
            'port = 5432max_connections = 200',
            'port = 5432\nmax_connections = 200'
        )
        
        # Write fixed content
        with open(pg_conf_path, 'w') as f:
            f.write(fixed_content)
        
        print("✅ Fixed! Added newline between port and max_connections")
        return True
    else:
        print("ℹ️ Config looks OK, no corruption found")
        return True

if __name__ == "__main__":
    if fix_postgresql_config():
        print("\n📋 Next steps:")
        print("  1. Start PostgreSQL: net start postgresql-x64-16")
        print("  2. Run the tracker: batch")
    else:
        sys.exit(1)
    
    input("\nPress Enter to exit...")
