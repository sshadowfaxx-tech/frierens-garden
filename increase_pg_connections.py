"""
Increase PostgreSQL max_connections for Windows
Run this as Administrator
"""

import subprocess
import sys
import os

def run_as_admin():
    """Check if running as admin"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    if not run_as_admin():
        print("❌ This script must be run as Administrator")
        print("Right-click Command Prompt and select 'Run as administrator'")
        input("Press Enter to exit...")
        return

    print("🔧 Increasing PostgreSQL max_connections...")
    
    # Path to PostgreSQL config
    pg_config_path = r"C:\Program Files\PostgreSQL\16\data\postgresql.conf"
    
    if not os.path.exists(pg_config_path):
        print(f"❌ Could not find {pg_config_path}")
        print("Please check your PostgreSQL installation path")
        return
    
    # Read current config
    with open(pg_config_path, 'r') as f:
        content = f.read()
    
    # Check if max_connections is already set
    if 'max_connections = 200' in content:
        print("✅ max_connections is already set to 200")
    else:
        # Replace or add max_connections
        import re
        
        # Try to find and replace existing max_connections line
        if 'max_connections' in content:
            content = re.sub(
                r'#?\s*max_connections\s*=\s*\d+',
                'max_connections = 200',
                content
            )
            print("✅ Updated max_connections to 200")
        else:
            # Add it to the end
            content += "\n# Increased for ShadowHunter tracker\nmax_connections = 200\n"
            print("✅ Added max_connections = 200")
        
        # Write back
        with open(pg_config_path, 'w') as f:
            f.write(content)
    
    # Restart PostgreSQL service
    print("🔄 Restarting PostgreSQL service...")
    try:
        subprocess.run(['net', 'stop', 'postgresql-x64-16'], check=False, capture_output=True)
        subprocess.run(['net', 'start', 'postgresql-x64-16'], check=True, capture_output=True)
        print("✅ PostgreSQL restarted successfully")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not restart PostgreSQL automatically: {e}")
        print("Please restart the PostgreSQL service manually:")
        print("  net stop postgresql-x64-16")
        print("  net start postgresql-x64-16")
    
    print("\n✨ Done! Your tracker should now handle more concurrent connections.")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
