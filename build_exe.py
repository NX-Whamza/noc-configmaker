#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script to create executable for NOC Config Maker
Uses PyInstaller to bundle backend, frontend, and dependencies
"""
import os
import sys
import subprocess
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_exe():
    """Build the executable with unified backend"""
    script_dir = Path(__file__).parent
    
    print("=" * 70)
    print("NOC Config Maker - Unified Backend Builder")
    print("=" * 70)
    print()
    print("Building single executable with integrated backend...")
    print()
    
    # Check PyInstaller
    if not check_pyinstaller():
        print("Installing PyInstaller...")
        install_pyinstaller()
        print()
    
    # Determine path separator for PyInstaller
    if sys.platform == 'win32':
        sep = ';'
    else:
        sep = ':'
    
    # Build PyInstaller command with clean, minimal imports
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=NOC-ConfigMaker",
        "--onefile",
        "--console",  # Keep console for backend logs
        "--clean",  # Clean PyInstaller cache before building
        
        # Data files (IMPORTANT: secure_data is NOT bundled - it stays separate for data persistence)
        f"--add-data=NOC-configMaker.html{sep}.",
        f"--add-data=login.html{sep}.",
        f"--add-data=change-password.html{sep}.",
        f"--add-data=config_policies{sep}config_policies",
        f"--add-data=nextlink_standards.py{sep}.",
        f"--add-data=nextlink_enterprise_reference.py{sep}.",
        f"--add-data=nextlink_compliance_reference.py{sep}.",
        # NOTE: secure_data/ folder is intentionally NOT included here
        # This ensures SQLite databases persist across EXE updates
        
        # Core dependencies (explicitly include everything needed)
        "--hidden-import=flask",
        "--hidden-import=flask_cors",
        "--hidden-import=werkzeug",
        "--hidden-import=werkzeug.serving",
        "--hidden-import=requests",
        "--hidden-import=sqlite3",
        "--hidden-import=smtplib",
        "--hidden-import=email",
        "--hidden-import=email.mime",
        "--hidden-import=email.mime.text",
        "--hidden-import=email.mime.multipart",
        
        # Our modules (unified backend structure)
        "--hidden-import=api_server",
        "--hidden-import=nextlink_standards",
        "--hidden-import=nextlink_enterprise_reference",
        "--hidden-import=nextlink_compliance_reference",
        
        # Authentication modules (standard library, but explicit for clarity)
        "--hidden-import=hashlib",
        "--hidden-import=secrets",
        "--hidden-import=base64",
        "--hidden-import=json",
        
        # JWT support (optional - will work without PyJWT using fallback)
        "--hidden-import=jwt",
        "--hidden-import=jwt.algorithms",
        
        # Collect Flask and Werkzeug completely
        "--collect-all=flask",
        "--collect-all=werkzeug",
        
        # Entry point
        "launcher.py"
    ]
    
    print("Building executable...")
    print("This may take several minutes...")
    print()
    
    # Write build start time to file for verification
    import datetime
    with open('build_start.txt', 'w') as f:
        f.write(f"Build started at: {datetime.datetime.now()}\n")
    
    try:
        # Run with real-time output
        process = subprocess.Popen(cmd, cwd=script_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        # Stream output
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        print()
        print("=" * 70)
        print("Build successful!")
        print("=" * 70)
        print()
        print(f"Executable location: {script_dir / 'dist' / 'NOC-ConfigMaker.exe'}")
        print()
        print("You can now distribute this .exe file to users.")
        print("They can run it without installing Python or dependencies.")
        print()
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 70)
        print("Build failed!")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        return False
    
    return True

if __name__ == '__main__':
    build_exe()

