#!/usr/bin/env python3
"""
Main entry point for AI Employee system.
Starts both watcher and orchestrator services.
"""
import os
import sys
import threading
import signal
import time
from pathlib import Path

def start_watcher():
    """Start the filesystem watcher"""
    print("🔄 Starting AI Employee File Watcher...")
    try:
        # Add src to path
        src_dir = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_dir))

        # Set environment
        os.environ.setdefault('PYTHONPATH', str(src_dir))

        from app.cli.run_watcher import main as watcher_main
        watcher_main()
    except KeyboardInterrupt:
        print("🛑 Watcher stopped by user")
    except Exception as e:
        print(f"❌ Watcher error: {e}")
        import traceback
        traceback.print_exc()

def start_orchestrator():
    """Start the orchestrator"""
    print("🔄 Starting AI Employee Orchestrator...")
    try:
        # Add src to path
        src_dir = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_dir))

        # Set environment
        os.environ.setdefault('PYTHONPATH', str(src_dir))

        from app.cli.run_orchestrator import main as orchestrator_main
        orchestrator_main()
    except KeyboardInterrupt:
        print("🛑 Orchestrator stopped by user")
    except Exception as e:
        print(f"❌ Orchestrator error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to start both services"""
    print("🤖 Starting AI Employee System...")
    print("📍 System Location: /mnt/c/AI_Hackthon/")
    print("📋 Available Folders: INBOX, NEEDS_ACTION, PENDING-APPROVAL, APPROVED, REJECTED, PLAN, DONE, LOGS")
    print("📊 Dashboard: /mnt/c/AI_Hackthon/dashboard.md")
    print("")

    # Start both services in separate threads
    watcher_thread = threading.Thread(target=start_watcher, daemon=True)
    orchestrator_thread = threading.Thread(target=start_orchestrator, daemon=True)

    watcher_thread.start()
    print("✅ Watcher service started")

    time.sleep(2)  # Give watcher a moment to start

    orchestrator_thread.start()
    print("✅ Orchestrator service started")

    print("")
    print("🚀 AI Employee System is now running!")
    print("💡 Drop files in /mnt/c/AI_Hackthon/INBOX/ to start the workflow")
    print("📊 Check /mnt/c/AI_Hackthon/dashboard.md for system status")
    print("📝 Logs are available in /mnt/c/AI_Hackthon/LOGS/")
    print("")
    print("Press Ctrl+C to stop the system")
    print("="*60)

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down AI Employee System...")
        print("✅ Services stopped gracefully")
        sys.exit(0)

if __name__ == "__main__":
    main()
