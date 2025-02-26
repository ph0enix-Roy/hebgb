from enum import Enum


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
