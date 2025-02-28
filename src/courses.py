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
        """获取用户已报名课程，并返回包含课程信息的字典列表

        Returns:
            list[dict]: 已报名课程的列表，每个元素是一个包含课程信息的字典。
                dict: 课程信息字典，包含以下字段：
                    - `coursename(str)`: 课程标题
                    - `courseid(str)`: 课程代码
                    - `chapterid(str)`: 章节代码
                    - `duration(str)`: 课程时长
                    - `hour(str)`: 学时
        """
        response = self.session.get(self.COURSE_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_courses(soup)

    def _parse_courses(self, soup):
        """解析课程页面"""
        courses = []
        for row in soup.find_all("div", class_="hoz_course_row"):
            course = {
                "coursename": self._extract_course_name(row),
                "courseid": self._extract_course_id(row),
                "chapterid": self._extract_chapter_id(row),
                "duration": self._extract_course_duration(row),
                "hour": self._extract_course_hour(row),
            }
            courses.append(course)
        return courses

    def _extract_course_name(self, row):
        """提取课程名"""
        return row.find("h2").text.strip().replace("\n", "").replace(" ", "")

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

    def _extract_course_duration(self, row):
        """提取课程时长"""
        duration_span = row.find("span", title="课程时长")
        if duration_span:
            return duration_span.get_text(strip=True)
        return "-"

    def _extract_course_hour(self, row):
        """提取课程学时"""
        hour_span = row.find("span", title="学时")
        if hour_span:
            return hour_span.get_text(strip=True)
        return "-"

    def display_courses_table(self, courses):
        """在控制台输出人类友好的已报名的课程信息

        Args:
            `list[dict]`: 课程信息字典列表对象
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
        table.add_column("学时", justify="center", style="cyan")
        i = 0
        for course in courses:
            i += 1
            table.add_row(
                str(i),
                course["coursename"],
                course["courseid"],
                course["chapterid"],
                course["duration"],
                course["hour"],
            )
        self.console.print(table)


class CourseProcessor:
    def __init__(self, session, console, course_id, chapter_id):
        self.session = session
        self.console = console
        self.course_id = course_id
        self.chapter_id = chapter_id

    def _get_video_duration(self):
        # 封装视频时长获取逻辑
        url = f"https://www.hebgb.gov.cn/portal/study_play.do?id={self.course_id}"

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip,deflate",
            "Accept-Language": "zh-CN, zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Length": "0",
            "Host": "www.hebgb.gov.cn",
            "Origin": "https://www.hebgb.gov.cn",
            "Referer": f"{url}",
        }

        # get page source
        html = self.session.get(url, headers=headers)
        # parse html
        soup = BeautifulSoup(html.text, "html.parser")

        # ignore errors
        course_id = soup.find("input", {"type": "hidden", "id": "course_id"}).get(
            "value", ""
        )

        is_gkk = soup.find("input", {"type": "hidden", "id": "is_gkk"}).get("value", "")
        payload = {"id": course_id, "is_gkk": is_gkk, "_": int(time.time() * 1000)}
        self.session.headers.update(
            {
                "X-Requested-With": "XMLHttpRequest",
                # accept
                "Accept": "*/*",
                # security
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                # referer
                "Referer": f"{url}",
            }
        )
        response = self.session.get(
            "https://www.hebgb.gov.cn/portal/getManifest.do",
            params=payload,
            headers=headers,
        )
        if response.status_code == 200:
            res_course_no = response.json().get("course_no", "")
            res_is_gkk = response.json().get("is_gkk", "")
            # 至此，已经拿到 course_no
            self.console.print(f"课程 coure_no: {res_course_no}")
        else:
            # 出错，则报错 15
            exit(15)

        payload = {
            "path": "sco1",
            "fileName": "1.mp4",
            "course_no": f"{res_course_no}",
            "is_gkk": f"{res_is_gkk}",
            "_": int(time.time() * 1000),
        }

        # get video url
        response = self.session.get(
            "https://www.hebgb.gov.cn/portal/getUrlBypf.do",
            params=payload,
            headers=headers,
        )

        if response.status_code == 200:
            video_url = response.text.strip()

            probe = ffmpeg.probe(video_url)
            video_stream = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "video"
                ),
                None,
            )

        try:
            if video_stream:
                duration = int(float(video_stream["duration"]))  # 单位秒
                return duration
            else:
                return 0
        except KeyError:  # 防止format字段不存在
            return 0
        except ValueError:  # 防止转换失败
            return 0

    def _simulate_learning(self, duration):
        # 封装学习进度模拟
        for _ in track(range(self._calculate_study_time(duration))):
            self._send_learning_progress()
            time.sleep(1)

    def start_learning(self):
        duration = self._get_video_duration()
        self._simulate_learning(duration)
