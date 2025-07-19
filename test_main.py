"""
Test Railway Entry Point - Minimal Version
"""
import os

def test_imports():
    """Test if all imports work."""
    try:
        print("Testing FastAPI import...")
        from fastapi import FastAPI
        print("✅ FastAPI imported successfully")
        
        print("Testing app import...")
        from main_fixed import app
        print("✅ App imported successfully")
        
        print("Testing config...")
        from app.core.config import settings
        print(f"✅ Config loaded - Environment: {settings.environment}")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing minimal Railway deployment")
    print(f"Python version: {os.sys.version}")
    print(f"PORT: {os.environ.get('PORT', '8000')}")
    
    if test_imports():
        print("✅ All imports successful - starting server without migrations...")
        port = os.environ.get("PORT", "8000")
        
        import subprocess
        subprocess.run([
            "uvicorn", 
            "main_fixed:app", 
            "--host", "0.0.0.0", 
            "--port", port,
            "--log-level", "debug"
        ])
    else:
        print("❌ Import test failed")
        exit(1) 