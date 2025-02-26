import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.src.hebgb import CourseManager  # 现在应该可以正常导入了
from rich.table import Table
from unittest.mock import Mock


def test_display_courses_table(mocker):
    # 创建模拟数据
    mock_courses = [
        {
            "coursename": "Python基础",
            "courseid": "1001",
            "chapterid": "2001",
            "duration": "45",
        },
        {
            "coursename": "Web开发",
            "courseid": "1002",
            "chapterid": "2002",
            "duration": "60",
        },
    ]

    # 创建Mock Console对象
    mock_console = Mock()

    # 初始化被测试对象
    manager = CourseManager(session=None, console=mock_console)

    # 执行测试方法
    manager.display_courses_table(mock_courses)

    # 验证console.print被调用
    mock_console.print.assert_called_once()

    # 获取实际生成的Table对象
    called_table = mock_console.print.call_args[0][0]

    # 验证表格结构
    assert isinstance(called_table, Table)
    assert called_table.title == "已报名的课程信息"
    assert [c.header for c in called_table.columns] == [
        "序号",
        "课程标题",
        "课程代码",
        "章节代码",
        "课程时长",
    ]
