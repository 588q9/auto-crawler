# auto-crawler

一个用于 GDUT “蕴瑜课堂”（Moodle）平台的基础自动化刷课/爬取框架。

注意：本项目仅提供技术框架与示例，请遵守平台的使用条款与课程教学要求。请仅在获得授权的情况下进行自动化访问。

## 功能概览

- 使用 `MoodleSession` Cookie 进行身份验证
- 访问 `https://courses.gdut.edu.cn/my/` 并解析“课程概览”中的课程列表
- 访问课程页并解析 `mod/fsresource` 视频资源，识别未完成项
- 提供 `watch-video` 命令，解析 M.cfg 并按间隔调用 AJAX 接口（需提供 JSON 模板）
- CLI 命令：列出课程

## 快速开始

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 运行列课命令（从“课程概览”区域提取，推荐以环境变量或参数传入 Cookie 值）：

```bash
python main.py list-courses --cookie-value wqeqwn53a5061qf6606kc9t
```

或使用环境变量：

```bash
set MOODLE_SESSION=fweqwun53a5061qf6606kc9t
python -m autocrawler.main list-courses
```

> 提示：`--cookie` 参数也支持传入完整的 `Cookie` 头内容，例如：
>
> `--cookie "MoodleSession=3243s5061qf6606kc9t"`

## 目录结构

```
config.py
http_client.py
parsers.py
jobs.py
main.py
requirements.txt
README.md
```

## 安全与合规

- Cookie 等敏感信息不要提交到任何版本库。
- 合理控制访问频率，避免对平台造成压力。
- 若页面结构更新，请调整 `parsers.py` 中的选择器或逻辑。

## 已知局限

- Moodle 不同主题/版本的课程列表结构可能不同；当前解析器使用常见选择器并带有后备匹配（如匹配 `/course/view.php?id=` 的链接）。
- 若“课程概览”通过异步加载（AJAX）填充课程列表，需增加对对应接口的请求与解析。

### 列出课程中的视频资源

```bash
python main.py list-videos --course-id 2545 --cookie-value ferr12n53a5061qf6606kc9t --only-incomplete
```

### 观看（刷）指定视频资源

`watch-video` 需要你提供真实的 AJAX JSON 模板（即页面在播放时提交的 payload），模板中可使用占位符：`{sesskey}`、`{timestamp}`、`{courseId}`、`{contextInstanceId}`、`{videoId}`，示例：

优选用文件提供模板，避免命令行转义：

```bash
python main.py watch-video --video-id 159716 \
  --cookie-value fm1ci3bun53a5061qf6606kc9t \
  --duration 600 --interval 60 \
  --payload-file payloads/example_fsresource_set_time.json
```

> 注意：以上 `methodname` 与 `args` 仅为示例，需以你页面真实的请求为准；你可将浏览器中监测到的网络请求（`service.php` 的 POST 体）直接粘贴为模板。模板支持占位符：`{sesskey}`、`{timestamp}`、`{courseId}`、`{contextInstanceId}`、`{videoId}`、`{fsresourceid}`、`{time}`。

- 解析器会优先从视频页的 `playerdata` 对象中提取 `fsresourceid` 与 `sesskey`（例如：`playerdata = {'fsresourceid':89161,'sesskey':'...','progress':1,...}`）；若 `M.cfg` 未包含 `sesskey`，会使用 `playerdata` 中的值。
- 当无法解析到 `fsresourceid` 时，会尝试通过 `core_course_get_course_module(cmid)` 获取模块信息并使用其 `instance`；也可通过 `--fsresourceid` 手动提供。
- `{time}` 会按“累计已观看秒数”自动填入；若模板包含 `progress` 字段，会按“已观看秒数 / 目标总时长”自动计算（`--target-seconds` 可指定，默认取页面时长或 `--duration`）。
- 若模板包含 `finish` 字段，接近完成时会自动置为 `1`。当服务端返回 `{"completion":"已完成"}` 时，脚本会自动结束。

### 批量刷课：课程内未完成视频

按顺序刷某课程中所有“未完成”的视频资源：

```bash
python main.py watch-course-incomplete --course-id 2545 \
  --cookie "MoodleSession=..." \
  --duration 600 --interval 20 \
  --payload-file payloads/example_fsresource_set_time.json \
  --limit 5 --gap 5
```

- 顺序执行以避免平台“同时观看多个视频”的警告；`--gap` 控制视频之间的间隔秒数。
- 模板占位符同 watch-video；每个视频会自动解析 `sesskey` 与 `fsresourceid`（优先 `playerdata`，回退 `M.cfg`/AJAX）。
- 可用 `--limit` 限制最多处理的视频数量。
### 探测 service.php 原始响应

使用 `probe-service` 进行一次请求探测并打印原文与解析结果：

```bash
python main.py probe-service --video-id 159716 \
  --cookie "MoodleSession=..." \
  --payload-file payloads/example_fsresource_set_time.json
```

- 探测会访问 `view.php` 页面，从 `playerdata`/`M.cfg` 获取 `sesskey` 与 `fsresourceid`，填入模板占位符后发送一次请求。
- 控制台会先打印 `service.php` 的原始响应文本，再打印解析出的 `status/progress/totaltime/completion` 等关键字段。
### 特别鸣谢Trae编辑器对本项目的大力支持
//TODO 相关提示词记录

