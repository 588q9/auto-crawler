import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from src.config.settings import load_config
from src.utils.logger import setup_logger
from src.core.http_client import MoodleClient
from src.features.checkin.scheduler import CheckinScheduler
from src.features.checkin.worker import CheckinWorker
from src.features.course.list import ListCoursesJob, ListCourseVideosJob
from src.features.course.watch import WatchVideoJob, ProbeServiceJob, WatchCourseIncompleteJob


@click.group()
@click.option("--config", "-c", default="config/config.yaml", help="配置文件路径")
@click.option("--log-level", default="INFO", help="日志级别")
@click.pass_context
def cli(ctx, config: str, log_level: str):
    ctx.ensure_object(dict)

    config_path = Path(config)
    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config}，使用默认配置")

    cfg = load_config(config if config_path.exists() else None)
    ctx.obj["config"] = cfg

    setup_logger(log_level or cfg.app.log_level)
    logger.info(f"配置文件: {config}")


@cli.group()
def checkin():
    pass


@checkin.command()
@click.option("--once", is_flag=True, help="执行单次签到")
@click.option("--cookie", type=str, default=None, help="覆盖请求头 Cookie")
@click.option("--api-user", type=str, default=None, help="覆盖请求头 New-API-User")
@click.pass_context
def run(ctx, once: bool, cookie: Optional[str], api_user: Optional[str]):
    cfg = ctx.obj["config"]

    if not cfg.checkin.enabled:
        logger.error("签到功能未启用，请在配置文件中设置 checkin.enabled = true")
        sys.exit(1)

    cookie_header = cookie or cfg.auth.cookie_header
    api_user_header = api_user or (getattr(cfg.auth, "new_api_user", None))
    if not cookie_header or not api_user_header:
        logger.error("缺少请求头：请通过 --cookie 与 --api-user 或配置文件提供")
        sys.exit(1)

    scheduler = CheckinScheduler(cfg.checkin, cfg.browser, cookie_header or "", api_user_header or "")

    if once:
        logger.info("执行单次签到")
        scheduler.run_once()
    else:
        logger.info("启动每日签到调度器")
        scheduler.run_daily()


@cli.group()
def course():
    pass


@course.command()
@click.pass_context
def list_courses(ctx):
    cfg = ctx.obj["config"]

    if not cfg.auth.cookie_header:
        logger.error("缺少Cookie，请在配置文件中设置 auth.cookie_header")
        sys.exit(1)

    client = MoodleClient(cfg.app.base_url, cfg.auth.cookie_header)
    job = ListCoursesJob(client)
    job.run()


@course.command()
@click.option("--course-id", type=int, required=True, help="课程ID")
@click.option("--only-incomplete", is_flag=True, help="只显示未完成的视频")
@click.pass_context
def list_videos(ctx, course_id: int, only_incomplete: bool):
    cfg = ctx.obj["config"]

    if not cfg.auth.cookie_header:
        logger.error("缺少Cookie，请在配置文件中设置 auth.cookie_header")
        sys.exit(1)

    client = MoodleClient(cfg.app.base_url, cfg.auth.cookie_header)
    job = ListCourseVideosJob(client, course_id, only_incomplete)
    job.run()


@course.command()
@click.option("--video-id", type=int, required=True, help="视频模块ID")
@click.option("--duration", type=int, default=None, help="刷课持续时间（秒）")
@click.option("--interval", type=int, default=None, help="进度提交间隔（秒）")
@click.option("--payload-file", type=str, default=None, help="从文件读取JSON模板")
@click.option("--target-seconds", type=int, default=None, help="视频总时长（秒）")
@click.pass_context
def watch_video(ctx, video_id: int, duration: Optional[int], interval: Optional[int],
                payload_file: Optional[str], target_seconds: Optional[int]):
    cfg = ctx.obj["config"]

    if not cfg.auth.cookie_header:
        logger.error("缺少Cookie，请在配置文件中设置 auth.cookie_header")
        sys.exit(1)

    client = MoodleClient(cfg.app.base_url, cfg.auth.cookie_header)

    duration = duration or cfg.course.duration_seconds
    interval = interval or cfg.course.interval_seconds

    payload_template = None
    if payload_file:
        try:
            with open(payload_file, "r", encoding="utf-8") as f:
                payload_template = f.read()
        except Exception as e:
            logger.error(f"读取模板文件失败: {e}")
            sys.exit(1)
    elif cfg.course.payload_template:
        try:
            with open(cfg.course.payload_template, "r", encoding="utf-8") as f:
                payload_template = f.read()
        except Exception as e:
            logger.error(f"读取模板文件失败: {e}")
            sys.exit(1)

    job = WatchVideoJob(
        client,
        video_id=video_id,
        duration_seconds=duration,
        interval_seconds=interval,
        payload_template=payload_template,
        target_seconds=target_seconds,
    )
    job.run()


@course.command()
@click.option("--video-id", type=int, required=True, help="视频模块ID")
@click.option("--payload-file", type=str, default=None, help="从文件读取JSON模板")
@click.option("--target-seconds", type=int, default=None, help="视频总时长（秒）")
@click.pass_context
def probe_service(ctx, video_id: int, payload_file: Optional[str], target_seconds: Optional[int]):
    cfg = ctx.obj["config"]

    if not cfg.auth.cookie_header:
        logger.error("缺少Cookie，请在配置文件中设置 auth.cookie_header")
        sys.exit(1)

    client = MoodleClient(cfg.app.base_url, cfg.auth.cookie_header)

    payload_template = None
    if payload_file:
        try:
            with open(payload_file, "r", encoding="utf-8") as f:
                payload_template = f.read()
        except Exception as e:
            logger.error(f"读取模板文件失败: {e}")
            sys.exit(1)
    elif cfg.course.payload_template:
        try:
            with open(cfg.course.payload_template, "r", encoding="utf-8") as f:
                payload_template = f.read()
        except Exception as e:
            logger.error(f"读取模板文件失败: {e}")
            sys.exit(1)

    job = ProbeServiceJob(
        client,
        video_id=video_id,
        payload_template=payload_template,
        target_seconds=target_seconds,
    )
    job.run()


@course.command()
@click.option("--course-id", type=int, required=True, help="课程ID")
@click.option("--duration", type=int, default=None, help="刷课持续时间（秒）")
@click.option("--interval", type=int, default=None, help="进度提交间隔（秒）")
@click.option("--payload-file", type=str, default=None, help="从文件读取JSON模板")
@click.option("--target-seconds", type=int, default=None, help="视频总时长（秒）")
@click.option("--limit", type=int, default=None, help="最多处理的视频数量")
@click.option("--gap", type=int, default=None, help="视频之间的间隔秒数")
@click.pass_context
def watch_course_incomplete(ctx, course_id: int, duration: Optional[int], interval: Optional[int],
                           payload_file: Optional[str], target_seconds: Optional[int],
                           limit: Optional[int], gap: Optional[int]):
    cfg = ctx.obj["config"]

    if not cfg.auth.cookie_header:
        logger.error("缺少Cookie，请在配置文件中设置 auth.cookie_header")
        sys.exit(1)

    client = MoodleClient(cfg.app.base_url, cfg.auth.cookie_header)

    duration = duration or cfg.course.duration_seconds
    interval = interval or cfg.course.interval_seconds
    gap = gap or cfg.course.gap_seconds

    payload_template = None
    if payload_file:
        try:
            with open(payload_file, "r", encoding="utf-8") as f:
                payload_template = f.read()
        except Exception as e:
            logger.error(f"读取模板文件失败: {e}")
            sys.exit(1)
    elif cfg.course.payload_template:
        try:
            with open(cfg.course.payload_template, "r", encoding="utf-8") as f:
                payload_template = f.read()
        except Exception as e:
            logger.error(f"读取模板文件失败: {e}")
            sys.exit(1)

    job = WatchCourseIncompleteJob(
        client,
        course_id=course_id,
        duration_seconds=duration,
        interval_seconds=interval,
        payload_template=payload_template,
        target_seconds=target_seconds,
        limit=limit,
        gap_seconds=gap,
    )
    job.run()


@cli.command()
@click.option("--checkin", is_flag=True, help="运行签到功能")
@click.option("--course", is_flag=True, help="运行刷课功能")
@click.option("--course-id", type=int, default=None, help="课程ID（用于刷课）")
@click.option("--cookie", type=str, default=None, help="覆盖签到 Cookie")
@click.option("--api-user", type=str, default=None, help="覆盖签到 New-API-User")
@click.pass_context
def run_all(ctx, checkin: bool, course: bool, course_id: Optional[int], cookie: Optional[str], api_user: Optional[str]):
    cfg = ctx.obj["config"]

    if not checkin and not course:
        logger.error("请指定要运行的功能：--checkin 或 --course")
        sys.exit(1)

    if checkin and cfg.checkin.enabled:
        logger.info("运行签到功能")
        from src.features.checkin.api_worker import ApiCheckinWorker
        worker = ApiCheckinWorker(cfg.checkin, (cookie or cfg.auth.cookie_header), (api_user or getattr(cfg.auth, "new_api_user", None)))
        worker.run()

    if course and cfg.course.enabled:
        if not course_id:
            logger.error("请指定课程ID：--course-id")
            sys.exit(1)

        logger.info(f"运行刷课功能，课程ID: {course_id}")
        client = MoodleClient(cfg.app.base_url, cfg.auth.cookie_header)

        payload_template = None
        if cfg.course.payload_template:
            try:
                with open(cfg.course.payload_template, "r", encoding="utf-8") as f:
                    payload_template = f.read()
            except Exception as e:
                logger.error(f"读取模板文件失败: {e}")

        job = WatchCourseIncompleteJob(
            client,
            course_id=course_id,
            duration_seconds=cfg.course.duration_seconds,
            interval_seconds=cfg.course.interval_seconds,
            payload_template=payload_template,
            limit=cfg.course.limit,
            gap_seconds=cfg.course.gap_seconds,
        )
        job.run()


if __name__ == "__main__":
    cli()
