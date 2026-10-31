"""Single cancellable simulation process used by the local app."""
import argparse
import json
from pathlib import Path
import traceback

from .app_model import Experiment, calculate, write_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        experiment = Experiment.read((args.directory/"request.json").read_text(encoding="utf-8"))
        run = calculate(experiment)
        write_result(run, args.directory/"result.npz")
        (args.directory/"status.json").write_text(json.dumps({"status": "complete"}), encoding="utf-8")
    except Exception as exc:
        (args.directory/"status.json").write_text(
            json.dumps({"status": "error", "message": str(exc)}), encoding="utf-8")
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
