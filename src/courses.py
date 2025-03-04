from datetime import datetime
import json
from bs4 import BeautifulSoup
import re
import ffmpeg
from rich.table import Table
from rich import box
from rich.text import Text
import random
import time
import urllib.parse

from exceptions import GbException, ErrorCodes


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

        title = Text("已报名的课程信息", style="bold cyan")
        table = Table(
            title=title,
            box=box.SIMPLE,
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
        # TODO: 处理用户输入
        a = input("请输入序号以开始学习：")


class CourseProcessor:
    def __init__(self, session, console, course_list):
        self.session = session
        self.console = console
        self.course_list = course_list

    def _get_video_duration(self, course_id):
        # 封装视频时长获取逻辑
        url = f"https://www.hebgb.gov.cn/portal/study_play.do?id={course_id}"

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
                "Accept": "*/*",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
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
            self.ref = response.json().get("chapter", [{}])[0].get("identifierref", "")
            # 至此，已经拿到 course_no
        else:
            raise GbException(ErrorCodes.COURSE_GET_FAILED, "获取课程信息失败")

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

    def _calculate_study_interval(self, course_count):
        """根据选定的课程数量生成随机的n个时间间隔，并返回每个间隔的时长

        每个时间间隔的时长为随机整数，范围为1-5秒。

        Args:
            course_count (int): 课程数量

        Returns:
            interval_times: 每个时间间隔的时长，单位秒
        """
        # 计算学习总时长
        interval_times = []
        for i in range(course_count):
            current_interval = random.randint(1, 5)
            interval_times.append(current_interval)
        return interval_times

    def start_learning(self):
        if not self.course_list:
            raise GbException(ErrorCodes.COURSE_GET_FAILED, "未获取到课程信息")

        course_count = len(self.course_list)
        interval_times = self._calculate_study_interval(course_count)

        with self.console.create_progress() as progress:
            task = progress.add_task("[cyan]学习进度", total=course_count)

            # 初始状态信息
            self.console.info(f"开始学习 {course_count} 门课程")

            for i, course in enumerate(self.course_list):
                # 更新实时状态
                self.console.info(f"正在学习：{course['coursename']}")
                self._simulate_learning(course)
                time.sleep(interval_times[i])
                progress.update(
                    task, advance=1, description=f"[cyan]正在学习 {i+1}/{course_count}"
                )

    def _simulate_learning(self, course):
        # 封装学习进度模拟逻辑
        duration = self._get_video_duration(course["courseid"])
        if duration == 0:
            raise GbException(ErrorCodes.COURSE_DURATION_ERROR, "课程时长获取失败")

        SEEK_URL = f"https://www.hebgb.gov.cn/portal/seekNew.do"

        self.session.headers.update(
            {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "cache-control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "www.hebgb.gov.cn",
                "Origin": "https://www.hebgb.gov.cn",
                "Pragma": "no-cache",
                "Referer": f"https://www.hebgb.gov.cn/portal/study_play.do?id={course['courseid']}",
                "X-Requested-With": "XMLHttpRequest",
                "sec-ch-ua": 'Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="133"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "Windows",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
            }
        )

        current_location = 0
        remaining_duration = duration

        while remaining_duration > 0:
            chunk = min(480, remaining_duration)
            is_full_chunk = chunk == 480

            time.sleep(3 if is_full_chunk else 2)

            serialize_sco = {
                f"{self.ref}": {
                    "lesson_location": current_location,
                    "session_time": 30 if is_full_chunk else 2,
                    "last_learn_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                "last_study_sco": f"{self.ref}",
            }

            payload = {
                "id": course["courseid"],
                "serializeSco": urllib.parse.quote(json.dumps(serialize_sco)),
                "duration": chunk,
                "study_course": course["chapterid"],
            }

            response = self.session.post(SEEK_URL, data=payload)

            if response.status_code != 200:
                self.console.status(response.status_code)
                raise GbException(ErrorCodes.AJAX_REQUEST_ERROR, "请求学习课程失败")

            # TODO: 学习进度信息需要用户友好的显示方式
            # TODO: 能否在此处更新进度条？
            self.console.status(f"Response:{response.json()}")

            remaining_duration -= chunk
            current_location += chunk
