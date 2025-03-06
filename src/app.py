from datetime import datetime

import requests
from rich.prompt import Prompt

from auth import AuthManager
from console_utils import RichOutput
from courses import CourseManager, CourseProcessor
from exceptions import ErrorCodes, GbException


class GbLearningApp:
    def __init__(self, console: RichOutput):
        self.session = requests.Session()
        self.console = console
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
            "Host": "www.hebgb.gov.cn",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def run(self):
        self.auth = AuthManager(self.session, self.console)
        self.current_user = None  # 用户状态跟踪
        self.course_mgr = CourseManager(self.session, self.console)
        self.error_msg = ""  # 错误信息跟踪

        while True:
            choice = self.show_main_menu()
            match choice:
                case "1":  # 选择用户
                    self.handle_user_selection()

                case "2":  # 登录
                    if self.current_user:
                        self.console.warning(f"已登录用户 {self.current_user}")
                        continue
                    if self.auth.login():
                        self.current_user = self.auth.username

                case "3":  # 显示当前用户学习状态
                    if self.check_auth():
                        self.auth.update_user_info()

                case "4":  # browse courses and start learning
                    if not self.check_auth():
                        continue
                    self.handle_course_learning()

                case "5":  # 退出
                    self.console.info("[bold]Bye~")
                    return

                case _:
                    self.console.error("无效输入，请重新选择")

    def show_main_menu(self):
        # self.console.clear()
        self.console.rule("[bold greed]自动学习工具")
        self.console.print(
            f"[bold blink]当前用户: {self.current_user or '未登录'}  ", justify="right"
        )
        self.console.info("# 1. 选择用户")
        self.console.info("# 2. 登录")
        self.console.info("# 3. 显示当前用户学习状态")
        self.console.info("# 4. 浏览课程并开始学习")
        self.console.info("# 5. 退出程序")
        self.console.print()
        if self.error_msg:
            self.console.error(self.error_msg)
            self.error_msg = ""
        return Prompt.ask("请输入选项编号", choices=["1", "2", "3", "4", "5"])

    def check_auth(self):
        if not self.current_user:
            self.error_msg = "# 请先登录！"
            return False
        return True

    def handle_course_learning(self):
        self.console.info("# 正在获取课程信息...")
        courses = self.course_mgr.get_courses()
        if not courses:
            self.console.warning("# 没有可用的课程")
            return

        self.course_mgr.display_courses_table(courses)
        user_input = input("# 请输入要学习的课程编号: 1,2-3/a(all)/q(quit): ")
        selected_courses = self.course_mgr.select_courses(courses, user_input)

        if selected_courses:
            processor = CourseProcessor(
                session=self.session,
                console=self.console,
                course_list=selected_courses,
            )
            processor.start_learning()

    # 示例保留的占位方法（后续可扩展）
    def handle_user_selection(self):
        # TODO: 实现多用户选择逻辑
        self.error_msg = "# 用户选择功能开发中，当前仅支持单用户"
