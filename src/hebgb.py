import json
import re
import time
from io import BytesIO
from enum import Enum


import ddddocr
import ffmpeg
import requests
from bs4 import BeautifulSoup
from PIL import Image
from rich import box
from rich.console import Console
from rich.progress import track
from rich.table import Table


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


class AuthManager:

    CAPTCHA_URL = "https://www.hebgb.gov.cn/portal/login_imgcode.do"
    LOGIN_URL = "https://www.hebgb.gov.cn/portal/login_ajax.do"
    USER_CHECK_URL = "https://www.hebgb.gov.cn/portal/checkIsLogin.do?_="

    def __init__(self, session, console):
        self.session = session
        self.console = console
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def login(self):
        """封装完整的登录流程"""
        self._load_credentials()
        captcha_code = self._get_captcha()
        self._validate_login(captcha_code)

    def _load_credentials(self):
        try:
            self.console.info("# 正在加载用户信息...", end="")
            with open("userinfo.json") as f:
                self.userinfo = json.load(f)[0]
            self.console.info("成功")
        except FileNotFoundError:
            self.console.error("! 用户信息文件未找到")
            raise GbException(ErrorCodes.LOGIN_FAILED, "用户信息文件未找到")
        except json.JSONDecodeError:
            self.console.error("! 用户信息文件格式错误")
            raise GbException(ErrorCodes.LOGIN_FAILED, "用户信息文件格式错误")
        except Exception as e:
            self.console.error(f"! 无法加载用户信息: {str(e)}")
            raise GbException(ErrorCodes.LOGIN_FAILED, f"无法加载用户信息: {str(e)}")

    def _get_captcha(self):
        # 封装验证码获取和识别逻辑
        headers = {
            "Referer": "https://www.hebgb.gov.cn/index.html",
        }

        # get capcha code image
        self.console.info("# 正在尝试获取登陆验证码...", end="")
        self.session.headers.update(headers)
        response = self.session.get(self.CAPTCHA_URL)
        if response.status_code != 200:
            raise GbException(ErrorCodes.CAPTCHA_FAILED, "验证码获取失败")

        self.console.info("成功")
        image = Image.open(BytesIO(response.content))
        return self._recognize_captcha(image)

    def _recognize_captcha(self, image):
        """识别验证码图片并返回识别结果

        Args:
            image (PIL.Image.Image): 验证码图片

        Returns:
            str: 识别结果
        """
        self.console.info("# 正在尝试识别验证码...", end="")

        threshold_image = self._create_threshold_table(image, 150)
        result = self.ocr.classification(threshold_image)

        self.console.info(f"识别结果：{result}")
        return result

    def _create_threshold_table(self, image, threshold):
        # 封装图像处理逻辑
        gray_image = image.convert("L")
        # 阈值表
        table = []
        for i in range(256):
            if i < threshold:
                table.append(0)
            else:
                table.append(1)

        # 图片二值化
        return gray_image.point(table, "1")

    def _validate_login(self, code):
        # 封装登录验证逻辑
        self.console.info("# 正在尝试登陆...", end="")

        if code != "":
            data = {
                "username": f"{self.userinfo['uname']}",
                "passwd": f"{self.userinfo['upass']}",
                "imgcode": f"{code}",
            }
        r_login = self.session.post(self.LOGIN_URL, data=data)
        if "验证码错误" in r_login.text:
            self.console.error(f"\n! {r_login.text}")
            exit(ErrorCodes.CAPTCHA_FAILED)
        elif "错误" in r_login.text:
            self.console.error(f"\n! {r_login.text}")
            exit(ErrorCodes.LOGIN_FAILED)
        else:
            self.console.info("成功")
            millis = int(round(time.time() * 1000))
            r = self.session.get(self.USER_CHECK_URL + str(millis))
            uinfo_dict = r.json()
            self.console.info("-----------------------------------------------")
            self.console.status(
                f"- 欢迎您，{uinfo_dict['realname']} 同志！\n"
                f"- 您 {uinfo_dict['year']} 年度要求总学时为 {uinfo_dict['yqzxs']} 学时，已完成学时 {uinfo_dict['ywczxs']} 学时,\n"
                f"- 要求必修总学时为 {uinfo_dict['yqbxxs']} 学时，已完成必修总学时 {uinfo_dict['ywcbxxs']} 学时"
            )


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


class ErrorCodes(Enum):
    SUCCESS = 0
    LOGIN_FAILED = 11
    CAPTCHA_FAILED = 12
    COURSE_INFO_ERROR = 13
    COURSE_DURATION_ERROR = 14
    COURSE_GET_FAILED = 15
    UNKNOWN_ERROR = 99


class GbException(Exception):
    def __init__(self, code: ErrorCodes, message: str):
        self.code = code.value
        self.message = message
        super().__init__(message)


if __name__ == "__main__":
    rich_console = RichOutput()
    try:
        app = GbLearningApp(console=rich_console)
        app.run()
    except Exception as e:
        # Console().print(f"[bold red]程序异常终止: {str(e)}")
        raise e
