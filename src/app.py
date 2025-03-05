from datetime import datetime

import requests

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
        self.console.info("# --------------------------------------------------")
        self.console.info(f"# 程序启动")

        auth = AuthManager(self.session, self.console)
        auth.login()

        course_mgr = CourseManager(self.session, self.console)
        courses = course_mgr.get_courses()

        if courses:
            course_mgr.display_courses_table(courses)

            self.console.info(
                "请输入要学习的课程编号，多个课程编号用逗号隔开，可使用范围表示法，如1-3。全部选择请直接输入all。",
                end="",
            )
            selected_courses = course_mgr.select_courses(courses)

            if not selected_courses:
                self.console.warning("未选择任何课程，程序退出。")
            else:
                processor = CourseProcessor(
                    session=self.session,
                    console=self.console,
                    course_list=selected_courses,
                )
                processor.start_learning()
