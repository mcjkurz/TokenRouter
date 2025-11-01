"""Simple script to run TokenRouter."""
import sys
import subprocess

if __name__ == "__main__":
    print("🚀 Starting TokenRouter...")
    print("📦 Make sure you've installed dependencies: pip install -r requirements.txt\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 TokenRouter stopped")
    except Exception as e:
        print(f"\n❌ Error starting TokenRouter: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")

