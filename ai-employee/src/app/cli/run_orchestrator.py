import sys
from pathlib import Path

def main():
    # Add the src directory to the Python path so modules can be imported
    src_dir = Path(__file__).parent.parent.parent.resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Import the module after path is set
    from app.orchestrator import run_orchestrator_loop
    run_orchestrator_loop()

if __name__ == "__main__":
    main()