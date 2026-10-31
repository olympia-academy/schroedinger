"""Compatibility entry point: python main.py [options]."""
import sys
from schroedinger.cli import main as run

def main(argv=None):
    return run(["--dimension", "2", *(sys.argv[1:] if argv is None else argv)])

if __name__ == "__main__":
    main()
