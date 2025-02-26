import json
import re
import time
from datetime import datetime
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

ua = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16"
login_url = "https://www.hebgb.gov.cn/portal/login_ajax.do"
code_url = "https://www.hebgb.gov.cn/portal/login_imgcode.do"
uinfo_url = "https://www.hebgb.gov.cn/portal/checkIsLogin.do?_="


class ErrorCodes(Enum):
    SUCCESS = 0
    LOGIN_FAILED = 11
    CAPTCHA_FAILED = 12
    COURSE_INFO_ERROR = 13
    COURSE_DURATION_ERROR = 14
    COURSE_GET_FAILED = 15
    UNKNOWN_ERROR = 99


def main():
    login(getua())
    get_Courses()


def getua():
    return ua


def login(ua):
    with open("userinfo.json", "r", encoding="utf-8") as file:
        uinfo = json.load(file)

    print("# 正在登陆...")
    headers = {
        "Host": "www.hebgb.gov.cn",
        "Referer": "https://www.hebgb.gov.cn/index.html",
        "User-Agent": f"{ua}",
    }

    # get capcha code image
    print("# 正在尝试获取登陆验证码...")
    session.headers.update(headers)
    r_code = session.get(code_url)
    code = 0

    # 检查响应状态码
    if r_code.status_code == 200:
        # 使用Pillow打开图像内容
        image = Image.open(BytesIO(r_code.content))
        # 转换为灰度图
        gray_image = image.convert("L")

        # 自定义灰度界限
        threshold = 150

        table = []
        for i in range(256):
            if i < threshold:
                table.append(0)
            else:
                table.append(1)

        # 图片二值化
        threshold_image = gray_image.point(table, "1")

        # OCR 文字识别
        ocr = ddddocr.DdddOcr(show_ad=False)
        code = ocr.classification(threshold_image)

        print("# 获取识别验证码成功，正在登陆...")
    else:
        print(f"获取验证码图片失败，状态码：{r_code.status_code}")

    if code != "":
        data = {
            "username": f"{uinfo[0]['uname']}",
            "passwd": f"{uinfo[0]['upass']}",
            "imgcode": f"{code}",
        }

        r_login = session.post(login_url, data=data)
        if "验证码错误" in r_login.text:
            print(r_login.text)
            exit(ErrorCodes.CAPTCHA_FAILED)
        elif "错误" in r_login.text:
            print(r_login.text)
            exit(ErrorCodes.LOGIN_FAILED)
        else:
            millis = int(round(time.time() * 1000))
            r = session.get(uinfo_url + str(millis))
            uinfo_dict = r.json()
            print("-----------------------------------------------")
            print(
                f"# 欢迎您，{uinfo_dict['realname']} 同志！\n# 您 {uinfo_dict['year']} 年度要求总学时为 {uinfo_dict['yqzxs']} 学时，已完成学时 {uinfo_dict['ywczxs']} 学时,\n# 要求必修总学时为 {uinfo_dict['yqbxxs']} 学时，已完成必修总学时 {uinfo_dict['ywcbxxs']} 学时"
            )


def get_Courses():
    """
    获取已报名课程
    """

    global table
    url_Signedup_Courses = (
        "https://www.hebgb.gov.cn/student/course_myselect.do?searchType=2&menu=course"
    )
    resp_Courses = session.get(url_Signedup_Courses)

    soup = BeautifulSoup(resp_Courses.text, "html.parser")

    course_rows = soup.find_all("div", class_="hoz_course_row")
    course_info_list = []

    for row in course_rows:
        # 课程名
        course_name = (
            row.find("h2").get_text(strip=True).replace("\n", "").replace(" ", "")
        )

        # 课程 ID
        onclick_value = row.find("input", type="button", onclick=True)["onclick"]
        match = re.search(r"addUrl\((\d+)\)", onclick_value)
        if match:
            course_id = match.group(1)
        else:
            course_id = ""

        # 章节 ID
        onclick_value = row.find("div", class_="hoz_c_lf lf")["onclick"]
        match = re.search(r"courseId=(\d+)", onclick_value)
        if match:
            chapter_id = match.group(1)
        else:
            chapter_id = ""

        # 课程时长（分钟）
        duration = (
            row.find("span", title="课程时长").get_text(strip=True).replace("分钟", "")
        )

        course_item = dict()
        course_item["coursename"] = course_name
        course_item["courseid"] = course_id
        course_item["chapterid"] = chapter_id
        course_item["duration"] = duration

        # 将信息添加到列表中
        course_info_list.append(course_item)

    table = Table(
        "序号",
        "课程标题",
        "课程代码",
        "章节代码",
        "课程时长",
        title="已报名的课程信息",
        box=box.MARKDOWN,
    )

    i = 0
    for course_info in course_info_list:
        i += 1
        table.add_row(
            str(i),
            course_info["coursename"],
            course_info["courseid"],
            course_info["chapterid"],
            course_info["duration"],
        )

    if course_info_list:
        print("暂无已报名课程!")

    console.print(table)

    a = input()
    temp = course_info_list[0]
    job(temp["courseid"], 16, temp["chapterid"], temp["duration"])


def get_course_duration(url):
    """获取课程时长

    Args:
        html (str): 课程页面 HTML 内容

    Returns:
        int: 课程时长（秒）
    """
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
    html = session.get(url, headers=headers)
    # parse html
    soup = BeautifulSoup(html.text, "html.parser")

    # ignore errors
    course_id = (
        element := soup.find("input", {"type": "hidden", "id": "course_id"})
    ).get("value", "")
    is_gkk = (element := soup.find("input", {"type": "hidden", "id": "is_gkk"})).get(
        "value", ""
    )
    payload = {"id": course_id, "is_gkk": is_gkk, "_": int(time.time() * 1000)}
    session.headers.update(
        {
            "User-Agent": ua,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "X-Requested-With": "XMLHttpRequest",
            "Host": "www.hebgb.gov.cn",
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
    response = session.get(
        "https://www.hebgb.gov.cn/portal/getManifest.do",
        params=payload,
        headers=headers,
    )
    if response.status_code == 200:
        res_course_no = response.json().get("course_no", "")
        res_is_gkk = response.json().get("is_gkk", "")
        # 至此，已经拿到 course_no
        console.print(f"课程 coure_no: {res_course_no}")
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
    response = session.get(
        "https://www.hebgb.gov.cn/portal/getUrlBypf.do",
        params=payload,
        headers=headers,
    )

    if response.status_code == 200:
        video_url = response.text.strip()

        probe = ffmpeg.probe(video_url)
        video_stream = next(
            (stream for stream in probe["streams"] if stream["codec_type"] == "video"),
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


def job(course_id, rate, chapter_id, duration):
    """学习课程

    Args:
        course_id (str): as it named
        rate (int): playback rate
        chapter_id (str): 与 HTTP POST Payload 中参数保持一致，在页面中显示参数名为 `courseId` :<
        duration (str): 课程时长（持续时间）
    """

    url = f"https://www.hebgb.gov.cn/portal/study_play.do?id={course_id}"
    url_learn = f"https://www.hebgb.gov.cn/portal/seekNew.do"

    # 获取课程时长
    duration = get_course_duration(url)

    if duration == 0:
        console.print("无法获取视频时长信息，程序将退出!")
        exit(ErrorCodes.COURSE_DURATION_ERROR)

    study_secs = int(int(duration) * 60 / 30 / rate) + 1
    print("预计本节所需时长为", f"{study_secs}秒")

    for k in track(range(study_secs), description=f"“学习”中..."):
        time.sleep(1)

        time_stamp = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
        )  # 格式化时间戳为本地时间
        res01 = {
            "lesson_location": f"{k * rate * 30}",
            "session_time": 30,
            "last_learn_time": f"{time_stamp}",
        }
        serializeSco = {"res01": res01, "last_study_sco": "res01"}
        data = {
            "id": f"{course_id}",
            "serializeSco": f"{serializeSco}",
            "duration": "480",
            "study_course": f"{chapter_id}",
        }
        # session.post(url_learn, data=data)
        print(data)
    print(f"章节:ID{chapter_id}  学习完成......")
    print("------------------------------------------------------")


if __name__ == "__main__":
    print("-----------------------------------------------")
    print(f"# 程序启动，时间戳：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    session = requests.Session()
    console = Console()
    try:
        main()
    except Exception as e:
        raise e
