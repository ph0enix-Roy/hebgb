from console_utils import RichOutput
from app import GbLearningApp


if __name__ == "__main__":
    rich_console = RichOutput()
    try:
        app = GbLearningApp(console=rich_console)
        app.run()
    except Exception as e:
        # Console().print(f"[bold red]程序异常终止: {str(e)}")
        raise e
