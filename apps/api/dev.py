"""Run app processes; terminate their process groups on exit or failure."""

import os
from pathlib import Path
import signal
import subprocess
import time


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    processes: list[subprocess.Popen] = []

    def stop(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        for command, cwd in [
            (["uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1"], root / "apps/api"),
            (["npm", "run", "dev"], root / "apps/web"),
        ]:
            processes.append(subprocess.Popen(command, cwd=cwd, start_new_session=True))
        while True:
            for process in processes:
                if process.poll() is not None:
                    return process.returncode or 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
