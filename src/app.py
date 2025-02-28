from auth import AuthManager
from courses import CourseManager
from exceptions import GbException, ErrorCodes
from console_utils import RichOutput
import requests
from datetime import datetime


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
        self.console.info(
            f"# 程序启动，时间戳：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        try:
            auth = AuthManager(self.session, self.console)
            auth.login()

            course_mgr = CourseManager(self.session, self.console)
            courses = course_mgr.get_courses()

            if courses:
                course_mgr.display_courses_table(courses)
                # self.process_learning(courses[0])

        except GbException as e:
            self.console.error(f"! 错误代码 {e.code}: {e.message}")
            exit(e.code)

    """def process_learning(self, course):
        processor = CourseProcessor(
            session=self.session,
            console=self.console,
            course_id=course["courseid"],
            chapter_id=course["chapterid"],
        )
        processor.start_learning()"""
