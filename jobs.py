from __future__ import annotations

import json
import time
from typing import List, Optional

from colorama import Fore, Style

from http_client import MoodleClient
from parsers import parse_overview_courses, Course, parse_course_fsresources, VideoItem


class ListCoursesJob:
    def __init__(self, client: MoodleClient):
        self.client = client

    def run(self) -> List[Course]:
        html = self.client.get_my_courses_page()
        courses = parse_overview_courses(html)
        # pretty print
        if courses:
            print(Fore.CYAN + f"课程概览中共发现 {len(courses)} 门课程" + Style.RESET_ALL)
        else:
            # Try AJAX service fallback
            api_courses = self.client.fetch_overview_courses_api(html, classification="all")
            converted: List[Course] = []
            for c in api_courses:
                cid = c.get("id")
                name = c.get("fullname") or c.get("shortname") or str(cid)
                url = c.get("viewurl") or (f"https://courses.gdut.edu.cn/course/view.php?id={cid}" if cid else "")
                converted.append(Course(id=cid, name=name, url=url))
            courses = converted
            print(Fore.YELLOW + "HTML未检出课程概览，已通过AJAX接口获取。" + Style.RESET_ALL)
            print(Fore.CYAN + f"课程概览中共发现 {len(courses)} 门课程" + Style.RESET_ALL)
        for idx, c in enumerate(courses, 1):
            cid = c.id if c.id is not None else "?"
            print(f"[{idx}] id={cid} name={c.name} url={c.url}")
        return courses


class ListCourseVideosJob:
    def __init__(self, client: MoodleClient, course_id: int, only_incomplete: bool = False):
        self.client = client
        self.course_id = course_id
        self.only_incomplete = only_incomplete

    def run(self) -> List[VideoItem]:
        html = self.client.get(f"/course/view.php?id={self.course_id}").text
        items = parse_course_fsresources(html)
        if self.only_incomplete:
            items = [it for it in items if it.incomplete is True]
        print(Fore.CYAN + f"课程 {self.course_id} 中找到 {len(items)} 个视频资源" + Style.RESET_ALL)
        for idx, it in enumerate(items, 1):
            state = (
                "未完成" if it.incomplete is True else ("已完成" if it.incomplete is False else "未知")
            )
            print(f"[{idx}] id={it.id} name={it.name} state={state} url={it.url}")
        return items


class WatchVideoJob:
    def __init__(
        self,
        client: MoodleClient,
        video_id: int,
        duration_seconds: int = 300,
        interval_seconds: int = 60,
        payload_template: Optional[str] = None,
        target_seconds: Optional[int] = None,
    ):
        self.client = client
        self.video_id = video_id
        self.duration_seconds = duration_seconds
        self.interval_seconds = interval_seconds
        self.payload_template = payload_template
        self.target_seconds = target_seconds

    def run(self) -> None:
        # Visit the video page to establish context and extract M.cfg
        print(Fore.CYAN + f"访问视频页面 id={self.video_id}" + Style.RESET_ALL)
        html = self.client.get(f"/mod/fsresource/view.php?id={self.video_id}").text
        mcfg = self.client.parse_m_cfg(html)
        sesskey = mcfg.get("sesskey") or self.client.extract_sesskey(html)
        sessiontimeout = int(mcfg.get("sessiontimeout")) if mcfg.get("sessiontimeout") else None
        course_id = mcfg.get("courseId")
        context_instance_id = mcfg.get("contextInstanceId")
        fsinfo = self.client.extract_fsresource_info(html)
        fsresourceid = fsinfo.get("fsresourceid")
        # 若 M.cfg 未给出 sesskey，尝试从 playerdata 中获取
        if not sesskey and fsinfo.get("sesskey"):
            sesskey = fsinfo.get("sesskey")
        if not self.target_seconds and fsinfo.get("duration"):
            self.target_seconds = int(fsinfo["duration"])  # 用页面时长估算分母
        # If fsresourceid missing, try resolving via course module info
        if not fsresourceid and context_instance_id:
            cm_info = self.client.get_course_module_info(int(context_instance_id), html_context=html)
            try:
                fsresourceid = cm_info.get("instance") or fsresourceid
            except Exception:
                pass
            try:
                print(Fore.BLUE + f"cm_info: {str(cm_info)[:160]}" + Style.RESET_ALL)
            except Exception:
                pass

        print(
            Fore.GREEN
            + f"解析 M.cfg: sesskey={sesskey}, courseId={course_id}, contextInstanceId={context_instance_id}, sessiontimeout={sessiontimeout}"
            + Style.RESET_ALL
        )

        if not sesskey:
            print(Fore.RED + "未能解析到 sesskey，无法提交进度。" + Style.RESET_ALL)
            return
        if not fsresourceid:
            print(Fore.YELLOW + "未能解析到 fsresourceid，尝试用 videoId 作为 cmid 调用。" + Style.RESET_ALL)
            fsresourceid = self.video_id

        # Prepare run loop
        start = time.time()
        end = start + self.duration_seconds
        calls = 0
        while time.time() < end:
            calls += 1
            timestamp = int(time.time() * 1000)
            elapsed = int(time.time() - start)

            if not self.payload_template:
                print(
                    Fore.YELLOW
                    + "未提供进度更新 JSON 模板（payload_template），仅演示性调用，等待你提供真实 JSON。"
                    + Style.RESET_ALL
                )
                time.sleep(self.interval_seconds)
                continue

            # Fill placeholders in template and parse JSON
            time_value = min(elapsed, int(self.duration_seconds))
            payload_str = (
                self.payload_template
                .replace("{timestamp}", str(timestamp))
                .replace("{sesskey}", str(sesskey))
                .replace("{courseId}", str(course_id))
                .replace("{contextInstanceId}", str(context_instance_id))
                .replace("{videoId}", str(self.video_id))
                .replace("{fsresourceid}", str(fsresourceid))
                .replace("{time}", str(time_value))
            )
            try:
                payload = json.loads(payload_str)
            except Exception as e:
                print(Fore.RED + f"JSON 模板解析失败: {e}" + Style.RESET_ALL)
                break

            # 计算可选 progress 值
            if self.target_seconds:
                progress_val = max(0.0, min(1.0, elapsed / float(self.target_seconds)))
                # 尝试写回到 payload 中（若存在 progress 字段）
                try:
                    if "progress" in payload[0].get("args", {}):
                        payload[0]["args"]["progress"] = f"{progress_val:.2f}"
                except Exception:
                    pass
                # 若接近完成则设置 finish=1
                try:
                    if "finish" in payload[0].get("args", {}):
                        payload[0]["args"]["finish"] = 1 if progress_val >= 0.999 else 0
                except Exception:
                    pass
            # unique 字段填充（若存在）
            try:
                import random
                uniq = f"{timestamp}_{random.random()}"
                if "unique" in payload[0].get("args", {}):
                    payload[0]["args"]["unique"] = uniq
            except Exception:
                pass

            # POST 到 service.php
            try:
                resp_json = self.client.post_service(payload, html_context=html, timestamp=timestamp)
                # 响应可能为列表，取第一个项的 data 或原始值
                out = resp_json
                try:
                    if isinstance(resp_json, list) and resp_json:
                        out = resp_json[0].get("data", resp_json[0])
                except Exception:
                    pass
                msg = str(out)
                print(Fore.GREEN + f"[{calls}] 提交成功: {msg[:160]}" + Style.RESET_ALL)

                # 检查完成状态
                try:
                    if isinstance(out, dict) and out.get("completion") == "已完成":
                        print(Fore.CYAN + "检测到已完成，提前结束。" + Style.RESET_ALL)
                        break
                except Exception:
                    pass
            except Exception as e:
                print(Fore.RED + f"[{calls}] 提交失败: {e}" + Style.RESET_ALL)

            # Respect session timeout warning if provided
            sleep_s = self.interval_seconds
            if sessiontimeout and sleep_s > sessiontimeout:
                sleep_s = max(30, sessiontimeout // 2)
            time.sleep(sleep_s)


class ProbeServiceJob:
    """发起一次 service.php 请求以捕获原始响应并解析关键字段。

    用法与 watch-video 类似，但仅发送一次并打印原文与解析结果。
    """
    def __init__(
        self,
        client: MoodleClient,
        video_id: int,
        payload_template: Optional[str] = None,
        target_seconds: Optional[int] = None,
    ):
        self.client = client
        self.video_id = video_id
        self.payload_template = payload_template
        self.target_seconds = target_seconds

    def run(self) -> None:
        print(Fore.CYAN + f"探测 service.php：video id={self.video_id}" + Style.RESET_ALL)
        html_resp = self.client.get(f"/mod/fsresource/view.php?id={self.video_id}")
        html = html_resp.text
        mcfg = self.client.parse_m_cfg(html)
        sesskey = mcfg.get("sesskey") or self.client.extract_sesskey(html)
        fsinfo = self.client.extract_fsresource_info(html)
        if not sesskey and fsinfo.get("sesskey"):
            sesskey = fsinfo.get("sesskey")
        fsresourceid = fsinfo.get("fsresourceid")
        context_instance_id = mcfg.get("contextInstanceId")
        course_id = mcfg.get("courseId")
        if not fsresourceid and context_instance_id:
            try:
                cm_info = self.client.get_course_module_info(int(context_instance_id), html_context=html)
                fsresourceid = cm_info.get("instance") or fsresourceid
            except Exception:
                pass
        # 最后兜底：若仍未解析到 fsresourceid，则使用 videoId 作为 cmid/fallback
        if not fsresourceid:
            fsresourceid = self.video_id

        if not self.payload_template:
            print(Fore.RED + "缺少模板：请通过 --payload-file 或 --payload-template 提供真实 JSON。" + Style.RESET_ALL)
            return
        timestamp = int(time.time() * 1000)
        payload_str = (
            self.payload_template
            .replace("{timestamp}", str(timestamp))
            .replace("{sesskey}", str(sesskey))
            .replace("{courseId}", str(course_id))
            .replace("{contextInstanceId}", str(context_instance_id))
            .replace("{videoId}", str(self.video_id))
            .replace("{fsresourceid}", str(fsresourceid))
            .replace("{time}", "3")  # 简单探测：填入一个小值
        )
        try:
            payload = json.loads(payload_str)
        except Exception as e:
            print(Fore.RED + f"JSON 模板解析失败: {e}" + Style.RESET_ALL)
            return

        out = self.client.post_service_capture(payload, html_context=html, timestamp=timestamp)
        raw = out.get("raw")
        parsed = out.get("json")
        print(Fore.GREEN + "原始响应：" + Style.RESET_ALL)
        print(str(raw)[:500])

        # 解析关键字段（若为列表则取第一个 data）
        try:
            view = parsed
            if isinstance(parsed, list) and parsed:
                view = parsed[0].get("data", parsed[0])
            if isinstance(view, dict):
                print(Fore.CYAN + f"解析：status={view.get('status')} progress={view.get('progress')} totaltime={view.get('totaltime')} completion={view.get('completion')}" + Style.RESET_ALL)
        except Exception:
            pass


class WatchCourseIncompleteJob:
    """按顺序刷指定课程中的未完成视频。

    顺序执行以避免并发观看警告。每个视频使用 WatchVideoJob 的逻辑，自动解析
    sesskey/fsresourceid，并在返回 "completion":"已完成" 时结束。
    """
    def __init__(
        self,
        client: MoodleClient,
        course_id: int,
        duration_seconds: int = 300,
        interval_seconds: int = 60,
        payload_template: Optional[str] = None,
        target_seconds: Optional[int] = None,
        limit: Optional[int] = None,
        gap_seconds: int = 5,
    ):
        self.client = client
        self.course_id = course_id
        self.duration_seconds = duration_seconds
        self.interval_seconds = interval_seconds
        self.payload_template = payload_template
        self.target_seconds = target_seconds
        self.limit = limit
        self.gap_seconds = gap_seconds

    def run(self) -> None:
        print(Fore.CYAN + f"扫描课程 {self.course_id} 的未完成视频" + Style.RESET_ALL)
        html = self.client.get(f"/course/view.php?id={self.course_id}").text
        items = parse_course_fsresources(html)
        items = [it for it in items if it.incomplete is True]
        if not items:
            print(Fore.GREEN + "没有检测到未完成视频。" + Style.RESET_ALL)
            return
        if self.limit is not None:
            items = items[: self.limit]
        print(Fore.CYAN + f"准备刷 {len(items)} 个视频（顺序执行）" + Style.RESET_ALL)
        for idx, it in enumerate(items, 1):
            print(Fore.MAGENTA + f"({idx}/{len(items)}) 处理视频 id={it.id} name={it.name}" + Style.RESET_ALL)
            job = WatchVideoJob(
                self.client,
                video_id=it.id,
                duration_seconds=self.duration_seconds,
                interval_seconds=self.interval_seconds,
                payload_template=self.payload_template,
                target_seconds=self.target_seconds,
            )
            job.run()
            # 间隔避免并发或频率过高
            time.sleep(self.gap_seconds)
