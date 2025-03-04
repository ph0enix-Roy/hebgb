from console_utils import RichOutput
from app import GbLearningApp
from exceptions import GbException, ErrorCodes


if __name__ == "__main__":
    rich_console = RichOutput()
    try:
        app = GbLearningApp(console=rich_console)
        app.run()
    except GbException as e:  # 业务异常
        rich_console.error(f"程序错误 {e.code}: {e.message}")
        exit(e.code)
    except Exception as e:
        # Console().print(f"[bold red]程序异常终止: {str(e)}")
        raise e
        exit(1)
