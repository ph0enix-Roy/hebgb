import unittest
from unittest.mock import Mock

from courses import CourseManager


class TestSelectCourses(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.console = Mock()
        self.manager = CourseManager(self.session, self.console)
        self.sample_courses = [{"coursename": f"Course {i}"} for i in range(1, 6)]

    def test_select_all(self):
        result = self.manager.select_courses(self.sample_courses, "all")
        self.assertEqual(len(result), 5)

    def test_single_number(self):
        result = self.manager.select_courses(self.sample_courses, "3")
        self.assertEqual(result, [self.sample_courses[2]])

    def test_range_selection(self):
        result = self.manager.select_courses(self.sample_courses, "1-3")
        self.assertEqual(result, self.sample_courses[:3])

    def test_reverse_range(self):
        result = self.manager.select_courses(self.sample_courses, "5-3")
        self.assertEqual(
            result,
            [self.sample_courses[4], self.sample_courses[3], self.sample_courses[2]],
        )

    def test_mixed_selection(self):
        result = self.manager.select_courses(self.sample_courses, "1,3-5")
        self.assertEqual(
            result,
            [
                self.sample_courses[0],
                self.sample_courses[2],
                self.sample_courses[3],
                self.sample_courses[4],
            ],
        )

    def test_empty_input(self):
        result = self.manager.select_courses(self.sample_courses, "")
        self.assertEqual(result, [])

    def test_invalid_input(self):
        result = self.manager.select_courses(self.sample_courses, "2,abc,6-8")
        self.assertEqual(result, [self.sample_courses[1]])

    def test_chinese_comma(self):
        result = self.manager.select_courses(self.sample_courses, "1，5")
        self.assertEqual(result, [self.sample_courses[0], self.sample_courses[4]])

    def test_out_of_range(self):
        result = self.manager.select_courses(self.sample_courses, "0,6")
        self.assertEqual(result, [])

    def test_duplicate_selection(self):
        result = self.manager.select_courses(self.sample_courses, "2,2-4")
        self.assertEqual(
            result,
            [self.sample_courses[1], self.sample_courses[2], self.sample_courses[3]],
        )

    def test_empty_courses(self):
        result = self.manager.select_courses([], "1-3")
        self.assertEqual
