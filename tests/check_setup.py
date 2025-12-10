#!/usr/bin/env python3
"""
NOC Config Maker - Setup Checker
Validates that everything is configured correctly before running
"""

import sys
import os
import subprocess

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required (you have {}.{}.{})".format(version.major, version.minor, version.micro))
        return False
    print("✅ Python {}.{}.{} - OK".format(version.major, version.minor, version.micro))
    return True

def check_pip_packages():
    """Check if required packages are installed"""
    required = ['flask', 'flask_cors', 'openai']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package} - installed")
        except ImportError:
            print(f"❌ {package} - NOT installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    return True

def check_api_key():
    """Check if OpenAI API key is configured"""
    # Check environment variable
    api_key = os.getenv('OPENAI_API_KEY', '')
    
    if api_key:
        print(f"✅ OPENAI_API_KEY environment variable set")
        print(f"   Key preview: {api_key[:15]}...{api_key[-4:]}")
        return True
    
    # Check .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            content = f.read()
            if 'OPENAI_API_KEY' in content:
                print("✅ OPENAI_API_KEY found in .env file")
                return True
    
    print("❌ OPENAI_API_KEY not configured")
    print("\nTo fix:")
    print("  Option 1: export OPENAI_API_KEY='your-key-here'")
    print("  Option 2: Create .env file with: OPENAI_API_KEY=your-key-here")
    return False

def check_files():
    """Check if required files exist"""
    files = [
        'api_server.py',
        'NOC-configMaker.html',
        'requirements.txt'
    ]
    
    all_exist = True
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file} - exists")
        else:
            print(f"❌ {file} - NOT FOUND")
            all_exist = False
    
    return all_exist

def test_api_server():
    """Test if we can start the API server (doesn't actually start it)"""
    try:
        with open('api_server.py', 'r') as f:
            content = f.read()
            if 'Flask' in content and 'openai' in content:
                print("✅ api_server.py looks valid")
                return True
    except Exception as e:
        print(f"❌ Error reading api_server.py: {e}")
        return False

def main():
    print("="*60)
    print("🔍 NOC Config Maker - Setup Checker")
    print("="*60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_pip_packages),
        ("API Key Configuration", check_api_key),
        ("Required Files", check_files),
        ("API Server Validation", test_api_server)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking: {name}")
        print("-" * 60)
        results.append(check_func())
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\n🚀 You're ready to start!")
        print("\nNext steps:")
        print("  1. python api_server.py")
        print("  2. Open NOC-configMaker.html in browser")
        return 0
    else:
        print(f"⚠️  {total - passed} checks failed ({passed}/{total} passed)")
        print("\n🔧 Please fix the issues above before continuing.")
        return 1

if __name__ == '__main__':
    exit(main())

