import atexit
import threading

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console()

_progress = None
_lock = threading.Lock()


def _get_progress():
    global _progress
    if _progress is None:
        with _lock:
            if _progress is None:
                _progress = Progress(
                    SpinnerColumn(spinner_name="dots"),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(bar_width=32),
                    TaskProgressColumn(),
                    TextColumn("·"),
                    TransferSpeedColumn(),
                    TextColumn("·"),
                    TimeRemainingColumn(),
                    console=console,
                    expand=False,
                    transient=False,
                    speed_estimate_period=10.0,
                )
                _progress.start()
                atexit.register(_progress.stop)
    return _progress


def print_line(*args, **kwargs):
    console.print(*args, **kwargs)


class ProgressBar:
    def __init__(self, total, desc, position=None, unit=None, unit_scale=False):
        self.task_id = _get_progress().add_task(desc, total=total)
        self.total = total

    def set_total(self, total):
        if total:
            self.total = total
            _get_progress().update(self.task_id, total=total)

    def update_to(self, value):
        _get_progress().update(self.task_id, completed=value)

    def close(self):
        progress = _get_progress()
        if self.total is not None:
            progress.update(self.task_id, completed=self.total, refresh=True)
        progress.remove_task(self.task_id)
