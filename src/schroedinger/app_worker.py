"""Single cancellable simulation process used by the local app."""
import argparse
import json
from pathlib import Path
import traceback
from time import monotonic

from .app_model import Experiment, calculate, write_result


class ProgressReporter:
    """Atomically publish actual steps, at most five times/s plus endpoints."""

    def __init__(self, directory, clock=monotonic):
        self.directory, self.clock = directory, clock
        self.updated = float("-inf")

    def __call__(self, completed, total, stage="computing"):
        now = self.clock()
        if completed not in (0, total) and now-self.updated < 0.2:
            return
        payload = {"completed_steps": completed, "total_steps": total, "stage": stage}
        temporary = self.directory/"progress.tmp"
        try:
            temporary.write_text(json.dumps(payload), encoding="utf-8")
            temporary.replace(self.directory/"progress.json")
        except OSError:
            # A temporarily busy progress file must not interrupt the simulation.
            return
        self.updated = now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        experiment = Experiment.read((args.directory/"request.json").read_text(encoding="utf-8"))
        progress = ProgressReporter(args.directory)
        run = calculate(experiment, progress_callback=progress)
        progress(experiment.steps, experiment.steps, stage="saving")
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
