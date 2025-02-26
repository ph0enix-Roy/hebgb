from io import BytesIO
import json
import time
import ddddocr
from PIL import Image

from exceptions import GbException, ErrorCodes
from console_utils import RichOutput


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
