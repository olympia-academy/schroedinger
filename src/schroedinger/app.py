"""Launch the optional local browser app: python -m schroedinger.app."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def entrypoint(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--no-browser", action="store_true", help="Start without opening a browser")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if importlib.util.find_spec("streamlit") is None:
        parser.error('Appen trenger Python 3.11+ og app-tillegget: python -m pip install -e ".[app]"')
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    command = [sys.executable, "-m", "streamlit", "run", str(Path(__file__).with_name("web_app.py")),
               "--server.address=127.0.0.1", f"--server.port={args.port}",
               f"--server.headless={'true' if args.no_browser else 'false'}",
               "--browser.gatherUsageStats=false"]
    print(f"Schrödinger-lab: http://127.0.0.1:{args.port} — stopp med Ctrl+C", flush=True)
    try:
        return subprocess.call(command, env=env)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(entrypoint())
