import sys
from pathlib import Path


def main():
    # Add the src directory to the Python path so modules can be imported
    src_dir = Path(__file__).parent.parent.parent.resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Import the module after path is set
    from app.gmail_watcher import main as gmail_watcher_main
    gmail_watcher_main()


if __name__ == "__main__":
    main()