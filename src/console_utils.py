from rich.console import Console
from datetime import datetime
from rich.progress import (
    Progress,
    BarColumn,
    TimeRemainingColumn,
    SpinnerColumn,
    TimeElapsedColumn,
)


class RichOutput(Console):  # 继承Console类
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def info(self, message, end="\n"):
        self.print(f"[blue][{datetime.now().strftime('%H:%M:%S')}] {message}", end=end)

    def warning(self, message, end="\n"):
        self.print(
            f"[yellow][{datetime.now().strftime('%H:%M:%S')}] {message}", end=end
        )

    def error(self, message, end="\n"):
        self.print(f"[red][{datetime.now().strftime('%H:%M:%S')}] {message}", end=end)

    def status(self, message, end="\n"):
        self.print(f"[green][{datetime.now().strftime('%H:%M:%S')}] {message}", end=end)

    def create_progress(self):
        return Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(bar_width=50),
            "[progress.percentage]{task.percentage:>3.0f}%",  # 新增百分比显示
            TimeElapsedColumn(),
            TimeRemainingColumn(),  # 新增剩余时间
            transient=True,
            console=self,
            refresh_per_second=10,
        )
