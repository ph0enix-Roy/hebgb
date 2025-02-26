from bs4 import BeautifulSoup
import re
import ffmpeg
import time
from rich.progress import track
from rich.table import Table
from rich import box

from exceptions import GbException
from console_utils import RichOutput


class CourseManager:

    COURSE_URL = (
        f"https://www.hebgb.gov.cn/student/course_myselect.do?searchType=2&menu=course"
    )

    def __init__(self, session, console):
        self.session = session
        self.console = console

    def get_courses(self):
        """获取用户已报名课程，并返回课程列表

        Returns:
            list: 已报名课程列表
        """
        response = self.session.get(self.COURSE_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_courses(soup)

    def _parse_courses(self, soup):
        """解析课程页面"""
        courses = []
        for row in soup.find_all("div", class_="hoz_course_row"):
            course = {
                "coursename": self._clean_text(row.find("h2").text),
                "courseid": self._extract_course_id(row),
                "chapterid": self._extract_chapter_id(row),
                "duration": self._get_duration(row),
            }
            courses.append(course)
        return courses

    def _clean_text(self, text):
        """清理课程名称中的多余字符"""
        return text.strip().replace("\n", "").replace(" ", "")

    def _extract_course_id(self, row):
        """提取课程ID"""
        button = row.find("input", type="button", onclick=True)
        if not button:
            return ""
        match = re.search(r"addUrl\((\d+)", button["onclick"])
        return match.group(1) if match else ""

    def _extract_chapter_id(self, row):
        """提取章节ID"""
        div = row.find("div", class_="hoz_c_lf lf")
        if not div:
            return ""
        match = re.search(r"courseId=(\d+)", div["onclick"])
        return match.group(1) if match else ""

    def _get_duration(self, row):
        """提取课程时长"""
        duration_span = row.find("span", title="课程时长")
        if duration_span:
            return duration_span.get_text(strip=True)
        return "0"

    def display_courses_table(self, courses):
        """在控制台输出已报名的课程信息

        Args:
            courses (list): 课程列表对象
        """
        table = Table(
            title="已报名的课程信息",
            box=box.MARKDOWN,
        )
        table.add_column("序号", justify="center", style="cyan")
        table.add_column("课程标题", justify="left", style="cyan")
        table.add_column("课程代码", justify="center", style="cyan")
        table.add_column("章节代码", justify="center", style="cyan")
        table.add_column("课程时长", justify="center", style="cyan")
        i = 0
        for course in courses:
            i += 1
            table.add_row(
                str(i),
                course["coursename"],
                course["courseid"],
                course["chapterid"],
                course["duration"],
            )
        self.console.print(table)


class CourseProcessor:
    def __init__(self, session, console, course_id, chapter_id):
        self.session = session
        self.console = console
        self.course_id = course_id
        self.chapter_id = chapter_id

    def start_learning(self):
        duration = self._get_video_duration()
        self._simulate_learning(duration)

    def _get_video_duration(self):
        # 封装视频时长获取逻辑
        probe = ffmpeg.probe(self._get_video_url())
        return self._parse_duration(probe)

    def _simulate_learning(self, duration):
        # 封装学习进度模拟
        for _ in track(range(self._calculate_study_time(duration))):
            self._send_learning_progress()
            time.sleep(1)
