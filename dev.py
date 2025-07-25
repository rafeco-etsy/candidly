#!/usr/bin/env python3
"""
Development helper script for Candidly.
Ensures database is properly set up and starts the development server.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        return False

def ensure_database():
    """Ensure database exists and is up to date."""
    instance_dir = Path("instance")
    db_file = instance_dir / "candidly.db"
    
    # Create instance directory if it doesn't exist
    instance_dir.mkdir(exist_ok=True)
    
    # Check if migration directory exists
    if not Path("migrations").exists():
        print("🔧 Initializing database migrations...")
        if not run_command("flask db init", "Initialize Flask-Migrate"):
            return False
    
    # Check if we need to create initial migration
    versions_dir = Path("migrations/versions")
    if not versions_dir.exists() or not list(versions_dir.glob("*.py")):
        print("🔧 Creating initial migration...")
        if not run_command("flask db migrate -m 'Initial migration'", "Create migration"):
            return False
    
    # Apply migrations
    if not run_command("flask db upgrade", "Apply database migrations"):
        return False
    
    # Verify database tables exist
    if db_file.exists():
        result = subprocess.run(
            f'sqlite3 {db_file} ".tables"', 
            shell=True, capture_output=True, text=True
        )
        if "feedback_template" in result.stdout:
            print("✅ Database is ready!")
            return True
        else:
            print("⚠️  Database exists but missing tables. Recreating...")
            db_file.unlink()
            return ensure_database()
    
    return True

def main():
    """Main development setup and server start."""
    print("🚀 Candidly Development Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Error: Please run this script from the candidly project root directory")
        sys.exit(1)
    
    # Check for .env file
    if not Path(".env").exists():
        print("⚠️  No .env file found. Create one with:")
        print("   echo 'OPENAI_API_KEY=your-key-here' > .env")
        print("   (The app will work with fallback responses without the API key)")
    
    # Ensure database is set up
    if not ensure_database():
        print("❌ Database setup failed")
        sys.exit(1)
    
    # Start development server
    print("\n🌐 Starting development server...")
    print("   Server will be available at: http://localhost:5001")
    print("   Press Ctrl+C to stop")
    print("-" * 40)
    
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Development server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()