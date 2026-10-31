"""One local worker at a time, with explicit cancellation and bounded lifetime."""
import atexit
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from time import monotonic
from uuid import uuid4

from .app_model import read_result


class JobManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = self.directory = self.log = self.identifier = None
        atexit.register(self.close)

    def _clear(self):
        if self.log:
            self.log.close()
        if self.directory:
            self.directory.cleanup()
        self.process = self.directory = self.log = self.identifier = None

    def start(self, experiment):
        experiment.configuration()
        with self.lock:
            if self.process and self.process.poll() is None:
                raise ValueError("En beregning kjører allerede. Vent eller avbryt den i fanen som startet den.")
            self._clear()
            self.directory = tempfile.TemporaryDirectory(prefix="olympia-schroedinger-")
            path = Path(self.directory.name)
            (path/"request.json").write_text(json.dumps({"schema_version": 1, "experiment": asdict(experiment)}), encoding="utf-8")
            self.log = (path/"worker.log").open("wb")
            env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                       MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", MPLBACKEND="Agg")
            try:
                self.process = subprocess.Popen(
                    [sys.executable, "-m", "schroedinger.app_worker", str(path)],
                    stdout=self.log, stderr=subprocess.STDOUT, env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            except Exception:
                self._clear()
                raise
            self.identifier = uuid4().hex
            self.started = monotonic()
            return self.identifier

    def status(self, identifier):
        with self.lock:
            if identifier != self.identifier or not self.process:
                return {"status": "expired", "message": "Denne kjøringen er ikke lenger tilgjengelig. Start på nytt."}
            if self.process.poll() is None:
                return {"status": "running", "seconds": monotonic()-self.started}
            status = Path(self.directory.name)/"status.json"
            if status.exists():
                return json.loads(status.read_text(encoding="utf-8"))
            return {"status": "error", "message": f"Beregningsprosessen stoppet med kode {self.process.returncode}."}

    def collect(self, identifier):
        with self.lock:
            if identifier != self.identifier or not self.process or self.process.poll() is None:
                raise ValueError("Resultatet er ikke klart.")
            run = read_result(Path(self.directory.name)/"result.npz")
            self._clear()
            return run

    def cancel(self, identifier):
        with self.lock:
            if identifier != self.identifier:
                return
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self._clear()

    def busy(self):
        with self.lock:
            return bool(self.process and self.process.poll() is None)

    def close(self):
        self.cancel(self.identifier)
