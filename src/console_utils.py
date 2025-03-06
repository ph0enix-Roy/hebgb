from datetime import datetime

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


class RichOutput(Console):  # 继承Console类
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def info(self, message, end="\n", **kwargs):
        self.print(
            f"[blue][{datetime.now().strftime('%H:%M:%S')}] {message}",
            end=end,
            **kwargs,
        )

    def warning(self, message, end="\n", **kwargs):
        self.print(
            f"[yellow][{datetime.now().strftime('%H:%M:%S')}] {message}",
            end=end,
            **kwargs,
        )

    def error(self, message, end="\n", **kwargs):
        self.print(
            f"[red][{datetime.now().strftime('%H:%M:%S')}] {message}",
            end=end,
            **kwargs,
        )

    def status(self, message, end="\n", **kwargs):
        self.print(
            f"[green][{datetime.now().strftime('%H:%M:%S')}] {message}",
            end=end,
            **kwargs,
        )

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
