from typing import List
from loguru import logger

from ...core.http_client import MoodleClient
from ...core.parsers import parse_overview_courses, parse_course_fsresources, Course, VideoItem


class ListCoursesJob:
    def __init__(self, client: MoodleClient):
        self.client = client
    
    def run(self) -> List[Course]:
        logger.info("获取课程列表")
        html = self.client.get_my_courses_page()
        courses = parse_overview_courses(html)
        
        if not courses:
            logger.warning("HTML未检出课程概览，尝试通过AJAX接口获取")
            api_courses = self.client.fetch_overview_courses_api(html, classification="all")
            courses = []
            for c in api_courses:
                cid = c.get("id")
                name = c.get("fullname") or c.get("shortname") or str(cid)
                url = c.get("viewurl") or f"https://courses.gdut.edu.cn/course/view.php?id={cid}" if cid else ""
                courses.append(Course(id=cid, name=name, url=url))
        
        logger.info(f"共发现 {len(courses)} 门课程")
        for idx, c in enumerate(courses, 1):
            logger.info(f"[{idx}] id={c.id} name={c.name} url={c.url}")
        
        return courses


class ListCourseVideosJob:
    def __init__(self, client: MoodleClient, course_id: int, only_incomplete: bool = False):
        self.client = client
        self.course_id = course_id
        self.only_incomplete = only_incomplete
    
    def run(self) -> List[VideoItem]:
        logger.info(f"获取课程 {self.course_id} 的视频列表")
        html = self.client.get(f"/course/view.php?id={self.course_id}").text
        items = parse_course_fsresources(html)
        
        if self.only_incomplete:
            items = [it for it in items if it.incomplete is True]
        
        logger.info(f"课程 {self.course_id} 中找到 {len(items)} 个视频资源")
        for idx, it in enumerate(items, 1):
            state = "未完成" if it.incomplete is True else ("已完成" if it.incomplete is False else "未知")
            logger.info(f"[{idx}] id={it.id} name={it.name} state={state} url={it.url}")
        
        return items
