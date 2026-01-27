import json
import time
from typing import List, Optional
from loguru import logger

from ...core.http_client import MoodleClient


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
        logger.info(f"访问视频页面 id={self.video_id}")
        html = self.client.get(f"/mod/fsresource/view.php?id={self.video_id}").text
        mcfg = self.client.parse_m_cfg(html)
        sesskey = mcfg.get("sesskey") or self.client.extract_sesskey(html)
        sessiontimeout = int(mcfg.get("sessiontimeout")) if mcfg.get("sessiontimeout") else None
        course_id = mcfg.get("courseId")
        context_instance_id = mcfg.get("contextInstanceId")
        fsinfo = self.client.extract_fsresource_info(html)
        fsresourceid = fsinfo.get("fsresourceid")
        
        if not sesskey and fsinfo.get("sesskey"):
            sesskey = fsinfo.get("sesskey")
        if not self.target_seconds and fsinfo.get("duration"):
            self.target_seconds = int(fsinfo["duration"])
        
        if not fsresourceid and context_instance_id:
            cm_info = self.client.get_course_module_info(int(context_instance_id), html_context=html)
            try:
                fsresourceid = cm_info.get("instance") or fsresourceid
            except Exception:
                pass
        
        logger.info(f"解析 M.cfg: sesskey={sesskey}, courseId={course_id}, contextInstanceId={context_instance_id}, sessiontimeout={sessiontimeout}")
        
        if not sesskey:
            logger.error("未能解析到 sesskey，无法提交进度。")
            return
        if not fsresourceid:
            logger.warning("未能解析到 fsresourceid，尝试用 videoId 作为 cmid 调用。")
            fsresourceid = self.video_id
        
        start = time.time()
        end = start + self.duration_seconds
        calls = 0
        
        while time.time() < end:
            calls += 1
            timestamp = int(time.time() * 1000)
            elapsed = int(time.time() - start)
            
            if not self.payload_template:
                logger.warning("未提供进度更新 JSON 模板，仅演示性调用。")
                time.sleep(self.interval_seconds)
                continue
            
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
                logger.error(f"JSON 模板解析失败: {e}")
                break
            
            if self.target_seconds:
                progress_val = max(0.0, min(1.0, elapsed / float(self.target_seconds)))
                try:
                    if "progress" in payload[0].get("args", {}):
                        payload[0]["args"]["progress"] = f"{progress_val:.2f}"
                except Exception:
                    pass
                try:
                    if "finish" in payload[0].get("args", {}):
                        payload[0]["args"]["finish"] = 1 if progress_val >= 0.999 else 0
                except Exception:
                    pass
            
            try:
                import random
                uniq = f"{timestamp}_{random.random()}"
                if "unique" in payload[0].get("args", {}):
                    payload[0]["args"]["unique"] = uniq
            except Exception:
                pass
            
            try:
                resp_json = self.client.post_service(payload, html_context=html, timestamp=timestamp)
                out = resp_json
                try:
                    if isinstance(resp_json, list) and resp_json:
                        out = resp_json[0].get("data", resp_json[0])
                except Exception:
                    pass
                msg = str(out)
                logger.info(f"[{calls}] 提交成功: {msg[:160]}")
                
                try:
                    if isinstance(out, dict) and out.get("completion") == "已完成":
                        logger.info("检测到已完成，提前结束。")
                        break
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"[{calls}] 提交失败: {e}")
            
            sleep_s = self.interval_seconds
            if sessiontimeout and sleep_s > sessiontimeout:
                sleep_s = max(30, sessiontimeout // 2)
            time.sleep(sleep_s)


class ProbeServiceJob:
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
        logger.info(f"探测 service.php：video id={self.video_id}")
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
        
        if not fsresourceid:
            fsresourceid = self.video_id
        
        if not self.payload_template:
            logger.error("缺少模板：请提供真实 JSON。")
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
            .replace("{time}", "3")
        )
        
        try:
            payload = json.loads(payload_str)
        except Exception as e:
            logger.error(f"JSON 模板解析失败: {e}")
            return
        
        out = self.client.post_service_capture(payload, html_context=html, timestamp=timestamp)
        raw = out.get("raw")
        parsed = out.get("json")
        logger.info("原始响应：")
        logger.info(str(raw)[:500])
        
        try:
            view = parsed
            if isinstance(parsed, list) and parsed:
                view = parsed[0].get("data", parsed[0])
            if isinstance(view, dict):
                logger.info(f"解析：status={view.get('status')} progress={view.get('progress')} totaltime={view.get('totaltime')} completion={view.get('completion')}")
        except Exception:
            pass


class WatchCourseIncompleteJob:
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
        logger.info(f"扫描课程 {self.course_id} 的未完成视频")
        html = self.client.get(f"/course/view.php?id={self.course_id}").text
        from ...core.parsers import parse_course_fsresources
        items = parse_course_fsresources(html)
        items = [it for it in items if it.incomplete is True]
        
        if not items:
            logger.info("没有检测到未完成视频。")
            return
        
        if self.limit is not None:
            items = items[: self.limit]
        
        logger.info(f"准备刷 {len(items)} 个视频（顺序执行）")
        
        for idx, it in enumerate(items, 1):
            logger.info(f"({idx}/{len(items)}) 处理视频 id={it.id} name={it.name}")
            job = WatchVideoJob(
                self.client,
                video_id=it.id,
                duration_seconds=self.duration_seconds,
                interval_seconds=self.interval_seconds,
                payload_template=self.payload_template,
                target_seconds=self.target_seconds,
            )
            job.run()
            time.sleep(self.gap_seconds)
