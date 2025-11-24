from __future__ import annotations

import argparse
import sys

from config import load_config
from http_client import MoodleClient
from jobs import ListCoursesJob, ListCourseVideosJob, WatchVideoJob, ProbeServiceJob, WatchCourseIncompleteJob


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autocrawler",
        description="GDUT Moodle 自动化爬虫/刷课基础框架",
    )
    p.add_argument(
        "command",
        choices=["list-courses", "list-videos", "watch-video", "probe-service", "watch-course-incomplete"],
        help="要执行的命令",
    )
    p.add_argument(
        "--cookie",
        dest="cookie_header",
        help="完整的Cookie头，例如 'MoodleSession=xxxx'",
    )
    p.add_argument(
        "--cookie-value",
        dest="cookie_value",
        help="仅MoodleSession的值，例如 'wd5061qf6606kc9t'",
    )
    # list-videos
    p.add_argument("--course-id", type=int, help="课程ID，例如 2545")
    p.add_argument("--only-incomplete", action="store_true", help="只显示未完成的视频")
    # watch-video
    p.add_argument("--video-id", type=int, help="视频模块ID，例如 159716")
    p.add_argument("--fsresourceid", type=int, help="fsresourceid（若无法自动解析可手动指定）")
    p.add_argument("--duration", type=int, default=300, help="刷课持续时间（秒）")
    p.add_argument("--interval", type=int, default=60, help="进度提交间隔（秒）")
    p.add_argument(
        "--payload-template",
        help="进度更新的JSON模板（包含 methodname 与 args），支持占位符 {sesskey} {timestamp} {courseId} {contextInstanceId} {videoId}",
    )
    p.add_argument(
        "--payload-file",
        help="从文件读取JSON模板，避免命令行转义问题（内容可含占位符）",
    )
    p.add_argument("--target-seconds", type=int, help="视频总时长（用于计算progress，若能从页面解析则可省略）")
    p.add_argument("--limit", type=int, help="批量刷课时最多处理的视频数量")
    p.add_argument("--gap", type=int, default=5, help="批量刷课两个视频之间的间隔秒数")
    return p


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    p = build_parser()
    args = p.parse_args(argv)

    cfg = load_config(cookie_header=args.cookie_header, cookie_value=args.cookie_value)
    if not cfg.cookie_header:
        print("缺少Cookie，使用 --cookie 或 --cookie-value，或设置环境变量 MOODLE_SESSION", file=sys.stderr)
        sys.exit(2)

    client = MoodleClient(base_url=cfg.base_url, cookie_header=cfg.cookie_header)

    if args.command == "list-courses":
        job = ListCoursesJob(client)
        job.run()
        return 0
    elif args.command == "list-videos":
        if not args.course_id:
            print("缺少 --course-id", file=sys.stderr)
            return 2
        job = ListCourseVideosJob(client, course_id=args.course_id, only_incomplete=args.only_incomplete)
        job.run()
        return 0
    elif args.command == "watch-video":
        if not args.video_id:
            print("缺少 --video-id", file=sys.stderr)
            return 2
        # 读取模板文件（若提供）
        tpl = args.payload_template
        if (not tpl) and args.payload_file:
            try:
                with open(args.payload_file, "r", encoding="utf-8") as f:
                    tpl = f.read()
            except Exception as e:
                print(f"读取模板文件失败: {e}", file=sys.stderr)
                return 2

        job = WatchVideoJob(
            client,
            video_id=args.video_id,
            duration_seconds=args.duration,
            interval_seconds=args.interval,
            payload_template=tpl,
            target_seconds=args.target_seconds,
        )
        # 若手动指定了 fsresourceid，则在模板替换之前注入
        if args.fsresourceid and tpl:
            job.payload_template = tpl.replace("{fsresourceid}", str(args.fsresourceid))
        job.run()
        return 0
    elif args.command == "probe-service":
        if not args.video_id:
            print("缺少 --video-id", file=sys.stderr)
            return 2
        tpl = args.payload_template
        if (not tpl) and args.payload_file:
            try:
                with open(args.payload_file, "r", encoding="utf-8") as f:
                    tpl = f.read()
            except Exception as e:
                print(f"读取模板文件失败: {e}", file=sys.stderr)
                return 2
        job = ProbeServiceJob(client, video_id=args.video_id, payload_template=tpl, target_seconds=args.target_seconds)
        if args.fsresourceid and tpl:
            job.payload_template = tpl.replace("{fsresourceid}", str(args.fsresourceid))
        job.run()
        return 0
    elif args.command == "watch-course-incomplete":
        if not args.course_id:
            print("缺少 --course-id", file=sys.stderr)
            return 2
        tpl = args.payload_template
        if (not tpl) and args.payload_file:
            try:
                with open(args.payload_file, "r", encoding="utf-8") as f:
                    tpl = f.read()
            except Exception as e:
                print(f"读取模板文件失败: {e}", file=sys.stderr)
                return 2
        job = WatchCourseIncompleteJob(
            client,
            course_id=args.course_id,
            duration_seconds=args.duration,
            interval_seconds=args.interval,
            payload_template=tpl,
            target_seconds=args.target_seconds,
            limit=args.limit,
            gap_seconds=args.gap,
        )
        job.run()
        return 0

    print("未知命令", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
