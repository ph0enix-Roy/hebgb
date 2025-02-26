from rich.console import Console


class RichOutput(Console):  # 继承Console类
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def info(self, message, end="\n"):
        self.print(f"[blue]{message}", end=end)

    def warning(self, message, end="\n"):
        self.print(f"[yellow]{message}", end=end)

    def error(self, message, end="\n"):
        self.print(f"[red]{message}", end=end)

    def status(self, message, end="\n"):
        self.print(f"[gray]{message}", end=end)
